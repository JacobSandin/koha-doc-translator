#!/usr/bin/env python3
"""
Improved status reporting for Koha manual translation
This script analyzes the translation status by comparing RST source files with PO files
to identify:
1. RST files without corresponding PO files
2. Content in RST files that isn't included in PO files
"""

import os
import glob
from pathlib import Path
import polib
import re
import argparse
from typing import Dict, List, Set, Tuple
import sys

class TranslationStatusAnalyzer:
    def __init__(self, source_dir, po_dir):
        """Initialize with source and PO directories"""
        self.source_dir = Path(source_dir)
        self.po_dir = Path(po_dir)
        
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
    
    def analyze_translation_status(self, language_code: str = 'sv', specific_file: str = None) -> Tuple[Dict, float, List[str], Dict]:
        """
        Analyze the translation status for a specific language.
        Returns a tuple of:
        - file_stats: Dictionary with translation stats for each file
        - overall_percentage: Overall translation percentage
        - missing_po_files: List of RST files without corresponding PO files
        - missing_content: Dictionary of content in RST files not in PO files
        """
        po_dir = self.po_dir / language_code / "LC_MESSAGES"
        if not po_dir.exists():
            print(f"No translations found for language {language_code}")
            return {}, 0.0, [], {}
        
        total_strings = 0
        total_translated = 0
        file_stats = {}
        missing_po_files = []
        missing_content = {}
        
        # First, get all RST files
        if specific_file:
            rst_files = [self.source_dir / f"{specific_file}.rst"]
            if not rst_files[0].exists():
                print(f"No source file found for {specific_file}")
                return {}, 0.0, [], {}
        else:
            rst_files = list(self.source_dir.rglob("*.rst"))
        
        # Process each RST file
        for rst_file in rst_files:
            file_stem = rst_file.stem
            po_file = po_dir / f"{file_stem}.po"
            
            # Check if PO file exists
            if not po_file.exists():
                missing_po_files.append(str(rst_file.relative_to(self.source_dir)))
                continue
                
            try:
                # Extract translatable content from RST file
                with open(rst_file, 'r', encoding='utf-8') as f:
                    rst_content = f.read()
                
                translatable_strings = self.get_translatable_content(rst_content)
                normalized_rst_strings = {self.normalize_text(s) for s in translatable_strings if s.strip()}
                
                # Get content from PO file
                po = polib.pofile(str(po_file))
                valid_entries = [entry for entry in po if not entry.obsolete]
                total_entries = len(valid_entries)
                
                # Count translated entries
                translated_entries = len([entry for entry in valid_entries 
                                       if (isinstance(entry.msgstr, list) and any(entry.msgstr)) or 
                                          (isinstance(entry.msgstr, str) and entry.msgstr.strip())])
                
                # Get normalized msgids from PO file
                normalized_po_msgids = {self.normalize_text(entry.msgid) for entry in valid_entries}
                
                # Find content in RST but not in PO
                missing_strings = normalized_rst_strings - normalized_po_msgids
                if missing_strings:
                    missing_content[file_stem] = list(missing_strings)
                
                # Calculate percentage
                if total_entries > 0:
                    percentage = (translated_entries / total_entries) * 100
                else:
                    percentage = 0.0
                
                file_stats[file_stem] = {
                    'total': total_entries,
                    'translated': translated_entries,
                    'percentage': percentage,
                    'rst_strings': len(normalized_rst_strings),
                    'po_strings': len(normalized_po_msgids),
                    'missing_strings': len(missing_strings) if missing_strings else 0
                }
                
                total_strings += total_entries
                total_translated += translated_entries
                
            except Exception as e:
                print(f"Error processing {rst_file}: {e}")
        
        overall_percentage = (total_translated / total_strings * 100) if total_strings > 0 else 0.0
        
        return file_stats, overall_percentage, missing_po_files, missing_content
    
    def print_translation_status(self, language_code: str = 'sv', specific_file: str = None):
        """Print a detailed report of translation status"""
        file_stats, overall_percentage, missing_po_files, missing_content = self.analyze_translation_status(language_code, specific_file)
        
        if not file_stats and not missing_po_files:
            return
        
        print(f"\nTranslation Status for {language_code}:")
        print("-" * 80)
        
        # Print file statistics including missing PO files
        print(f"{'File':<30} {'Progress':<10} {'Translated':<12} {'Total':<8} {'Missing':<8}")
        print("-" * 80)
        
        # First add the missing PO files to the stats with 0 translated
        for rst_file in sorted(missing_po_files):
            # Get the filename without extension
            filename = Path(rst_file).stem
            # Add to the table with 0 translated strings
            # Estimate total strings by counting in the RST file
            try:
                rst_path = self.source_dir / rst_file
                with open(rst_path, 'r', encoding='utf-8') as f:
                    rst_content = f.read()
                translatable_strings = self.get_translatable_content(rst_content)
                total_strings = len([s for s in translatable_strings if s.strip()])
            except Exception:
                total_strings = 0
                
            progress_bar = "-" * 10  # Empty progress bar
            print(f"{filename:<30} {progress_bar:<10} {'0':<12} {total_strings:<8} {'(all)':<8}")
        
        # Then print the existing PO files
        for filename, stats in sorted(file_stats.items()):
            # Use simple ASCII characters for progress bar
            blocks = int(stats['percentage'] / 10)
            progress_bar = "#" * blocks + "-" * (10 - blocks)
            missing = stats.get('missing_strings', 0)
            missing_indicator = f"({missing})" if missing > 0 else ""
            print(f"{filename:<30} {progress_bar:<10} {stats['translated']:<12} {stats['total']:<8} {missing_indicator:<8}")
        
        print("-" * 80)
        
        # Recalculate overall percentage including missing files
        total_all = sum(stats['total'] for stats in file_stats.values())
        translated_all = sum(stats['translated'] for stats in file_stats.values())
        # Add the missing files (with 0 translated)
        if missing_po_files:
            total_missing_strings = 0
            for rst_file in missing_po_files:
                try:
                    rst_path = self.source_dir / rst_file
                    with open(rst_path, 'r', encoding='utf-8') as f:
                        rst_content = f.read()
                    translatable_strings = self.get_translatable_content(rst_content)
                    total_missing_strings += len([s for s in translatable_strings if s.strip()])
                except Exception:
                    pass
            
            total_all += total_missing_strings
            
        overall_percentage = (translated_all / total_all * 100) if total_all > 0 else 0.0
        print(f"Overall completion: {overall_percentage:.1f}%")
        
        # Print details of missing content
        if missing_content and not specific_file:
            print("\nFiles with content in RST not included in PO files:")
            for filename, strings in sorted(missing_content.items()):
                print(f"  - {filename}: {len(strings)} strings missing")
        
        # If specific file is requested and has missing content, show the actual missing strings
        if specific_file and specific_file in missing_content:
            print(f"\nMissing content in {specific_file}.rst (not in PO file):")
            for i, string in enumerate(missing_content[specific_file], 1):
                # Truncate long strings for display
                display_string = string[:100] + "..." if len(string) > 100 else string
                print(f"  {i}. {display_string}")

def main():
    parser = argparse.ArgumentParser(description='Improved Koha Manual Translation Status Tool')
    parser.add_argument('--lang', default='sv', help='Language code (default: sv)')
    parser.add_argument('--file', help='Check specific file (without .rst extension)')
    parser.add_argument('--source-dir', default='repos/koha-manual/source', help='Path to RST source files')
    parser.add_argument('--po-dir', default='repos/koha-manual/locales', help='Path to PO files directory')
    
    args = parser.parse_args()
    
    # Check if directories exist
    source_dir = Path(args.source_dir)
    po_dir = Path(args.po_dir)
    
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)
    
    if not po_dir.exists():
        print(f"Error: PO directory {po_dir} does not exist")
        sys.exit(1)
    
    analyzer = TranslationStatusAnalyzer(source_dir, po_dir)
    analyzer.print_translation_status(args.lang, args.file)

if __name__ == "__main__":
    main()
