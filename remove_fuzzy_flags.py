#!/usr/bin/env python3
"""
Script to remove fuzzy flags from PO files in the Koha manual.

This script scans all PO files in the specified directory and removes
any fuzzy flags from the entries. This ensures that all translations
are treated as valid when building the manual.
"""

import os
import glob
import polib
from pathlib import Path

def remove_fuzzy_flags(po_file_path):
    """Remove fuzzy flags from a PO file."""
    try:
        po = polib.pofile(po_file_path)
        changed = False
        fuzzy_count = 0
        
        for entry in po:
            if 'fuzzy' in entry.flags:
                entry.flags.remove('fuzzy')
                changed = True
                fuzzy_count += 1
        
        if changed:
            po.save()
            print(f"Updated {po_file_path}: Removed fuzzy flag from {fuzzy_count} entries")
            return fuzzy_count
        return 0
    except Exception as e:
        print(f"Error processing {po_file_path}: {e}")
        return 0

def main():
    """Main function to process all PO files."""
    # Path to the locales directory
    locales_dir = Path("repos/koha-manual/locales")
    
    # Check if directory exists
    if not locales_dir.exists():
        print(f"Error: Directory {locales_dir} does not exist")
        return
    
    # Process all PO files for Swedish translations
    sv_po_dir = locales_dir / "sv" / "LC_MESSAGES"
    if not sv_po_dir.exists():
        print(f"Error: Directory {sv_po_dir} does not exist")
        return
    
    # Find all PO files
    po_files = list(sv_po_dir.glob("*.po"))
    if not po_files:
        print(f"No PO files found in {sv_po_dir}")
        return
    
    print(f"Found {len(po_files)} PO files to process")
    
    # Process each file
    total_fuzzy_removed = 0
    for po_file in po_files:
        fuzzy_removed = remove_fuzzy_flags(po_file)
        total_fuzzy_removed += fuzzy_removed
    
    print(f"\nProcessing complete. Removed fuzzy flags from {total_fuzzy_removed} entries across {len(po_files)} files.")

if __name__ == "__main__":
    main()
