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

# Load environment variables
load_dotenv()

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
    def __init__(self, source_dir, po_dir):
        """Initialize the translator with source and target directories"""
        self.source_dir = Path(source_dir)
        self.po_dir = Path(po_dir)
        self.translator = deepl.Translator(os.getenv('DEEPL_API_KEY'))
        self.glossary = None
        self.glossary_name = "koha_manual_glossary"
        # Map lowercase language codes to DeepL uppercase codes
        self.deepl_lang_map = {
            'sv': 'SV',
            'en': 'EN'
        }

    def load_or_create_glossary(self, phrases_file):
        """Load existing glossary or create a new one from phrases.csv"""
        try:
            # Try to find existing glossary
            glossaries = self.translator.list_glossaries()  
            for glossary in glossaries:
                if glossary.name == self.glossary_name:
                    print(f"Using existing glossary: {self.glossary_name}")
                    self.glossary = glossary
                    return
            
            # No existing glossary found, create new one from phrases.csv
            print(f"Creating new glossary from {phrases_file}")
            entries = {}
            
            with open(phrases_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['EN'] and row['SV']:  # Only add if both translations exist
                        entries[row['EN']] = row['SV']
            
            if entries:
                self.glossary = self.translator.create_glossary(
                    self.glossary_name,
                    source_lang="EN",
                    target_lang="SV",
                    entries=entries
                )
                print(f"Created glossary with {len(entries)} entries")
            else:
                print("No valid entries found in phrases.csv")
                
        except Exception as e:
            print(f"Error loading/creating glossary: {e}")
            if hasattr(e, 'response'):
                print(f"API Response: {e.response.text if hasattr(e.response, 'text') else e.response}")
    
    def read_rst_file(self, file_path):
        """Read content from an RST file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def get_translatable_content(self, rst_content):
        """Extract translatable content from RST file"""
        lines = rst_content.split('\n')
        translatable_lines = []
        current_line = []
        in_ref = False
        
        for i, line in enumerate(lines):
            line = line.strip()
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
                
            if i < len(lines) - 1:  # Check next line for section headers
                next_line = lines[i + 1].strip()
                if next_line and all(c == '=' for c in next_line):  # Skip section headers
                    continue
                if next_line and all(c == '-' for c in next_line):  # Skip subsection headers
                    continue
                if next_line and all(c == '~' for c in next_line):  # Skip subsubsection headers
                    continue
            if all(c == '=' for c in line) or all(c == '-' for c in line) or all(c == '~' for c in line):
                continue  # Skip section header lines
                
            # Add non-empty lines to current multiline
            if line:
                current_line.append(line)
        
        # Add any remaining lines
        if current_line:
            translatable_lines.append(' '.join(current_line))
        
        return translatable_lines
    
    def normalize_text(self, text):
        """Normalize text by joining multiline strings and standardizing whitespace"""
        if not text:
            return text
        
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
    def translate_text(self, text, source_lang='en', target_lang='sv'):
        """Translate a chunk of text using DeepL with retry logic"""
        if not text or text.strip() == '' or text.strip() == '=':
            return None  # Skip empty lines or separator lines
            
        try:
            # Add a small delay between requests to avoid rate limiting
            time.sleep(1)  # Increased delay to avoid rate limits
            
            # Convert to DeepL language codes (uppercase)
            deepl_source = self.deepl_lang_map.get(source_lang.lower(), source_lang.upper())
            deepl_target = self.deepl_lang_map.get(target_lang.lower(), target_lang.upper())
            
            # Use glossary if available
            if self.glossary:
                result = self.translator.translate_text(
                    text,
                    source_lang=deepl_source,
                    target_lang=deepl_target,
                    preserve_formatting=True,
                    glossary=self.glossary
                )
            else:
                result = self.translator.translate_text(
                    text,
                    source_lang=deepl_source,
                    target_lang=deepl_target,
                    preserve_formatting=True
                )
            return result.text if result else None
            
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

    def analyze_translation_status(self, language_code: str = 'sv', specific_file: str = None) -> Tuple[Dict, float]:
        """
        Analyze the translation status for a specific language.
        Returns a tuple of (file_stats, overall_percentage)
        """
        po_dir = self.po_dir / language_code / "LC_MESSAGES"
        if not po_dir.exists():
            print(f"No translations found for language {language_code}")
            return {}, 0.0
        
        total_strings = 0
        total_translated = 0
        file_stats = {}
        
        # First, get all RST files
        if specific_file:
            rst_files = [self.source_dir / f"{specific_file}.rst"]
            if not rst_files[0].exists():
                print(f"No source file found for {specific_file}")
                return {}, 0.0
        else:
            rst_files = list(self.source_dir.rglob("*.rst"))
        
        # Process each RST file
        for rst_file in rst_files:
            file_stem = rst_file.stem
            po_file = po_dir / f"{file_stem}.po"
            
            try:
                # Get total strings from PO file first
                if po_file.exists():
                    po = polib.pofile(str(po_file))
                    # Only filter out obsolete entries
                    valid_entries = [entry for entry in po if not entry.obsolete]
                    total_entries = len(valid_entries)
                    
                    # Count translated entries (both single and multiline)
                    translated_entries = len([entry for entry in valid_entries 
                                           if (isinstance(entry.msgstr, list) and any(entry.msgstr)) or 
                                              (isinstance(entry.msgstr, str) and entry.msgstr.strip())])
                    
                    if total_entries > 0:
                        percentage = (translated_entries / total_entries) * 100
                    else:
                        percentage = 0.0
                    
                    file_stats[file_stem] = {
                        'total': total_entries,
                        'translated': translated_entries,
                        'percentage': percentage
                    }
                    
                    total_strings += total_entries
                    total_translated += translated_entries
                
            except Exception as e:
                print(f"Error processing {rst_file}: {e}")
        
        overall_percentage = (total_translated / total_strings * 100) if total_strings > 0 else 0.0
        
        return file_stats, overall_percentage
    
    def print_translation_status(self, language_code: str = 'sv', specific_file: str = None):
        """Print a detailed report of translation status"""
        file_stats, overall_percentage = self.analyze_translation_status(language_code, specific_file)
        
        if not file_stats:
            return
        
        print(f"\nTranslation Status for {language_code}:")
        print("-" * 60)
        print(f"{'File':<30} {'Progress':<10} {'Translated':<12} {'Total':<8}")
        print("-" * 60)
        
        for filename, stats in sorted(file_stats.items()):
            # Use simple ASCII characters for progress bar
            blocks = int(stats['percentage'] / 10)
            progress_bar = "#" * blocks + "-" * (10 - blocks)
            print(f"{filename:<30} {progress_bar:<10} {stats['translated']:<12} {stats['total']:<8}")
        
        print("-" * 60)
        print(f"Overall completion: {overall_percentage:.1f}%")
    
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
            entry = po.find(msgid)
            if entry:
                entry.msgstr = msgstr
                updated_entries.add(msgid)
        
        # Second pass: Try to find matches using normalized text
        for msgid, msgstr in translations.items():
            if msgid in updated_entries:
                continue
                
            normalized_msgid = self.normalize_text(msgid)
            found = False
            
            for entry in po:
                normalized_entry_msgid = self.normalize_text(entry.msgid)
                if normalized_entry_msgid == normalized_msgid:
                    entry.msgstr = msgstr
                    found = True
                    break
            
            # If no match found, create a new entry
            if not found:
                entry = polib.POEntry(
                    msgid=msgid,
                    msgstr=msgstr
                )
                po.append(entry)
        
        # Save the file
        po.save(str(po_path))
    
    def process_manual(self, specific_file=None, translate_all=False, debug=False):
        """Process RST files and update PO translations"""
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
                    
                    # Load existing translations and get all entries
                    existing_translations = {}
                    all_entries = []
                    if po_path.exists():
                        po = polib.pofile(po_path)
                        all_entries = [entry for entry in po if not entry.obsolete]
                        if not translate_all:
                            for entry in po:
                                if entry.msgstr:  # Only consider translated entries
                                    normalized_msgid = self.normalize_text(entry.msgid)
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
                    
                    for text in translatable_content:
                        if text and text not in translations:
                            normalized_text = self.normalize_text(text)
                            # Skip if already translated (unless translate_all is True)
                            if normalized_text in existing_translations and not translate_all:
                                translations[text] = existing_translations[normalized_text]
                                skip_count += 1
                                logging.info(f"\nSkipping already translated in {rst_file.stem}: {text}")
                                print(f"\nSkipping already translated: {text[:50]}...")
                                continue
                                
                            try:
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
                                    
                                    translations[text] = translated
                                    success_count += 1
                            except Exception as e:
                                fail_count += 1
                                logging.error(f"\nFailed to translate in {rst_file.stem}: {text}")
                                logging.error(f"Error: {str(e)}")
                                print(f"\nFailed to translate: {text[:50]}...")
                    
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
                            
                        # Also print to console
                        print(f"Successfully translated: {success_count} strings")
                        print(f"Skipped already translated: {skip_count} strings")
                        if fail_count > 0:
                            print(f"Failed to translate: {fail_count} strings")
                        if translate_all:
                            print("Note: --translate-all was enabled, existing translations were replaced with new ones")
                        
                except Exception as e:
                    error_msg = f"Error processing {rst_file}: {e}"
                    logging.error(error_msg)
                    print(error_msg)
                    continue
            
            completion_msg = "\nTranslation process completed successfully"
            logging.info(completion_msg)
            print(completion_msg)
            
        except Exception as e:
            error_msg = f"Error: {e}"
            logging.error(error_msg)
            print(error_msg)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Koha Manual Translation Tool')
    parser.add_argument('--status', action='store_true', help='Show translation status')
    parser.add_argument('--translate', action='store_true', help='Run the translation process')
    parser.add_argument('--lang', default='sv', help='Language code (default: sv)')
    parser.add_argument('--file', help='Process specific file (without .rst extension)')
    parser.add_argument('--all', action='store_true', help='Process all files (required for bulk translation)')
    parser.add_argument('--phrases', default='phrases.csv', help='Path to phrases CSV file (default: phrases.csv)')
    parser.add_argument('--translate-all', action='store_true', help='Translate all strings, even if they already exist in PO file')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with full text output')
    parser.add_argument('--log-file', help='Specify custom log file path (default: log/translation_TIMESTAMP.log)')
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
    po_dir = "repos/koha-manual-l10n"  # PO files location
    
    translator = KohaTranslator(manual_source, po_dir)
    
    if args.translate:
        try:
            # Load glossary before translation
            translator.load_or_create_glossary(args.phrases)
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
            translator.process_manual(args.file, args.translate_all, args.debug)
        except Exception as e:
            error_msg = f"Error during translation process: {e}"
            logging.error(error_msg)
            print(error_msg)
            return
    elif args.status or not args.translate:
        # Just show status if no translation requested
        logging.info(f"Checking translation status for {args.lang}" + (f" file: {args.file}" if args.file else ""))
        translator.print_translation_status(args.lang, args.file)

if __name__ == "__main__":
    main()
