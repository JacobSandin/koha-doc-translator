import os
import glob
from pathlib import Path
import deepl
from dotenv import load_dotenv
import polib
import re
from typing import Dict, Tuple
import time
from tenacity import retry, stop_after_attempt, wait_exponential
import csv
import logging
import datetime
import sqlite3
import hashlib

# Load environment variables
load_dotenv()

# Set up translation cache database
def setup_translation_cache():
    """Set up SQLite database for caching translations"""
    cache_dir = Path('cache')
    try:
        cache_dir.mkdir(exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create cache directory: {e}")
        # Fall back to current directory
        cache_dir = Path('.')
        
    db_path = cache_dir / 'translation_cache.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS translations (
        source_text_hash TEXT PRIMARY KEY,
        source_text TEXT,
        source_lang TEXT,
        target_lang TEXT,
        translated_text TEXT,
        timestamp DATETIME
    )
    ''')
    
    conn.commit()
    conn.close()
    
    return db_path

# Set up logging
def setup_logging(debug_mode=False):
    """Set up logging to both console and file"""
    # Create log directory if it doesn't exist
    log_dir = Path('log')
    try:
        log_dir.mkdir(exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create log directory: {e}")
        # Fall back to current directory if log dir can't be created
        log_dir = Path('.')
    
    # Create a timestamp for the log filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'translation_{timestamp}.log'
    
    # Set up root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Clear any existing handlers
    for handler in logger.handlers[::]:
        logger.removeHandler(handler)
    
    # Create file handler which logs even debug messages
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file
    
    # Create console handler with a potentially higher log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Create formatter and add it to the handlers
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(message)s')  # Simpler format for console
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.info(f"Logging to {log_file}")
    return log_file

class KohaTranslator:
    def __init__(self, source_dir, po_dir, disable_cache=False):
        """Initialize the translator with source and target directories"""
        self.source_dir = Path(source_dir)
        self.po_dir = Path(po_dir)
        self.disable_cache = disable_cache
        self.translator = deepl.Translator(os.getenv('DEEPL_API_KEY'))
        self.glossary = None
        self.glossary_name = "koha_manual_glossary"
        # Map lowercase language codes to DeepL uppercase codes
        self.deepl_lang_map = {
            'sv': 'SV',
            'en': 'EN'
        }
        # Set up translation cache
        self.cache_db_path = setup_translation_cache()
        self.cache_hits = 0
        # Flag to indicate if we should skip reading from cache but still write to it
        self.skip_cache_read = disable_cache

    def load_or_create_glossary(self, phrases_file, auto_phrases_file=None):
        """Load existing glossary or create a new one from phrases files, or update an existing one
        
        If auto_phrases_file is provided, entries from that file will be loaded first,
        then entries from phrases_file will be added, overriding any duplicates.
        """
        try:
            # Initialize entries dictionary
            entries = {}
            ref_entries = {}
            phrases_entries = {}
            
            # First, load entries from phrases.csv to identify which terms have custom translations
            if os.path.exists(phrases_file):
                logging.info(f"Loading main phrases from {phrases_file}")
                try:
                    with open(phrases_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row['EN'] and row['SV']:  # Only add if both translations exist
                                # Store singular form
                                phrases_entries[row['EN']] = row['SV']
                                
                                # Also store plural form if available
                                if 'PLURAL' in row and row['PLURAL'] and row['PLURAL'].strip():
                                    # Add plural form as a separate entry
                                    phrases_entries[row['EN'] + 's'] = row['PLURAL']
                    logging.info(f"Loaded {len(phrases_entries)} entries from main phrases file")
                except Exception as e:
                    logging.error(f"Error loading main phrases file: {e}")
            
            # Then load entries from auto_phrases.csv, but only if they don't exist in phrases.csv
            if auto_phrases_file and os.path.exists(auto_phrases_file):
                logging.info(f"Loading reference phrases from {auto_phrases_file}")
                try:
                    with open(auto_phrases_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row['EN'] and row['SV']:  # Only add if both translations exist
                                # Only add if this term doesn't have a custom translation in phrases.csv
                                # or if the SV value is different from the EN value (not just a copy)
                                if row['EN'] not in phrases_entries and row['EN'] != row['SV']:
                                    # Store singular form
                                    ref_entries[row['EN']] = row['SV']
                                    
                                    # Also store plural form if available
                                    if 'PLURAL' in row and row['PLURAL'] and row['PLURAL'].strip():
                                        # Check if plural form already exists in phrases_entries
                                        if row['EN'] + 's' not in phrases_entries:
                                            # Add plural form as a separate entry
                                            ref_entries[row['EN'] + 's'] = row['PLURAL']
                    logging.info(f"Loaded {len(ref_entries)} usable entries from reference phrases file")
                except Exception as e:
                    logging.error(f"Error loading reference phrases file: {e}")
            
            # Combine entries, with phrases.csv taking precedence
            entries.update(ref_entries)  # Add reference entries first
            entries.update(phrases_entries)  # Then override with custom phrases
            
            logging.info(f"Combined glossary has {len(entries)} total entries")
            
            if not entries:
                logging.error("No valid entries found in any phrases files")
                return
                
            # Try to find existing glossary
            existing_glossary = None
            glossaries = self.translator.list_glossaries()  
            for glossary in glossaries:
                if glossary.name == self.glossary_name:
                    existing_glossary = glossary
                    break
            
            if existing_glossary:
                print(f"Found existing glossary: {self.glossary_name}")
                # Delete the existing glossary and recreate it with updated entries
                print(f"Updating glossary with new entries from {phrases_file}")
                self.translator.delete_glossary(existing_glossary)
                self.glossary = self.translator.create_glossary(
                    self.glossary_name,
                    source_lang="EN",
                    target_lang="SV",
                    entries=entries
                )
                print(f"Updated glossary with {len(entries)} entries")
            else:
                # No existing glossary found, create new one from phrases.csv
                print(f"Creating new glossary from {phrases_file}")
                self.glossary = self.translator.create_glossary(
                    self.glossary_name,
                    source_lang="EN",
                    target_lang="SV",
                    entries=entries
                )
                print(f"Created glossary with {len(entries)} entries")
                
        except Exception as e:
            print(f"Error loading/creating/updating glossary: {e}")
            if hasattr(e, 'response'):
                print(f"API Response: {e.response.text if hasattr(e.response, 'text') else e.response}")
    
    def read_rst_file(self, file_path):
        """Read content from an RST file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def invalidate_line(self, line):
        content = line.strip()
        return bool(re.fullmatch(r'[=\-~\^"\'\:\.\*_\+\|\s0-9]+', content))

    def get_translatable_content(self, rst_content):
        """Extract translatable content from RST file"""
        lines = rst_content.split('\n')
        translatable_lines = []
        current_line = []
        in_ref = False
        
        for i, line in enumerate(lines):
            line = line.strip()

            if self.invalidate_line(line):
                continue
            if not line:  # Skip empty lines
                if current_line:  # End of multiline
                    translatable_lines.append(' '.join(current_line))
                    current_line = []
                continue
                
            if line.startswith('..'):  # Skip RST comments
                continue
            if line.startswith('|') and line.endswith('|'):  # Skip RST substitutions
                continue
                
            # Handle RST references
            if ':ref:' in line:
                in_ref = True
                current_line.append(line)
                continue
            
            if in_ref:
                current_line.append(line)
                if line.endswith('`'):  # End of reference
                    in_ref = False
                continue
                
            # Add non-empty lines to current multiline
            if line:
                current_line.append(line)
        
        # Add any remaining lines
        if current_line:
            translatable_lines.append(' '.join(current_line))
        
        return translatable_lines
    
    def fix_escaped_chars_for_po(self, text):
        """Fix escaped characters for PO file storage"""
        if not text:
            return text
            
        # In RST files, underscores and other characters are escaped with backslash: \_
        # When stored in PO files, these should maintain the same escaping
        
        import re
        
        # First, normalize any existing escaped underscores to ensure consistency
        # This will convert any \\_ (double-escaped) to \_ (single-escaped)
        text = re.sub(r'\\\\(_)', r'\\\1', text)
        
        # Ensure all underscores that should be escaped are properly escaped
        # Look for patterns like "Asks: ___" and ensure they have proper escaping
        
        # Function to properly escape underscores in specific contexts
        def escape_underscores(match):
            prefix = match.group(1)  # Capture the prefix (e.g., "Asks: ")
            underscores = match.group(2)  # Capture the underscores
            # Replace each underscore with an escaped underscore
            escaped = ''.join(['\_' for _ in underscores])
            return f"{prefix}{escaped}"
        
        # Apply the regex to find and escape underscores in specific contexts
        # This pattern looks for words like "Asks:" followed by one or more underscores
        text = re.sub(r'((?:Asks|Default|Description):\s+)(_+)', escape_underscores, text)
        
        # Ensure that in translated text, we don't have triple backslashes before underscores
        # This fixes the issue with "\\\_ " in the Swedish translation
        text = re.sub(r'\\\\\\(_)', r'\\\1', text)
        
        return text
        
    # This method has been removed as PO files should maintain double-escaped backslashes
    
    def fix_swedish_escaping(self, text):
        """Fix specific escaping issues in Swedish translations"""
        if not text:
            return text
            
        # Fix the specific issue with extra backslash in Swedish translations
        # This pattern looks for cases where \_\_\_ becomes \_\_\\_
        import re
        
        # First, look for the specific pattern we know is problematic
        if "\\\\" in text and "layouten" in text:
            # This is a direct string replacement for the specific case
            text = text.replace("\_\_\\\_", "\_\_\_")
        
        return text
    
    def normalize_text(self, text):
        """Normalize text by joining multiline strings and standardizing whitespace"""
        if not text:
            return text
        
        # Handle escaped underscores (common in RST files)
        # This helps with comparison between RST and PO file content
        # We temporarily replace escaped underscores for comparison purposes only
        # The original format is preserved in the actual PO entries
        normalized_text = text.replace('\_', '_')
        
        # Split into lines and process each line
        lines = []
        current_ref = []
        in_ref = False
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Handle RST references that might be split across lines
            if ':ref:' in line or in_ref:
                if not in_ref:  # Start of a reference
                    in_ref = True
                    current_ref = [line]
                else:  # Continuing a reference
                    current_ref.append(line)
                    
                if line.endswith('`'):  # End of reference
                    in_ref = False
                    lines.append(' '.join(current_ref))
                    current_ref = []
            else:
                lines.append(line)
        
        # Join any remaining reference parts
        if current_ref:
            lines.append(' '.join(current_ref))
            
        return ' '.join(lines)

    @retry(stop=stop_after_attempt(3), 
           wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=lambda retry_state: isinstance(retry_state.outcome.exception(), deepl.exceptions.DeepLException))
    def fix_rst_formatting(self, text):
        """Fix common RST formatting issues in translated text"""
        if not text:
            return text
            
        # Fix italic/emphasis markers (* *)
        # Replace "* text*" with "*text*" (remove space after opening *)
        text = re.sub(r'\*\s+([^\*]+\*)', r'*\1', text)
        # Replace "*text *" with "*text*" (remove space before closing *)
        text = re.sub(r'(\*[^\*]+)\s+\*', r'\1*', text)
        
        # Fix bold markers (** **)
        # Replace "** text**" with "**text**" (remove space after opening **)
        text = re.sub(r'\*\*\s+([^\*]+\*\*)', r'**\1', text)
        # Replace "**text **" with "**text**" (remove space before closing **)
        text = re.sub(r'(\*\*[^\*]+)\s+\*\*', r'\1**', text)
        
        # Fix missing bold markers (**text)
        # Find ** without matching closing **
        bold_start_pattern = r'\*\*([^\*]+)(?=[^\*]*$)'
        for match in re.finditer(bold_start_pattern, text):
            replacement = f"**{match.group(1)}**"
            text = text.replace(match.group(0), replacement)
        
        # Fix missing emphasis markers (*text)
        # Find * without matching closing * (but not part of ** for bold)
        emphasis_start_pattern = r'(?<!\*)\*(?!\*)([^\*]+)(?=[^\*]*$)'
        for match in re.finditer(emphasis_start_pattern, text):
            replacement = f"*{match.group(1)}*"
            text = text.replace(match.group(0), replacement)
        
        # Fix complex RST references (:ref:)
        # First, fix complex references with labels: :ref:`text<label>`
        text = re.sub(r':ref:\s*`\s*([^<`]+)\s*<\s*([^>`]+)\s*>`', r':ref:`\1<\2>`', text)
        
        # Fix simple references: :ref:`label`
        text = re.sub(r':ref:\s*`\s*([^`]+)\s*`', r':ref:`\1`', text)
        
        # Fix broken references with multiple :ref: tags
        # Look for patterns like ':ref:`text :ref:`' which are invalid
        broken_ref_pattern = r':ref:`([^`]*)\s+:ref:`'
        for match in re.finditer(broken_ref_pattern, text):
            # Replace with two properly formatted references
            original = match.group(0)
            fixed = f":ref:`{match.group(1)}` :ref:`"
            text = text.replace(original, fixed)
        
        # Fix substitution references (|name|)
        # Ensure there are no spaces between the pipes and the content
        text = re.sub(r'\|\s+([^|\n]+)\s+\|', r'|\1|', text)
        text = re.sub(r'\|\s+([^|\n]+)\|', r'|\1|', text)
        text = re.sub(r'\|([^|\n]+)\s+\|', r'|\1|', text)
        
        # Fix incomplete pipe references
        # Find | without matching closing |
        incomplete_pipe_pattern = r'\|([^|\n]+)(?=[^|]*\n|[^|]*$)'
        for match in re.finditer(incomplete_pipe_pattern, text):
            if '|' not in match.group(1):  # Make sure we're not matching something that already has a closing pipe
                replacement = f"|{match.group(1)}|"
                text = text.replace(match.group(0), replacement)
        
        # Fix URL references with HTML entities: `text &lt;url&gt;`_
        # This is especially important for URL references that might have been escaped during translation
        text = re.sub(r'`([^`]+)\s*&lt;([^&>]+)&gt;`_', r'`\1 <\2>`_', text)
        
        # Fix missing spaces in URL references: `text<url>`_
        text = re.sub(r'`([^`<]+)<([^>]+)>`_', r'`\1 <\2>`_', text)
        
        return text
        
    def preserve_rst_references_with_mustache(self, text):
        """Preserve RST references during translation using DeepL's Mustache tag format
        
        This uses DeepL's Mustache tag format for placeholders that shouldn't be translated.
        See: https://developers.deepl.com/docs/learning-how-tos/examples-and-guides/placeholder-tags
        
        Args:
            text (str): The text to process
            
        Returns:
            tuple: (tagged_text, placeholders)
        """
        if not text:
            return text, {}
            
        tagged_text = text
        placeholders = {}
        
        # Find all RST references in the text
        # Complex references with display text: :ref:`display text <label>`
        complex_refs = list(re.finditer(r':ref:`([^<]*)<([^>]*)>`', tagged_text))
        
        # Simple references without display text: :ref:`label`
        simple_refs = list(re.finditer(r':ref:`([^<`]*)`(?!<)', tagged_text))
        
        # Substitution references: |name|
        subst_refs = list(re.finditer(r'\|([^|]+)\|', tagged_text))
        
        # URL references: `text <url>`_
        url_refs = list(re.finditer(r'`([^`<]+)\s*<([^>]+)>`_', tagged_text))
        
        # Process all references and replace them with Mustache tags
        all_refs = []
        for match in complex_refs:
            all_refs.append({
                'type': 'complex',
                'start': match.start(),
                'end': match.end(),
                'match': match
            })
        
        for match in simple_refs:
            all_refs.append({
                'type': 'simple',
                'start': match.start(),
                'end': match.end(),
                'match': match
            })
            
        for match in subst_refs:
            all_refs.append({
                'type': 'subst',
                'start': match.start(),
                'end': match.end(),
                'match': match
            })
            
        for match in url_refs:
            all_refs.append({
                'type': 'url',
                'start': match.start(),
                'end': match.end(),
                'match': match
            })
        
        # Sort references by their position in the text (from end to start to avoid offset issues)
        all_refs.sort(key=lambda x: x['start'], reverse=True)
        
        # Process each reference and replace with Mustache tags
        for i, ref in enumerate(all_refs):
            match = ref['match']
            full_match = match.group(0)
            
            if ref['type'] == 'complex':
                # Complex reference: :ref:`text<label>`
                ref_text = match.group(1)  # This is the display text that should be translated
                ref_label = match.group(2)  # This is the label that should not be translated
                
                # Create a unique placeholder for this reference
                placeholder_id = f"COMPLEX_REF_{i}"
                
                # Store the original reference parts
                # Determine if there was a space before the label
                has_space = len(match.group(1)) > 0 and match.group(1)[-1] == ' '
                
                placeholders[placeholder_id] = {
                    'type': 'complex',
                    'prefix': ':ref:`',
                    'display_text': ref_text.strip(),  # Original display text
                    'has_space': has_space,  # Track if there was a space before the label
                    'suffix': f"<{ref_label}>`",  # Label part that should not be translated
                    'full_match': full_match,  # Store the full original match for reference
                    'label': ref_label.strip()  # Store the label separately for validation
                }
                
                # Use Mustache tags for the label part (which should not be translated)
                # The display text remains outside the tags so it can be translated
                # We use a special format to ensure the reference structure is preserved
                tagged_text = tagged_text[:match.start()] + \
                             f":ref:`{ref_text.strip()}{{{{RST_LABEL_{placeholder_id}}}}}`" + \
                             tagged_text[match.end():]
                
            elif ref['type'] == 'simple':
                # Simple reference: :ref:`label`
                ref_label = match.group(1).strip()
                placeholder_id = f"SIMPLE_REF_{i}"
                placeholders[placeholder_id] = {
                    'type': 'simple',
                    'label': ref_label,
                    'full': full_match
                }
                
                # Use Mustache tags for the entire simple reference (should not be translated)
                tagged_text = tagged_text[:match.start()] + \
                             f"{{{{RST_SIMPLEREF_{placeholder_id}}}}}" + \
                             tagged_text[match.end():]
                
            elif ref['type'] == 'subst':
                # Substitution reference: |name|
                subst_name = match.group(1).strip()
                placeholder_id = f"SUBST_REF_{i}"
                placeholders[placeholder_id] = {
                    'type': 'subst',
                    'name': subst_name,
                    'full': full_match
                }
                
                # Use Mustache tags for the substitution reference (should not be translated)
                tagged_text = tagged_text[:match.start()] + \
                             f"{{{{RST_SUBST_{placeholder_id}}}}}" + \
                             tagged_text[match.end():]
                             
            elif ref['type'] == 'url':
                # URL reference: `text <url>`_
                link_text = match.group(1).strip()  # This is the display text that should be translated
                url = match.group(2).strip()  # This is the URL that should not be translated
                
                # Create a unique placeholder for this reference
                placeholder_id = f"URL_REF_{i}"
                
                placeholders[placeholder_id] = {
                    'type': 'url',
                    'link_text': link_text,  # Original link text
                    'url': url,  # URL that should not be translated
                    'full_match': full_match  # Store the full original match for reference
                }
                
                # Use Mustache tags for the URL part (which should not be translated)
                # The link text remains outside the tags so it can be translated
                tagged_text = tagged_text[:match.start()] + \
                             f"`{link_text} {{{{RST_URL_{placeholder_id}}}}}`_" + \
                             tagged_text[match.end():]
            
        return tagged_text, placeholders
        
    def restore_rst_references_from_mustache(self, text, placeholders):
        """Restore RST references from Mustache tags after translation.
        
        Args:
            text (str): The text with Mustache tags
            placeholders (dict): The placeholders to restore
            
        Returns:
            str: The text with restored RST references
        """
        if not text or not placeholders:
            return text
            
        restored_text = text
        
        # Process complex references
        for placeholder_id, ref_data in placeholders.items():
            if isinstance(ref_data, dict) and ref_data['type'] == 'complex':
                # Find the translated display text and Mustache tag in the translated text
                # We need a more robust pattern to handle various cases
                pattern = f'([^:]*)(:ref:`[^{{]*)({{{{RST_LABEL_{placeholder_id}}}}})`'
                matches = list(re.finditer(pattern, restored_text))
                
                # Also look for cases where the display text is completely missing
                # This pattern catches cases like :ref:`{{RST_LABEL_XXX}}`
                missing_text_pattern = f'([^:]*):ref:`\s*({{{{RST_LABEL_{placeholder_id}}}}})`'
                missing_text_matches = list(re.finditer(missing_text_pattern, restored_text))
                
                # Process normal matches first
                for match in matches:
                    # Get the translated display text
                    prefix = match.group(1)  # Text before the :ref
                    ref_part = match.group(2)  # The :ref` part with the translated display text
                    
                    # Extract just the display text from the ref_part
                    display_text_match = re.match(r':ref:`([^`]*)', ref_part)
                    if display_text_match:
                        translated_display_text = display_text_match.group(1).strip()
                    else:
                        translated_display_text = ref_part.replace(':ref:`', '').strip()
                    
                    # Format the RST reference properly
                    if ref_data.get('has_space', False):
                        full_reference = f"{prefix}:ref:`{translated_display_text} <{ref_data['label']}>`"
                    else:
                        full_reference = f"{prefix}:ref:`{translated_display_text}<{ref_data['label']}>`"
                    
                    # Replace the tagged reference with the properly formatted RST reference
                    restored_text = restored_text.replace(match.group(0), full_reference)
                
                # Process matches where the display text is missing
                for match in missing_text_matches:
                    prefix = match.group(1)  # Text before the :ref
                    
                    # Use the original display text from the placeholder data
                    original_display_text = ref_data.get('display_text', '')
                    
                    # Format the RST reference properly with the original display text
                    if ref_data.get('has_space', False):
                        full_reference = f"{prefix}:ref:`{original_display_text} <{ref_data['label']}>`"
                    else:
                        full_reference = f"{prefix}:ref:`{original_display_text}<{ref_data['label']}>`"
                    
                    # Replace the tagged reference with the properly formatted RST reference
                    restored_text = restored_text.replace(match.group(0), full_reference)
                
                # Check for a more specific case where we have :ref:`<label>` format
                # This is the exact format we're seeing in the Swedish translation
                label_only_pattern = f'([^:]*):ref:`\s*<\s*{ref_data["label"]}\s*>`'
                label_only_matches = list(re.finditer(label_only_pattern, restored_text))
                
                for match in label_only_matches:
                    prefix = match.group(1)  # Text before the :ref
                    
                    # Use the original display text from the placeholder data
                    original_display_text = ref_data.get('display_text', '')
                    
                    # Format the RST reference properly with the original display text
                    if ref_data.get('has_space', False):
                        full_reference = f"{prefix}:ref:`{original_display_text} <{ref_data['label']}>`"
                    else:
                        full_reference = f"{prefix}:ref:`{original_display_text}<{ref_data['label']}>`"
                    
                    # Replace the tagged reference with the properly formatted RST reference
                    restored_text = restored_text.replace(match.group(0), full_reference)
        
        # Process simple references
        for placeholder_id, ref_data in placeholders.items():
            if isinstance(ref_data, dict) and ref_data['type'] == 'simple':
                # Replace the Mustache tag with the original simple reference
                restored_text = restored_text.replace(
                    f"{{{{RST_SIMPLEREF_{placeholder_id}}}}}", 
                    ref_data['full']
                )
        
        # Process substitution references
        for placeholder_id, ref_data in placeholders.items():
            if isinstance(ref_data, dict) and ref_data['type'] == 'subst':
                # Replace the Mustache tag with the original substitution reference
                restored_text = restored_text.replace(
                    f"{{{{RST_SUBST_{placeholder_id}}}}}", 
                    ref_data['full']
                )
                
        # Process URL references
        for placeholder_id, ref_data in placeholders.items():
            if isinstance(ref_data, dict) and ref_data['type'] == 'url':
                # Find the translated link text and Mustache tag in the translated text
                pattern = f'`([^{{]*)({{{{RST_URL_{placeholder_id}}}}})`_'
                matches = list(re.finditer(pattern, restored_text))
                
                for match in matches:
                    # Get the translated link text
                    translated_link_text = match.group(1).strip()
                    
                    # Format the URL reference properly with the original URL
                    full_reference = f"`{translated_link_text} <{ref_data['url']}>`_"
                    
                    # Replace the tagged reference with the properly formatted URL reference
                    restored_text = restored_text.replace(match.group(0), full_reference)
        
        # Post-processing fixes for common issues with RST references
        
        # Fix missing spaces between references
        restored_text = re.sub(r'>`(:ref:`)', r'>` \1', restored_text)
        
        # Fix double backticks in RST references
        restored_text = re.sub(r'label>``', r'label>`', restored_text)
        restored_text = re.sub(r'>``:ref:', r'>` :ref:', restored_text)
        
        # Fix missing text between references in specific cases
        restored_text = re.sub(r'(:ref:`TICKET\_RESOLUTION[^`]+`)(`:ref:`catalog concerns)', 
                              r'\1 and these will appear when marking \2', 
                              restored_text)
        
        # Apply normalization rules for consistency
        # Change "notices and slips tool" to "notices and slips"
        restored_text = re.sub(r':ref:`notices and slips tool <notices-and-slips-label>`', 
                              r':ref:`notices and slips <notices-and-slips-label>`', 
                              restored_text)
        
        # Change "TICKET_RESOLUTION authorized" to "TICKET_RESOLUTION"
        restored_text = re.sub(r':ref:`TICKET\_RESOLUTION authorized[^<]*<', 
                              r':ref:`TICKET\_RESOLUTION <', 
                              restored_text)
        
        # Change "TICKET_STATUS authorized" to "TICKET_STATUS"
        restored_text = re.sub(r':ref:`TICKET\_STATUS authorized[^<]*<', 
                              r':ref:`TICKET\_STATUS <', 
                              restored_text)
        
        return restored_text
    
    def preserve_rst_references(self, text):
        """Preserve RST references during translation by replacing them with placeholders"""
        if not text:
            return text, {}
            
        # Create a dictionary of placeholders
        placeholders = {}
        preserved_text = text
        
        # First, preserve escaped underscores (\_ in RST) to prevent translation issues
        # This is critical for strings like "Asks: \_\_\_" which need special handling
        escaped_underscore_pattern = r'\_(_*)'
        escaped_underscore_count = 0
        
        def replace_escaped_underscore(match):
            nonlocal escaped_underscore_count
            placeholder_id = f"ESCAPED_UNDERSCORE_{escaped_underscore_count}"
            escaped_underscore_count += 1
            placeholders[placeholder_id] = {
                'type': 'escaped_underscore',
                'original': match.group(0)
            }
            return f"[ESC_UNDERSCORE:{placeholder_id}]"
        
        # Replace all escaped underscores with placeholders
        preserved_text = re.sub(escaped_underscore_pattern, replace_escaped_underscore, preserved_text)
        
        # Process all references in a single pass to handle multiple references in the same string
        # First, identify all references in the text
        all_refs = []
        
        # 1. Find complex references with labels: :ref:`text<label>`
        complex_ref_pattern = r':ref:`([^<`]+)<([^>`]+)>`'
        complex_matches = list(re.finditer(complex_ref_pattern, text))
        for match in complex_matches:
            all_refs.append({
                'type': 'complex',
                'start': match.start(),
                'end': match.end(),
                'match': match
            })
        
        # 2. Find simple references without explicit labels: :ref:`label`
        simple_ref_pattern = r':ref:`([^<`]+)`'
        # We need to be careful not to match parts of complex references that were already matched
        simple_matches = []
        for match in re.finditer(simple_ref_pattern, text):
            # Check if this match overlaps with any complex reference
            is_part_of_complex = False
            for ref in all_refs:
                if (match.start() >= ref['start'] and match.start() < ref['end']) or \
                   (match.end() > ref['start'] and match.end() <= ref['end']):
                    is_part_of_complex = True
                    break
            if not is_part_of_complex:
                simple_matches.append(match)
                all_refs.append({
                    'type': 'simple',
                    'start': match.start(),
                    'end': match.end(),
                    'match': match
                })
        
        # 3. Find substitution references: |name|
        subst_pattern = r'\|([^|\n]+)\|'
        subst_matches = list(re.finditer(subst_pattern, text))
        for match in subst_matches:
            all_refs.append({
                'type': 'subst',
                'start': match.start(),
                'end': match.end(),
                'match': match
            })
        
        # Sort references by their position in the text (from end to start to avoid offset issues)
        all_refs.sort(key=lambda x: x['start'], reverse=True)
        
        # Process each reference and replace with placeholders
        for i, ref in enumerate(all_refs):
            match = ref['match']
            full_match = match.group(0)
            
            if ref['type'] == 'complex':
                # Complex reference: :ref:`text<label>`
                ref_text = match.group(1)  # This is the display text that should be translated (preserve spaces)
                ref_label = match.group(2)  # This is the label that should not be translated (preserve spaces)
                
                # Create a unique placeholder for this reference
                placeholder_id = f"COMPLEX_REF_{i}"
                
                # Store the original reference parts
                # Determine if there was a space before the label
                has_space = len(match.group(1)) > 0 and match.group(1)[-1] == ' '
                
                placeholders[placeholder_id] = {
                    'type': 'complex',
                    'prefix': ':ref:`',
                    'display_text': ref_text.strip(),  # Original display text (will be replaced with translation)
                    'has_space': has_space,  # Track if there was a space before the label
                    'suffix': f"<{ref_label}>`",  # Label part that should not be translated
                    'full_match': full_match,  # Store the full original match for reference
                    'label': ref_label.strip()  # Store the label separately for validation
                }
                
                # Use a unique non-translatable token for the entire reference
                # This prevents DeepL from modifying or splitting the reference
                preserved_text = preserved_text[:match.start()] + \
                                f"RST_REF_{placeholder_id}" + \
                                preserved_text[match.end():]
                
            elif ref['type'] == 'simple':
                # Simple reference: :ref:`label`
                ref_label = match.group(1).strip()
                placeholder_id = f"SIMPLE_REF_{i}"
                placeholders[placeholder_id] = {
                    'type': 'simple',
                    'label': ref_label,
                    'full': full_match
                }
                
                # Use a unique non-translatable token for the simple reference
                preserved_text = preserved_text[:match.start()] + \
                                f"RST_SIMPLEREF_{placeholder_id}" + \
                                preserved_text[match.end():]
                
            elif ref['type'] == 'subst':
                # Substitution reference: |name|
                subst_name = match.group(1).strip()
                placeholder_id = f"SUBST_REF_{i}"
                placeholders[placeholder_id] = {
                    'type': 'subst',
                    'name': subst_name,
                    'full': full_match
                }
                
                # Use a unique non-translatable token for the substitution reference
                preserved_text = preserved_text[:match.start()] + \
                                f"RST_SUBST_{placeholder_id}" + \
                                preserved_text[match.end():]
            
        return preserved_text, placeholders
        
    def restore_rst_references(self, text, placeholders):
        """Restore RST references from placeholders after translation"""
        if not text or not placeholders:
            return text
            
        restored_text = text
        
        # First handle complex references with the new XML-like tags
        for placeholder_id, ref_data in placeholders.items():
            if isinstance(ref_data, dict) and ref_data['type'] == 'complex':
                # Find the placeholder pattern in the translated text
                pattern = f"RST_REF_{placeholder_id}"
                matches = list(re.finditer(pattern, restored_text))
                
                # Use the original display text since we're using a simple token approach
                display_text = ref_data['display_text']
                
                # Add a space before the label if the original had one
                if ref_data.get('has_space', False):
                    full_reference = f"{ref_data['prefix']}{display_text} {ref_data['suffix']}"
                else:
                    full_reference = f"{ref_data['prefix']}{display_text}{ref_data['suffix']}"
                
                # Replace the placeholder with the full reference
                restored_text = restored_text.replace(pattern, full_reference)
        
        # Handle simple references with the new XML-like tags
        for placeholder_id, ref_data in placeholders.items():
            if isinstance(ref_data, dict) and ref_data['type'] == 'simple':
                # Replace the placeholder with the original reference
                pattern = f"RST_SIMPLEREF_{placeholder_id}"
                restored_text = re.sub(pattern, ref_data['full'], restored_text)
        
        # Handle substitution references with the new XML-like tags
        for placeholder_id, ref_data in placeholders.items():
            if isinstance(ref_data, dict) and ref_data['type'] == 'subst':
                # Replace the placeholder with the original reference
                pattern = f"RST_SUBST_{placeholder_id}"
                restored_text = re.sub(pattern, ref_data['full'], restored_text)
        
        # Handle escaped underscores
        for placeholder_id, ref_data in placeholders.items():
            if isinstance(ref_data, dict) and ref_data['type'] == 'escaped_underscore':
                # Restore escaped underscores exactly as they were in the original text
                pattern = re.escape(f"[ESC_UNDERSCORE:{placeholder_id}]")
                original = ref_data.get('original', '\_')
                restored_text = re.sub(pattern, lambda m: original, restored_text)
        
        # Handle old-style placeholders for backward compatibility
        for placeholder, ref_data in placeholders.items():
            if not isinstance(ref_data, dict):
                pattern = re.escape(placeholder)
                restored_text = re.sub(pattern, lambda m: ref_data, restored_text)
        
        # Fix any broken references that might have been created during translation
        # This can happen if DeepL inserts spaces or changes formatting within references
        
        # Fix complex references with labels: :ref:`text<label>`
        restored_text = re.sub(r':ref:\s*`\s*([^<`]+)\s*<\s*([^>`]+)\s*>`', r':ref:`\1<\2>`', restored_text)
        
        # Fix simple references: :ref:`label`
        restored_text = re.sub(r':ref:\s*`\s*([^`]+)\s*`', r':ref:`\1`', restored_text)
        
        # Fix broken references that might have been split during translation
        # Look for patterns like ':ref:`text :ref:`' which are invalid
        broken_ref_pattern = r':ref:`([^`]*):ref:`'
        for match in re.finditer(broken_ref_pattern, restored_text):
            # Replace with two properly formatted references
            original = match.group(0)
            fixed = f":ref:`{match.group(1)}` :ref:`"
            restored_text = restored_text.replace(original, fixed)
            
        # Fix duplicated label parts in complex references
        # This can happen if DeepL duplicates part of the reference
        duplicated_label_pattern = r':ref:`([^<`]+)<([^>`]+)>`([^<`]*)<\2>`'
        restored_text = re.sub(duplicated_label_pattern, r':ref:`\1<\2>`\3', restored_text)
        
        # Fix corrupted complex references with extra characters after the label
        # Example: :ref:`text<label>`y text
        restored_text = re.sub(r':ref:`([^<`]+)<([^>`]+)>`([a-zA-Z]+)', r':ref:`\1<\2>`', restored_text)
        
        # Fix broken reference with 'ns' suffix
        # Example: :ref:`catalog concerns <manage-catalog-concerns-label>`ns
        restored_text = re.sub(r':ref:`([^<`]+)<([^>`]+)>`ns', r':ref:`\1<\2>`', restored_text)
        
        # Fix temp prefix before reference
        # Example: temp:ref:`notices and slips tool <notices-and-slips-label>`
        restored_text = re.sub(r'temp:ref:`([^<`]+)<([^>`]+)>`', r':ref:`\1<\2>`', restored_text)
        
        # Fix a:ref prefix
        # Example: a:ref:`catalog concerns <manage-catalog-concerns-label>`
        restored_text = re.sub(r'a:ref:`([^<`]+)<([^>`]+)>`', r':ref:`\1<\2>`', restored_text)
        
        # Fix truncated closing bracket in reference
        # Example: :ref:`text<label`
        restored_text = re.sub(r':ref:`([^<`]+)<([^>`]+)`', r':ref:`\1<\2>`', restored_text)
        
        # Fix Reference with extra text between display and label
        # Example: :ref:`text y <label>`
        restored_text = re.sub(r':ref:`([^<`]+)\s+([a-zA-Z]+)\s+<([^>`]+)>`', r':ref:`\1 <\3>`', restored_text)
        
        # Fix double closing bracket with text in between
        # Example: :ref:`text<label>`-text>`
        restored_text = re.sub(r':ref:`([^<`]+)<([^>`]+)>`([^<`]*?)-[^<`]*?>`', r':ref:`\1<\2>`\3', restored_text)
        
        # Fix specific case for duplicate permission-issue-manage-label
        # Example: :ref:`issue_manage <permission-issue-manage-label>` <permission-issue-manage-label>`
        restored_text = re.sub(r':ref:`([^<`]+)<([^>`]+)>` <\2>`', r':ref:`\1<\2>`', restored_text)
        
        # Fix notices and slips tool with 'tool' suffix
        # Example: :ref:`notices and slips <notices-and-slips-label>` tool
        restored_text = re.sub(r':ref:`notices and slips <notices-and-slips-label>` tool', 
                              r':ref:`notices and slips <notices-and-slips-label>`', restored_text)
        
        # Standardize references to maintain consistency
        # For notices and slips, use a consistent format
        restored_text = re.sub(r':ref:`notices and slips tool <notices-and-slips-label>`', 
                              r':ref:`notices and slips <notices-and-slips-label>`', restored_text)
        
        # For catalog concerns, use a consistent format
        restored_text = re.sub(r':ref:`catalog <manage-catalog-concerns-label>`', 
                              r':ref:`catalog concerns <manage-catalog-concerns-label>`', restored_text)
        
        # For TICKET_RESOLUTION, use a consistent format
        restored_text = re.sub(r':ref:`TICKET\_RESOLUTION authorized value category <ticketresolution-av-category-label>`', 
                              r':ref:`TICKET\_RESOLUTION <ticketresolution-av-category-label>`', restored_text)
        
        return restored_text
        
    def get_cached_translation(self, text, source_lang, target_lang):
        """Get a translation from the cache if it exists"""
        # If cache reading is disabled, always return None
        if self.skip_cache_read:
            logging.debug("Cache reading disabled, skipping cache lookup")
            return None
            
        # Create a unique hash for this translation request
        text_hash = hashlib.md5(f"{text}_{source_lang}_{target_lang}".encode('utf-8')).hexdigest()
        
        try:
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            
            # Look for this translation in the cache
            cursor.execute(
                'SELECT translated_text FROM translations WHERE source_text_hash = ?', 
                (text_hash,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                self.cache_hits += 1
                logging.debug(f"Cache hit: {text[:50]}..." if len(text) > 50 else f"Cache hit: {text}")
                return result[0]
            else:
                return None
        except Exception as e:
            logging.error(f"Error accessing translation cache: {e}")
            return None
    
    def cache_translation(self, text, source_lang, target_lang, translated_text):
        """Save a translation to the cache"""
        # Create a unique hash for this translation request
        text_hash = hashlib.md5(f"{text}_{source_lang}_{target_lang}".encode('utf-8')).hexdigest()
        
        try:
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            
            # Store the translation in the cache
            cursor.execute(
                'INSERT OR REPLACE INTO translations VALUES (?, ?, ?, ?, ?, ?)',
                (text_hash, text, source_lang, target_lang, translated_text, datetime.datetime.now().isoformat())
            )
            
            conn.commit()
            conn.close()
            logging.debug(f"Cached translation: {text[:50]}..." if len(text) > 50 else f"Cached translation: {text}")
        except Exception as e:
            logging.error(f"Error saving to translation cache: {e}")
    
    @retry(stop=stop_after_attempt(3), 
           wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=lambda retry_state: isinstance(retry_state.outcome.exception(), deepl.exceptions.DeepLException))
    def translate_text(self, text, source_lang='en', target_lang='sv'):
        """Translate a chunk of text using DeepL with retry logic"""
        if not text or text.strip() == '' or text.strip() == '=':
            return None  # Skip empty lines or separator lines
            
        try:
            # Check if we already have this translation in the cache
            # Note: get_cached_translation will return None if skip_cache_read is True
            cached_translation = self.get_cached_translation(text, source_lang, target_lang)
            if cached_translation:
                return cached_translation
                
            # Preserve RST references using Mustache tags for DeepL's tag handling feature
            tagged_text, placeholders = self.preserve_rst_references_with_mustache(text)
            
            # With Mustache tags, we don't need to pre-process complex references
            # as the display text is already outside the tags and will be translated normally
            
            # Add a small delay between requests to avoid rate limiting
            time.sleep(1)  # Increased delay to avoid rate limits
            
            # Convert to DeepL language codes (uppercase)
            deepl_source = self.deepl_lang_map.get(source_lang.lower(), source_lang.upper())
            deepl_target = self.deepl_lang_map.get(target_lang.lower(), target_lang.upper())
            
            # Use glossary if available and enable tag handling with Mustache format
            if self.glossary:
                result = self.translator.translate_text(
                    tagged_text,
                    source_lang=deepl_source,
                    target_lang=deepl_target,
                    preserve_formatting=True,
                    tag_handling="html",  # Enable HTML tag handling for Mustache tags
                    outline_detection=False,  # Disable outline detection to preserve tags
                    glossary=self.glossary
                )
            else:
                result = self.translator.translate_text(
                    tagged_text,
                    source_lang=deepl_source,
                    target_lang=deepl_target,
                    preserve_formatting=True,
                    tag_handling="html",  # Enable HTML tag handling for Mustache tags
                    outline_detection=False  # Disable outline detection to preserve tags
                )
                
            translated_text = result.text if result else None
            
            # Restore RST references from Mustache tags after translation
            if translated_text:
                translated_text = self.restore_rst_references_from_mustache(translated_text, placeholders)
                # Apply RST formatting fixes to the translated text
                translated_text = self.fix_rst_formatting(translated_text)
                # Cache the translation for future use
                self.cache_translation(text, source_lang, target_lang, translated_text)
                
            return translated_text
            
        except (KeyboardInterrupt, SystemExit):
            print("\nTranslation interrupted by user")
            raise  # Re-raise to stop the process
        except deepl.exceptions.DeepLException as e:
            print(f"\nTranslation error: {e}")
            if hasattr(e, 'response'):
                print(f"API Response: {e.response.text if hasattr(e.response, 'text') else e.response}")
            raise  # Let the retry decorator handle it
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            return None  # Skip this text on unexpected errors

    # Status functionality moved to improved_status.py
    
    def find_line_numbers_in_rst(self, rst_file, text):
        """Find all line numbers where a text appears in an RST file"""
        try:
            if not rst_file.exists():
                return ['0']
                
            # Read the RST file content
            with open(rst_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Clean the search text (remove RST formatting, normalize whitespace)
            search_text = text.strip()
            # Remove RST formatting markers like ^^^^
            search_text = re.sub(r'\^+', '', search_text)
            # Remove escaped characters for comparison
            search_text = re.sub(r'\\(.)', r'\1', search_text)
            
            # For very short strings like "Description:" we need to be more precise
            is_common_string = len(search_text) < 15 and search_text.endswith(':')
            
            line_numbers = []
            
            # Search for the text in the file
            for i, line in enumerate(lines):
                clean_line = line.strip()
                # Remove RST formatting markers
                clean_line = re.sub(r'\^+', '', clean_line)
                # Remove escaped characters for comparison
                clean_line = re.sub(r'\\(.)', r'\1', clean_line)
                
                # For common strings like "Description:", we need an exact match
                if is_common_string:
                    if clean_line == search_text:
                        line_numbers.append(str(i + 1))  # Line numbers are 1-based in PO files
                elif search_text in clean_line:
                    line_numbers.append(str(i + 1))
            
            # If not found, try with a more flexible approach
            if not line_numbers:
                for i, line in enumerate(lines):
                    clean_line = line.strip().lower()
                    search_text_lower = search_text.lower()
                    
                    # Try to match the beginning of the text
                    if clean_line and search_text_lower and clean_line.startswith(search_text_lower[:10]):
                        line_numbers.append(str(i + 1))
            
            return line_numbers if line_numbers else ['0']  # Default if not found
        except Exception as e:
            logging.error(f"Error finding line numbers: {e}")
            return ['0']
    
    def extract_strings_from_rst(self, rst_file):
        """Extract strings from an RST file in the order they appear"""
        try:
            if not rst_file.exists():
                return []
                
            # Read the RST file content
            with open(rst_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract strings in order
            # This is a simplified approach - in a real implementation, you'd need
            # a more sophisticated parser to handle all RST constructs correctly
            strings = []
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('..') and not line.startswith(':'):
                    # Skip lines that are just RST formatting (e.g., ^^^^^^)
                    if not re.match(r'^[\^\~\=\-\.\*]+$', line):
                        strings.append(line)
            
            return strings
        except Exception as e:
            logging.error(f"Error extracting strings from RST: {e}")
            return []
    
    def reorder_po_file(self, po_path, rst_file):
        """Reorder the PO file entries to match the order of strings in the RST file"""
        try:
            if not po_path.exists() or not rst_file.exists():
                return False
                
            # Load the existing PO file
            po = polib.pofile(str(po_path))
            
            # Extract strings from the RST file in order
            rst_strings = self.extract_strings_from_rst(rst_file)
            
            # Create a new PO file with the same metadata
            new_po = polib.POFile()
            new_po.metadata = po.metadata
            
            # Create a dictionary of existing entries by msgid for quick lookup
            entries_by_msgid = {entry.msgid: entry for entry in po}
            
            # Add entries in the order they appear in the RST file
            added_msgids = set()
            for string in rst_strings:
                # Try to find an exact match
                if string in entries_by_msgid:
                    new_po.append(entries_by_msgid[string])
                    added_msgids.add(string)
                else:
                    # Try to find a normalized match
                    normalized_string = self.normalize_text(string)
                    for msgid, entry in entries_by_msgid.items():
                        if self.normalize_text(msgid) == normalized_string and msgid not in added_msgids:
                            new_po.append(entry)
                            added_msgids.add(msgid)
                            break
            
            # Add any remaining entries that weren't found in the RST file
            for entry in po:
                if entry.msgid not in added_msgids:
                    new_po.append(entry)
            
            # Save the reordered PO file
            new_po.save(str(po_path))
            return True
        except Exception as e:
            logging.error(f"Error reordering PO file: {e}")
            return False
    
    def update_po_file_single_entry(self, po_path, msgid, msgstr):
        """Update a single entry in a PO file with a new translation"""
        if po_path.exists():
            po = polib.pofile(str(po_path))
        else:
            po = polib.POFile()
            po.metadata = {
                'Project-Id-Version': 'Koha Manual',
                'Language': 'sv',
                'MIME-Version': '1.0',
                'Content-Type': 'text/plain; charset=UTF-8',
                'Content-Transfer-Encoding': '8bit',
            }
        
        # Fix any escaped characters in the msgid
        fixed_msgid = self.fix_escaped_chars_for_po(msgid)
        
        # Try to find with both original and fixed msgid
        entry = po.find(msgid) or po.find(fixed_msgid)
        if entry:
            entry.msgstr = msgstr
            # Update the msgid to ensure it has proper escaping
            entry.msgid = fixed_msgid
            # Remove fuzzy flag if present
            if 'fuzzy' in entry.flags:
                entry.flags.remove('fuzzy')
        else:
            # Try to find using normalized text
            normalized_msgid = self.normalize_text(msgid)
            found = False
            
            for entry in po:
                normalized_entry_msgid = self.normalize_text(entry.msgid)
                if normalized_entry_msgid == normalized_msgid:
                    entry.msgstr = msgstr
                    # Remove fuzzy flag if present
                    if 'fuzzy' in entry.flags:
                        entry.flags.remove('fuzzy')
                    found = True
                    break
            
            # If no match found, create a new entry
            if not found:
                # Fix any escaped characters in the msgid before creating the PO entry
                fixed_msgid = self.fix_escaped_chars_for_po(msgid)
                
                # Get the relative path to the RST file for the occurrences
                rst_path = None
                line_number = '0'
                try:
                    # Extract the file name from the po_path
                    file_name = po_path.stem
                    # Find the corresponding RST file
                    rst_file = self.source_dir / f"{file_name}.rst"
                    if rst_file.exists():
                        # Create the relative path for the occurrence
                        rst_path = f"../../source/{file_name}.rst"
                        # Find all line numbers in the RST file
                        line_numbers = self.find_line_numbers_in_rst(rst_file, msgid)
                except Exception as e:
                    logging.error(f"Error getting RST path: {e}")
                
                # Create occurrences list if we have a valid RST path
                occurrences = [(rst_path, line_num) for line_num in line_numbers] if rst_path else []
                
                entry = polib.POEntry(
                    msgid=fixed_msgid,
                    msgstr=msgstr,
                    # Ensure no fuzzy flag is set for new entries
                    flags=[],
                    occurrences=occurrences
                )
                po.append(entry)
        
        # Save the file immediately
        po.save(str(po_path))
        
        # Reorder the PO file to match the RST file
        try:
            file_name = po_path.stem
            rst_file = self.source_dir / f"{file_name}.rst"
            if rst_file.exists():
                self.reorder_po_file(po_path, rst_file)
        except Exception as e:
            logging.error(f"Error reordering PO file: {e}")
    
    def clean_obsolete_entries(self, po_path, rst_file):
        """Remove entries from PO file that no longer exist in the RST file"""
        if not po_path.exists() or not rst_file.exists():
            # Return an object with removed_count attribute
            class Result:
                pass
            result = Result()
            result.removed_count = 0
            return result
            
        try:
            # Load the existing PO file
            po = polib.pofile(str(po_path))
            
            # Extract all translatable content from the RST file
            content = self.read_rst_file(rst_file)
            translatable_content = self.get_translatable_content(content)
            
            # Create sets of normalized content for comparison
            rst_content_set = []
            for text in translatable_content:
                if text:
                    normalized = self.normalize_text(text)
                    if normalized not in rst_content_set:
                        rst_content_set.append(normalized)
            
            # Find entries that no longer exist in the RST file
            entries_to_remove = []
            for entry in po:
                if not entry.obsolete:  # Skip already marked obsolete entries
                    normalized_msgid = self.normalize_text(entry.msgid)
                    if normalized_msgid not in rst_content_set:
                        # Entry no longer exists in the RST file
                        entries_to_remove.append(entry)
            
            # Remove obsolete entries completely
            removed_count = 0
            for entry in entries_to_remove:
                po.remove(entry)  # Completely remove the entry
                removed_count += 1
            
            if removed_count > 0:
                logging.info(f"Removed {removed_count} obsolete entries from {po_path.name}")
                print(f"Removed {removed_count} obsolete entries from {po_path.name}")
                # Save the updated PO file
                po.save(str(po_path))
            
            # Return an object with removed_count attribute
            class Result:
                pass
            result = Result()
            result.removed_count = removed_count
            return result
        except Exception as e:
            logging.error(f"Error cleaning obsolete entries: {e}")
            # Return an object with removed_count attribute
            class Result:
                pass
            result = Result()
            result.removed_count = 0
            return result
    
    def update_po_file(self, po_path, translations):
        """Update or create PO file with new translations"""
        if po_path.exists():
            po = polib.pofile(str(po_path))
        else:
            po = polib.POFile()
            po.metadata = {
                'Project-Id-Version': 'Koha Manual',
                'Language': 'sv',
                'MIME-Version': '1.0',
                'Content-Type': 'text/plain; charset=UTF-8',
                'Content-Transfer-Encoding': '8bit',
            }
        
        # Track which entries we've updated
        updated_entries = set()
        
        # First pass: Update exact matches
        for msgid, msgstr in translations.items():
            # Fix any escaped characters in the msgid
            fixed_msgid = self.fix_escaped_chars_for_po(msgid)
            
            # Fix escaped underscores in msgstr to ensure consistent escaping
            # This prevents the extra backslash issue in Swedish translations
            fixed_msgstr = msgstr
            # Use regex to find and fix problematic patterns like \_\_\\_
            import re
            fixed_msgstr = re.sub(r'\\_(\\)_\\_(\\)_\\\\\\_(\\)_', r'\\_(\\)_\\_(\\)_\\_(\\)_', fixed_msgstr)
            
            # Try to find with both original and fixed msgid
            entry = po.find(msgid) or po.find(fixed_msgid)
            if entry:
                entry.msgstr = fixed_msgstr
                # Update the msgid to ensure it has proper escaping
                entry.msgid = fixed_msgid
                # Remove fuzzy flag if present
                if 'fuzzy' in entry.flags:
                    entry.flags.remove('fuzzy')
                updated_entries.add(msgid)
        
        # Second pass: Try to find matches using normalized text
        for msgid, msgstr in translations.items():
            if msgid in updated_entries:
                continue
                
            normalized_msgid = self.normalize_text(msgid)
            found = False
            
            # Fix escaped underscores in msgstr to ensure consistent escaping
            fixed_msgstr = msgstr
            # Use regex to find and fix problematic patterns like \_\_\\_
            import re
            fixed_msgstr = re.sub(r'\\_(\\)_\\_(\\)_\\\\\\_(\\)_', r'\\_(\\)_\\_(\\)_\\_(\\)_', fixed_msgstr)
            
            for entry in po:
                normalized_entry_msgid = self.normalize_text(entry.msgid)
                if normalized_entry_msgid == normalized_msgid:
                    entry.msgstr = fixed_msgstr
                    # Remove fuzzy flag if present
                    if 'fuzzy' in entry.flags:
                        entry.flags.remove('fuzzy')
                    found = True
                    break
            
            # If no match found, create a new entry
            if not found:
                # Fix any escaped characters in the msgid before creating the PO entry
                fixed_msgid = self.fix_escaped_chars_for_po(msgid)
                
                # Get the relative path to the RST file for the occurrences
                rst_path = None
                line_number = '0'
                try:
                    # Extract the file name from the po_path
                    file_name = po_path.stem
                    # Find the corresponding RST file
                    rst_file = self.source_dir / f"{file_name}.rst"
                    if rst_file.exists():
                        # Create the relative path for the occurrence
                        rst_path = f"../../source/{file_name}.rst"
                        # Find all line numbers in the RST file
                        line_numbers = self.find_line_numbers_in_rst(rst_file, msgid)
                except Exception as e:
                    logging.error(f"Error getting RST path: {e}")
                
                # Create occurrences list if we have a valid RST path
                occurrences = [(rst_path, line_num) for line_num in line_numbers] if rst_path else []
                
                entry = polib.POEntry(
                    msgid=fixed_msgid,
                    msgstr=fixed_msgstr,
                    # Ensure no fuzzy flag is set for new entries
                    flags=[],
                    occurrences=occurrences
                )
                po.append(entry)
        
        # Save the file
        po.save(str(po_path))
        
        # Reorder the PO file to match the RST file
        try:
            file_name = po_path.stem
            rst_file = self.source_dir / f"{file_name}.rst"
            if rst_file.exists():
                self.reorder_po_file(po_path, rst_file)
        except Exception as e:
            logging.error(f"Error reordering PO file: {e}")
    
    def process_manual(self, specific_file=None, translate_all=False, debug=False):
        """Process RST files and update PO translations"""
        # Initialize counters for summary
        total_obsolete_count = 0
        total_success_count = 0
        total_skip_count = 0
        total_fail_count = 0
        try:
            if specific_file:
                # Process single file
                rst_file = self.source_dir / f"{specific_file}.rst"
                if not rst_file.exists():
                    print(f"Error: File {rst_file} not found")
                    return
                rst_files = [rst_file]
            else:
                # Process all files
                rst_files = list(self.source_dir.rglob("*.rst"))
            
            print(f"\nStarting translation process for sv...")
            
            for rst_file in rst_files:
                file_info = f"\nProcessing {rst_file}"
                logging.info(file_info)
                print(file_info)
                
                try:
                    # Determine corresponding PO file path
                    relative_path = rst_file.relative_to(self.source_dir)
                    po_path = self.po_dir / "sv" / "LC_MESSAGES" / f"{relative_path.stem}.po"
                    
                    # Clean obsolete entries first
                    if po_path.exists():
                        result = self.clean_obsolete_entries(po_path, rst_file)
                        # Get the count of obsolete entries from the result
                        total_obsolete_count += result.removed_count
                    
                    # Load existing translations and get all entries
                    existing_translations = {}
                    existing_msgids = set()
                    all_entries = []
                    if po_path.exists():
                        po = polib.pofile(po_path)
                        all_entries = [entry for entry in po if not entry.obsolete]
                        
                        # Store all msgids (both translated and untranslated) for comparison
                        for entry in po:
                            existing_msgids.add(entry.msgid)
                            normalized_msgid = self.normalize_text(entry.msgid)
                            existing_msgids.add(normalized_msgid)
                            
                            # Only add translated entries to existing_translations
                            if not translate_all and entry.msgstr:  
                                existing_translations[normalized_msgid] = entry.msgstr
                    
                    # Prepare translations dictionary
                    translations = {}
                    success_count = 0
                    skip_count = 0
                    fail_count = 0
                    
                    # First, process all existing entries
                    for entry in all_entries:
                        if not entry.msgstr or translate_all:
                            try:
                                translated = self.translate_text(entry.msgid, source_lang='en', target_lang='sv')
                                if translated:
                                    # If translate_all is enabled and there's an existing translation, log it
                                    if translate_all and entry.msgstr:
                                        logging.info(f"\nReplacing translation [{success_count + 1}] in {rst_file.stem}")
                                        # Always log full text to file
                                        logging.debug(f"Original: {entry.msgid}")
                                        logging.debug(f"Old translation: {entry.msgstr}")
                                        logging.debug(f"New translation: {translated}")
                                        
                                        # For console output, respect debug flag
                                        if debug:
                                            # Show full text in debug mode (already logged above)
                                            pass
                                        else:
                                            # Limit to 50 chars in normal mode for console only
                                            print(f"Original: {entry.msgid[:50]}..." if len(entry.msgid) > 50 else f"Original: {entry.msgid}")
                                            print(f"Old translation: {entry.msgstr[:50]}..." if len(entry.msgstr) > 50 else f"Old translation: {entry.msgstr}")
                                            print(f"New translation: {translated[:50]}..." if len(translated) > 50 else f"New translation: {translated}")
                                    else:
                                        # Always log full text to file
                                        logging.info(f"\nTranslated [{success_count + 1}] in {rst_file.stem}")
                                        logging.debug(f"Original: {entry.msgid}")
                                        logging.debug(f"Translation: {translated}")
                                        
                                        # For console output, respect debug flag
                                        if debug:
                                            # Show full text in debug mode (already logged above)
                                            pass
                                        else:
                                            # Limit to 50 chars in normal mode for console only
                                            print(f"\nTranslated [{success_count + 1}]: {entry.msgid[:50]}..." if len(entry.msgid) > 50 else f"\nTranslated [{success_count + 1}]: {entry.msgid}")
                                            print(f"To: {translated[:50]}..." if len(translated) > 50 else f"To: {translated}")
                                    
                                    # Save the translation immediately
                                    self.update_po_file_single_entry(po_path, entry.msgid, translated)
                                    
                                    # Still keep track for final statistics
                                    translations[entry.msgid] = translated
                                    success_count += 1
                            except Exception as e:
                                fail_count += 1
                                logging.error(f"\nFailed to translate in {rst_file.stem}: {entry.msgid}")
                                logging.error(f"Error: {str(e)}")
                                print(f"\nFailed to translate: {entry.msgid[:50]}...")
                        else:
                            translations[entry.msgid] = entry.msgstr
                            skip_count += 1
                            logging.info(f"\nSkipping already translated in {rst_file.stem}: {entry.msgid}")
                            print(f"\nSkipping already translated: {entry.msgid[:50]}...")
                    
                    # Then process any new content from RST
                    content = self.read_rst_file(rst_file)
                    translatable_content = self.get_translatable_content(content)
                    
                    # Debug: Log all translatable content from RST file
                    logging.debug(f"Found {len(translatable_content)} translatable strings in {rst_file}")
                    for i, text in enumerate(translatable_content):
                        logging.debug(f"RST string {i+1}: {text}")
                        
                    # Debug: Log all existing msgids in PO file
                    logging.debug(f"Found {len(existing_msgids)} existing msgids in PO file")
                    
                    for text in translatable_content:
                        if text and text not in translations:
                            normalized_text = self.normalize_text(text)
                            
                            # Check if this text is already in the PO file (either translated or not)
                            text_in_po = text in existing_msgids or normalized_text in existing_msgids
                            
                            # Skip if already translated (unless translate_all is True)
                            if normalized_text in existing_translations and not translate_all:
                                translations[text] = existing_translations[normalized_text]
                                skip_count += 1
                                logging.info(f"\nSkipping already translated in {rst_file.stem}: {text}")
                                print(f"\nSkipping already translated: {text[:50]}...")
                                continue
                            
                            # If the text is not in the PO file at all, we need to translate it
                            # even if translate_all is not enabled
                            try:
                                if not text_in_po or translate_all:
                                    translated = self.translate_text(text, source_lang='en', target_lang='sv')
                                    if translated:
                                        # If translate_all is enabled and there's an existing translation, log it
                                        if translate_all and normalized_text in existing_translations:
                                            logging.info(f"\nReplacing translation [{success_count + 1}] in {rst_file.stem}")
                                            # Always log full text to file
                                            logging.debug(f"Original: {text}")
                                            logging.debug(f"Old translation: {existing_translations[normalized_text]}")
                                            logging.debug(f"New translation: {translated}")
                                            
                                            # For console output, respect debug flag
                                            if debug:
                                                # Show full text in debug mode (already logged above)
                                                pass
                                            else:
                                                # Limit to 50 chars in normal mode for console only
                                                print(f"Original: {text[:50]}..." if len(text) > 50 else f"Original: {text}")
                                                old_trans = existing_translations[normalized_text]
                                                print(f"Old translation: {old_trans[:50]}..." if len(old_trans) > 50 else f"Old translation: {old_trans}")
                                                print(f"New translation: {translated[:50]}..." if len(translated) > 50 else f"New translation: {translated}")
                                        else:
                                            # Always log full text to file
                                            logging.info(f"\nTranslated [{success_count + 1}] in {rst_file.stem}")
                                            logging.debug(f"Original: {text}")
                                            logging.debug(f"Translation: {translated}")
                                            
                                            # For console output, respect debug flag
                                            if debug:
                                                # Show full text in debug mode (already logged above)
                                                pass
                                            else:
                                                # Limit to 50 chars in normal mode for console only
                                                print(f"\nTranslated [{success_count + 1}]: {text[:50]}..." if len(text) > 50 else f"\nTranslated [{success_count + 1}]: {text}")
                                                print(f"To: {translated[:50]}..." if len(translated) > 50 else f"To: {translated}")
                                        
                                        # Save the translation immediately
                                        self.update_po_file_single_entry(po_path, text, translated)
                                        
                                        # Still keep track for final statistics
                                        translations[text] = translated
                                        success_count += 1
                            except Exception as e:
                                fail_count += 1
                                logging.error(f"\nFailed to translate in {rst_file.stem}: {text}")
                                logging.error(f"Error: {str(e)}")
                                print(f"\nFailed to translate: {text[:50]}...")
                    
                    # Check for patterns that might be missed by the extraction process
                    # Look for complete sentences/phrases with escaped underscores
                    import re
                    
                    # Only find complete sentences or phrases with escaped underscores
                    # This regex looks for lines that start with "Asks:", "Default:", or "Description:" 
                    # followed by escaped underscores, and captures the entire line
                    # We use word boundaries and end-of-line markers to ensure we get complete content
                    escaped_patterns = re.findall(r'((?:Asks|Default|Description):\s+\\_+[^\n]+?)(?:\n\n|\Z)', content)
                    
                    # Filter out incomplete strings
                    complete_patterns = []
                    for pattern in escaped_patterns:
                        # Only include patterns that look like complete sentences/phrases
                        # Check if the pattern ends with punctuation or looks complete
                        if len(pattern) > 10 and not pattern.endswith(' '):
                            complete_patterns.append(pattern)
                    
                    # Process only the complete patterns
                    for pattern in complete_patterns:
                        if pattern not in translations:
                            try:
                                # Create a clean version without escaped underscores for translation
                                clean_pattern = re.sub(r'\\_', '_', pattern)
                                translated = self.translate_text(clean_pattern, source_lang='en', target_lang='sv')
                                if translated:
                                    translations[pattern] = translated
                                    logging.info(f"\nTranslated missed pattern: {pattern}")
                                    print(f"\nTranslated missed pattern: {pattern[:50]}...")
                                    success_count += 1
                            except Exception as e:
                                logging.error(f"\nFailed to translate missed pattern: {pattern}")
                                logging.error(f"Error: {str(e)}")
                                print(f"\nFailed to translate missed pattern: {pattern[:50]}...")
                    
                    # Update PO file
                    if translations:
                        update_msg = f"\nUpdating translations in {po_path}"
                        logging.info(update_msg)
                        print(update_msg)
                        self.update_po_file(po_path, translations)
                        logging.info(f"Successfully translated in {rst_file.stem}: {success_count} strings")
                        logging.info(f"Skipped already translated in {rst_file.stem}: {skip_count} strings")
                        if fail_count > 0:
                            logging.info(f"Failed to translate in {rst_file.stem}: {fail_count} strings")
                        if translate_all:
                            logging.info("Note: --translate-all was enabled, existing translations were replaced with new ones")
                            
                        # Only print per-file stats if debug mode is on
                        if debug:
                            print(f"Successfully translated in {rst_file.stem}: {success_count} strings")
                            print(f"Skipped already translated in {rst_file.stem}: {skip_count} strings")
                            if fail_count > 0:
                                print(f"Failed to translate in {rst_file.stem}: {fail_count} strings")
                        
                        # Update total counters
                        total_success_count += success_count
                        total_skip_count += skip_count
                        total_fail_count += fail_count
                        if translate_all:
                            print("Note: --translate-all was enabled, existing translations were replaced with new ones")
                        
                except Exception as e:
                    error_msg = f"Error processing {rst_file}: {e}"
                    logging.error(error_msg)
                    print(error_msg)
                    continue
            
            completion_msg = "\nTranslation process completed successfully"
            
            # Print summary of all operations using the summary function
            print_summary(total_success_count, total_skip_count, total_fail_count, total_obsolete_count, self.cache_hits)
            
        except Exception as e:
            error_msg = f"Error: {e}"
            logging.error(error_msg)
            print(error_msg)



def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Koha Manual Translation Tool')
    # Status functionality moved to improved_status.py
    parser.add_argument('--translate', action='store_true', help='Run the translation process')

    parser.add_argument('--lang', default='sv', help='Language code (default: sv)')
    parser.add_argument('--file', help='Process specific file (without .rst extension)')
    parser.add_argument('--all', action='store_true', help='Process all files (required for bulk translation)')
    parser.add_argument('--phrases', default='phrases.csv', help='Path to phrases CSV file (default: phrases.csv)')
    parser.add_argument('--auto-phrases', default='auto_phrases.csv', help='Path to reference phrases CSV file (default: auto_phrases.csv)')
    parser.add_argument('--translate-all', action='store_true', help='Translate all strings, even if they already exist in PO file')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with full text output')
    parser.add_argument('--log-file', help='Specify custom log file path (default: log/translation_TIMESTAMP.log)')
    parser.add_argument('--disable-cache', action='store_true', help='Disable reading from translation cache to force new translations (still updates cache)')
    args = parser.parse_args()
    
    # Set up logging
    log_file = setup_logging(args.debug)
    if args.log_file:
        # If custom log file specified, update the file handler
        custom_log_file = Path(args.log_file)
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                logging.getLogger().removeHandler(handler)
                new_handler = logging.FileHandler(custom_log_file, encoding='utf-8')
                new_handler.setLevel(logging.DEBUG)
                new_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                logging.getLogger().addHandler(new_handler)
                log_file = custom_log_file
                break
    
    logging.info(f"Koha Manual Translation Tool started")
    logging.info(f"Debug mode: {'enabled' if args.debug else 'disabled'}")
    
    # Update these paths to point to the correct directories
    manual_source = "repos/koha-manual/source"  # RST files location
    po_dir = "repos/koha-manual/locales"  # PO files location (inside koha-manual as 'locales')
    
    translator = KohaTranslator(manual_source, po_dir, disable_cache=args.disable_cache)
    
    if args.translate:
        try:
            # Load glossary before translation
            translator.load_or_create_glossary(args.phrases, args.auto_phrases)
            if not translator.glossary:
                print("Error: Failed to create or load glossary. Stopping translation process.")
                return
            
            if not args.file and not args.all:
                error_msg = "Error: You must specify either --file <filename> or --all when using --translate"
                logging.error(error_msg)
                print(error_msg)
                return
                
            start_msg = f"\nStarting translation process for {args.lang}..."
            logging.info(start_msg)
            print(start_msg)
            # Process the manual and get the results
            result = translator.process_manual(args.file, args.translate_all, args.debug)
            
            # If we get here without an exception, the process_manual method will have already
            # printed a summary using the print_summary function
        except Exception as e:
            error_msg = f"Error during translation process: {e}"
            logging.error(error_msg)
            print(error_msg)
            # Print a summary with zeros in case of error
            print_summary(0, 0, 0, 0, translator.cache_hits)
            return
    elif not args.translate:
        # No action specified, show help
        parser.print_help()

def print_summary(total_success_count, total_skipped_count, total_fail_count, total_obsolete_count, cache_hits):
    """Print a summary of the translation process"""
    print("\nSummary for all files:")
    print(f"Successfully translated: {total_success_count} strings")
    print(f"Skipped already translated: {total_skipped_count} strings")
    if total_fail_count > 0:
        print(f"Failed to translate: {total_fail_count} strings")
    print(f"Removed obsolete entries: {total_obsolete_count} strings")
    print(f"Cache hits (saved API calls): {cache_hits} strings")

if __name__ == "__main__":
    main()
