#!/usr/bin/env python3
"""
Script to fix corrupted RST references in PO files
"""

import os
import re
import polib
import argparse
from pathlib import Path

def fix_corrupted_references(po_file_path, dry_run=False, verbose=False):
    """
    Fix corrupted RST references in a PO file
    
    Args:
        po_file_path: Path to the PO file
        dry_run: If True, only show what would be changed without making changes
        verbose: If True, show detailed information about changes
    """
    if not os.path.exists(po_file_path):
        print(f"Error: File not found: {po_file_path}")
        return False
    
    try:
        # Load the PO file
        po = polib.pofile(po_file_path)
        changes_made = False
        
        for entry in po:
            if not entry.msgstr:
                continue
            
            original_msgstr = entry.msgstr
            fixed_msgstr = original_msgstr
            
            # Fix pattern 1: Corrupted complex references with extra characters after the label
            # Example: :ref:`text<label>`y text
            pattern1 = r':ref:`([^<`]+)<([^>`]+)>`([a-zA-Z]+)'
            def fix_pattern1(match):
                return f':ref:`{match.group(1)}<{match.group(2)}`'
            fixed_msgstr = re.sub(pattern1, fix_pattern1, fixed_msgstr)
            
            # Fix pattern 2: Duplicated label parts in complex references
            # Example: :ref:`text<label>`text<label>`
            pattern2 = r':ref:`([^<`]+)<([^>`]+)>`([^<`]*)<\2>`'
            def fix_pattern2(match):
                return f':ref:`{match.group(1)}<{match.group(2)}`{match.group(3)}'
            fixed_msgstr = re.sub(pattern2, fix_pattern2, fixed_msgstr)
            
            # Fix pattern 3: Broken references with text inserted in the middle
            # Example: :ref:`text a:ref:`text
            pattern3 = r':ref:`([^<`]+) a:ref:`'
            def fix_pattern3(match):
                return f':ref:`{match.group(1)}` :ref:`'
            fixed_msgstr = re.sub(pattern3, fix_pattern3, fixed_msgstr)
            
            # Fix pattern 4: Duplicated text after reference
            # Example: :ref:`notices and slips tool <notices-and-slips-label>`ips tool
            pattern4 = r':ref:`([^<`]+)<([^>`]+)>`([a-zA-Z]+\s+[a-zA-Z]+)'
            def fix_pattern4(match):
                # Check if the trailing text is a duplicate of part of the display text
                display_text = match.group(1)
                trailing_text = match.group(3)
                if trailing_text in display_text:
                    return f':ref:`{match.group(1)}<{match.group(2)}`'
                else:
                    return f':ref:`{match.group(1)}<{match.group(2)}` {trailing_text}'
            fixed_msgstr = re.sub(pattern4, fix_pattern4, fixed_msgstr)
            
            # Fix pattern 5: Broken reference with 'ns' suffix
            # Example: :ref:`catalog concerns <manage-catalog-concerns-label>`ns
            pattern5 = r':ref:`([^<`]+)<([^>`]+)>`ns'
            def fix_pattern5(match):
                return f':ref:`{match.group(1)}<{match.group(2)}`'
            fixed_msgstr = re.sub(pattern5, fix_pattern5, fixed_msgstr)
            
            # Fix pattern 6: Temp prefix before reference
            # Example: temp:ref:`notices and slips tool <notices-and-slips-label>`
            pattern6 = r'temp:ref:`([^<`]+)<([^>`]+)>`'
            def fix_pattern6(match):
                return f':ref:`{match.group(1)}<{match.group(2)}`'
            fixed_msgstr = re.sub(pattern6, fix_pattern6, fixed_msgstr)
            
            # Fix pattern 7: Duplicated reference with different formatting
            # Example: :ref:`text<label>` :ref:`text<label>`
            pattern7 = r':ref:`([^<`]+)<([^>`]+)>`\s+:ref:`\1<\2>`'
            def fix_pattern7(match):
                return f':ref:`{match.group(1)}<{match.group(2)}`'
            fixed_msgstr = re.sub(pattern7, fix_pattern7, fixed_msgstr)
            
            # Fix pattern 8: Truncated closing bracket in reference
            # Example: :ref:`text<label`
            pattern8 = r':ref:`([^<`]+)<([^>`]+)`'
            def fix_pattern8(match):
                return f':ref:`{match.group(1)}<{match.group(2)}>`'
            fixed_msgstr = re.sub(pattern8, fix_pattern8, fixed_msgstr)
            
            # Fix pattern 9: Reference with extra text between display and label
            # Example: :ref:`text y <label>`
            pattern9 = r':ref:`([^<`]+)\s+([a-zA-Z]+)\s+<([^>`]+)>`'
            def fix_pattern9(match):
                return f':ref:`{match.group(1)} <{match.group(3)}>`'
            fixed_msgstr = re.sub(pattern9, fix_pattern9, fixed_msgstr)
            
            # Fix pattern 10: Specific case for 'ips tool' suffix
            # Example: :ref:`notices and slips tool <notices-and-slips-label>`ips tool
            pattern10 = r':ref:`([^<`]+)<([^>`]+)>`ips tool'
            def fix_pattern10(match):
                return f':ref:`{match.group(1)}<{match.group(2)}`'
            fixed_msgstr = re.sub(pattern10, fix_pattern10, fixed_msgstr)
            
            # Fix pattern 11: Specific case for 'temp:ref' prefix
            # Example: temp:ref:`notices and slips tool <notices-and-slips-label>` tool
            pattern11 = r'temp:ref:`([^<`]+)<([^>`]+)>`([^<`]*?)'
            def fix_pattern11(match):
                return f':ref:`{match.group(1)}<{match.group(2)}`{match.group(3)}'
            fixed_msgstr = re.sub(pattern11, fix_pattern11, fixed_msgstr)
            
            # Fix pattern 12: Specific case for 'a:ref' prefix
            # Example: a:ref:`catalog concerns <manage-catalog-concerns-label>`
            pattern12 = r'a:ref:`([^<`]+)<([^>`]+)>`'
            def fix_pattern12(match):
                return f':ref:`{match.group(1)}<{match.group(2)}`'
            fixed_msgstr = re.sub(pattern12, fix_pattern12, fixed_msgstr)
            
            # Fix pattern 13: Missing word 'concerns' in catalog concerns reference
            # Example: :ref:`catalog <catalog-concerns-label>`
            pattern13 = r':ref:`catalog <catalog-concerns-label>`'
            fixed_msgstr = fixed_msgstr.replace(':ref:`catalog <catalog-concerns-label>`', ':ref:`catalog concerns <catalog-concerns-label>`')
            
            # Fix pattern 14: Missing word 'slips' in notices reference
            # Example: :ref:`notices and <notices-and-slips-label>`
            pattern14 = r':ref:`notices and <notices-and-slips-label>`'
            fixed_msgstr = fixed_msgstr.replace(':ref:`notices and <notices-and-slips-label>`', ':ref:`notices and slips <notices-and-slips-label>`')
            
            # Fix pattern 15: Double closing bracket with text in between
            # Example: :ref:`text<label>`-text>`
            pattern15 = r':ref:`([^<`]+)<([^>`]+)>`([^<`]*?)-[^<`]*?>`'
            def fix_pattern15(match):
                return f':ref:`{match.group(1)}<{match.group(2)}`{match.group(3)}'
            fixed_msgstr = re.sub(pattern15, fix_pattern15, fixed_msgstr)
            
            # Fix pattern 16: Specific case for ticketresolution-av-category-label
            # Example: :ref:`TICKET_RESOLUTION auktoriserat värde <ticketresolution-av-category-label>`-av-category-label>`
            pattern16 = r':ref:`TICKET\_RESOLUTION ([^<`]+)<ticketresolution-av-category-label>`-av-category-label>`'
            def fix_pattern16(match):
                return f':ref:`TICKET\_RESOLUTION {match.group(1)}<ticketresolution-av-category-label>`'
            fixed_msgstr = re.sub(pattern16, fix_pattern16, fixed_msgstr)
            
            # Fix pattern 17: Specific case for duplicate permission-issue-manage-label
            # Example: :ref:`issue_manage <permission-issue-manage-label>` <permission-issue-manage-label>`
            pattern17 = r':ref:`([^<`]+)<([^>`]+)>` <\2>`'
            def fix_pattern17(match):
                return f':ref:`{match.group(1)}<{match.group(2)}`'
            fixed_msgstr = re.sub(pattern17, fix_pattern17, fixed_msgstr)
            
            # Fix pattern 18: Specific case for membership_expiry.pl
            # Example: :ref:`membership_expiry.pl <cron-notify-patrons-of-expiration-label>`-patrons-of-expiration-label>`
            pattern18 = r':ref:`membership\_expiry\.pl <cron-notify-patrons-of-expiration-label>`-patrons-of-expiration-label>`'
            fixed_msgstr = fixed_msgstr.replace(
                ':ref:`membership\_expiry.pl <cron-notify-patrons-of-expiration-label>`-patrons-of-expiration-label>`', 
                ':ref:`membership\_expiry.pl <cron-notify-patrons-of-expiration-label>`'
            )
            
            # Fix pattern 19: Specific case for notices and slips with duplicate 'tool'
            # Example: :ref:`notices and slips <notices-and-slips-label>` tool
            pattern19 = r':ref:`notices and slips <notices-and-slips-label>` tool'
            fixed_msgstr = fixed_msgstr.replace(
                ':ref:`notices and slips <notices-and-slips-label>` tool', 
                ':ref:`notices and slips <notices-and-slips-label>`'
            )
            
            # Fix pattern 20: Missing 'slips' in notices reference
            # Example: :ref:`notices <notices-and-slips-label>`
            pattern20 = r':ref:`notices <notices-and-slips-label>`'
            fixed_msgstr = fixed_msgstr.replace(
                ':ref:`notices <notices-and-slips-label>`', 
                ':ref:`notices and slips <notices-and-slips-label>`'
            )
            
            # Fix pattern 21: Specific case for TICKET_STATUS
            # Example: :ref:`TICKET_STATUS authorized <ticketstatus-av-category-label>` :ref:`catalog <manage-catalog-concerns-label>` .
            if ':ref:`TICKET\_STATUS authorized <ticketstatus-av-category-label>`' in fixed_msgstr and ':ref:`catalog <manage-catalog-concerns-label>`' in fixed_msgstr:
                fixed_msgstr = fixed_msgstr.replace(
                    ':ref:`TICKET\_STATUS authorized <ticketstatus-av-category-label>`  :ref:`catalog <manage-catalog-concerns-label>` .', 
                    ':ref:`TICKET\_STATUS authorized value category <ticketstatus-av-category-label>` och dessa kommer att visas när du uppdaterar :ref:`catalog concerns <manage-catalog-concerns-label>`.')
            
            # Fix pattern 22: Missing 'concerns' in catalog concerns reference
            # Example: :ref:`catalog <manage-catalog-concerns-label>`
            pattern22 = r':ref:`catalog <manage-catalog-concerns-label>`'
            fixed_msgstr = fixed_msgstr.replace(
                ':ref:`catalog <manage-catalog-concerns-label>`', 
                ':ref:`catalog concerns <manage-catalog-concerns-label>`'
            )
            
            # Fix pattern 23: Notices and slips with 'tool' suffix
            # Example: :ref:`notices and slips <notices-and-slips-label>` tool
            pattern23 = r':ref:`notices and slips <notices-and-slips-label>` tool'
            fixed_msgstr = fixed_msgstr.replace(
                ':ref:`notices and slips <notices-and-slips-label>` tool', 
                ':ref:`notices and slips <notices-and-slips-label>`'
            )
            
            # Fix pattern 24: Specific case for TICKET_STATUS with catalog concerns
            # Example: Du kan nu definiera anpassade statusar i den nya :ref:`TICKET_STATUS <ticketstatus-av-category-label>` :ref:`catalog <manage-catalog-concerns-label>` .
            if ':ref:`TICKET\_STATUS <ticketstatus-av-category-label>`' in fixed_msgstr and ':ref:`catalog concerns <manage-catalog-concerns-label>`' in fixed_msgstr:
                fixed_msgstr = fixed_msgstr.replace(
                    ':ref:`TICKET\_STATUS <ticketstatus-av-category-label>`  :ref:`catalog concerns <manage-catalog-concerns-label>` .', 
                    ':ref:`TICKET\_STATUS authorized value category <ticketstatus-av-category-label>` och dessa kommer att visas när du uppdaterar :ref:`catalog concerns <manage-catalog-concerns-label>`.')
            
            # Fix pattern 25: Specific case for TICKET_RESOLUTION
            # Example: Du kan nu definiera anpassade resolutioner i den nya :ref:`TICKET_RESOLUTION auktoriserat värde <ticketresolution-av-category-label>` :ref:`catalog concerns <manage-catalog-concerns-label>` som "Resolved".
            if ':ref:`TICKET\_RESOLUTION auktoriserat värde <ticketresolution-av-category-label>`' in fixed_msgstr and ':ref:`catalog concerns <manage-catalog-concerns-label>`' in fixed_msgstr:
                fixed_msgstr = fixed_msgstr.replace(
                    ':ref:`TICKET\_RESOLUTION auktoriserat värde <ticketresolution-av-category-label>` :ref:`catalog concerns <manage-catalog-concerns-label>`  som "Resolved".', 
                    ':ref:`TICKET\_RESOLUTION <ticketresolution-av-category-label>` och dessa kommer att visas när du markerar :ref:`catalog concerns <manage-catalog-concerns-label>` som "Resolved".')
            
            # Normalize both strings for comparison by removing extra spaces
            # and standardizing reference formats
            norm_original = re.sub(r'\s+', ' ', original_msgstr).strip()
            norm_fixed = re.sub(r'\s+', ' ', fixed_msgstr).strip()
            
            # Replace variations of the same reference with a standard form for comparison
            norm_original = norm_original.replace('notices and slips tool', 'notices and slips')
            norm_fixed = norm_fixed.replace('notices and slips tool', 'notices and slips')
            
            norm_original = norm_original.replace('TICKET\_RESOLUTION authorized', 'TICKET\_RESOLUTION')
            norm_fixed = norm_fixed.replace('TICKET\_RESOLUTION authorized', 'TICKET\_RESOLUTION')
            
            # If changes were made to this entry (after normalization)
            if norm_fixed != norm_original:
                changes_made = True
                if verbose or dry_run:
                    print(f"\nIn file: {po_file_path}")
                    print(f"Original: {original_msgstr}")
                    print(f"Fixed: {fixed_msgstr}")
                
                if not dry_run:
                    entry.msgstr = fixed_msgstr
        
        # Save the changes if any were made
        if changes_made and not dry_run:
            po.save(po_file_path)
            print(f"Fixed corrupted references in {po_file_path}")
            return True
        elif changes_made and dry_run:
            print(f"Would fix corrupted references in {po_file_path} (dry run)")
            return True
        else:
            if verbose:
                print(f"No corrupted references found in {po_file_path}")
            return False
    
    except Exception as e:
        print(f"Error processing {po_file_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Fix corrupted RST references in PO files')
    parser.add_argument('--file', help='Process a specific PO file')
    parser.add_argument('--dir', default='repos/koha-manual/locales/sv/LC_MESSAGES', 
                        help='Directory containing PO files (default: repos/koha-manual/locales/sv/LC_MESSAGES)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--verbose', action='store_true', help='Show detailed information about changes')
    args = parser.parse_args()
    
    if args.file:
        # Process a single file
        fix_corrupted_references(args.file, args.dry_run, args.verbose)
    else:
        # Process all PO files in the directory
        po_dir = Path(args.dir)
        if not po_dir.exists() or not po_dir.is_dir():
            print(f"Error: Directory not found: {po_dir}")
            return
        
        fixed_count = 0
        total_count = 0
        
        for po_file in po_dir.glob('*.po'):
            total_count += 1
            if fix_corrupted_references(po_file, args.dry_run, args.verbose):
                fixed_count += 1
        
        if args.dry_run:
            print(f"\nWould fix corrupted references in {fixed_count} of {total_count} PO files (dry run)")
        else:
            print(f"\nFixed corrupted references in {fixed_count} of {total_count} PO files")

if __name__ == "__main__":
    main()
