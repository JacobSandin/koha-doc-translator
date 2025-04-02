#!/usr/bin/env python3
"""
Script to extract the display text from :ref: tags in RST files
(the part between :ref:` and the first <)
"""

import os
import re
from pathlib import Path

def extract_display_text(ref_text):
    """Extract the display text from a :ref: tag"""
    # Find the position of the first <
    pos = ref_text.find('<')
    
    # If < is found, extract everything before it
    if pos > 0:
        text = ref_text[:pos].strip()
    else:
        # If no < is found, it's a simple reference where the label is the display text
        text = ref_text.strip()
    
    return text

def clean_text_for_csv(text):
    """Clean up text for CSV output by removing newlines and extra spaces"""
    # Replace newlines and multiple spaces with a single space
    cleaned = re.sub(r'\s+', ' ', text)
    return cleaned.strip()

def find_ref_display_texts(rst_dir):
    """Find all :ref: instances in RST files and extract their display text"""
    # List to store all display texts
    display_texts = []
    
    # Regular expressions for finding references
    # This pattern captures the text between :ref:` and `
    ref_pattern = re.compile(r':ref:`([^`]+)`', re.DOTALL)
    
    # Find all RST files
    rst_files = list(Path(rst_dir).rglob("*.rst"))
    print(f"Found {len(rst_files)} RST files to scan")
    
    total_refs = 0
    
    for rst_file in rst_files:
        try:
            # Read the entire file content
            with open(rst_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Find all :ref: instances in the file
                matches = list(ref_pattern.finditer(content))
                
                # Process each match
                for match in matches:
                    ref_text = match.group(1)
                    display_text = extract_display_text(ref_text)
                    display_texts.append(display_text)
                    total_refs += 1
                        
        except Exception as e:
            print(f"Error processing {rst_file}: {e}")
    
    print(f"Found {total_refs} :ref: instances across {len(rst_files)} files")
    return display_texts

def main():
    # Path to RST files
    rst_dir = "repos/koha-manual/source"
    output_txt_file = "ref_display_text.txt"
    output_csv_file = "ref_phrases.csv"
    
    # Find all :ref: display texts
    print(f"Scanning RST files in {rst_dir}...")
    display_texts = find_ref_display_texts(rst_dir)
    
    # Load existing entries from ref_phrases.csv if it exists
    existing_entries = set()
    if os.path.exists(output_csv_file):
        try:
            print(f"Loading existing entries from {output_csv_file}...")
            with open(output_csv_file, 'r', encoding='utf-8') as f:
                import csv
                reader = csv.reader(f)
                next(reader)  # Skip header row
                for row in reader:
                    if row and len(row) > 0:
                        existing_entries.add(row[0].strip())
            print(f"Loaded {len(existing_entries)} existing entries")
        except Exception as e:
            print(f"Error loading existing entries: {e}")
    
    # Remove duplicates while preserving order
    unique_texts = []
    seen = set()
    for text in display_texts:
        cleaned_text = clean_text_for_csv(text)
        if cleaned_text not in seen and cleaned_text not in existing_entries:
            seen.add(cleaned_text)
            unique_texts.append(cleaned_text)
    
    # Write the unique display texts to the text file
    with open(output_txt_file, 'w', encoding='utf-8') as f:
        for text in unique_texts:
            f.write(text + '\n')
    
    # Append the new unique display texts to the CSV file
    mode = 'a' if os.path.exists(output_csv_file) else 'w'
    with open(output_csv_file, mode, encoding='utf-8', newline='') as f:
        import csv
        writer = csv.writer(f)
        if mode == 'w':  # Only write header for new file
            writer.writerow(["EN", "SV", "PL"])  # Header row
        for text in unique_texts:
            writer.writerow([text, text, text])  # Same value for all three columns
    
    print(f"Found {len(display_texts)} total display texts")
    print(f"Added {len(unique_texts)} new unique entries to {output_csv_file}")
    print(f"Skipped {len(seen) - len(unique_texts)} duplicates within current scan")
    print(f"Skipped {len([t for t in seen if clean_text_for_csv(t) in existing_entries])} entries that already exist in {output_csv_file}")
    print(f"Extracted {len(unique_texts)} unique display texts to {output_txt_file}")
    print(f"Created CSV file {output_csv_file} with {len(unique_texts)} entries")
    print(f"Removed {len(display_texts) - len(unique_texts)} duplicates")
    
    # Also print some examples to the console
    print("\nExample display texts:")
    for i, text in enumerate(unique_texts[:10]):
        print(f"{i+1}. {text}")
    
    print(f"\nSee {output_txt_file} for complete text list")
    print(f"See {output_csv_file} for CSV format")

if __name__ == "__main__":
    main()
