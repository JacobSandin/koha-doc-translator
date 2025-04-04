#!/usr/bin/env python3
"""
Script to find all :ref: instances and PascalCase words in RST files, including multi-line references
and consecutive references
"""

import os
import re
from pathlib import Path
import csv
from collections import defaultdict

def find_all_refs(rst_dir):
    """Find all :ref: instances and PascalCase words in RST files"""
    # Dictionary to store results
    refs_by_file = defaultdict(list)
    
    # Regular expressions for finding references
    # This pattern will match both :ref:`label` and :ref:`text<label>` formats
    # Using re.DOTALL to match across line breaks
    ref_pattern = re.compile(r':ref:`([^`]+)`', re.DOTALL)
    
    # Pattern for PascalCase words (starts with capital letter, has at least one lowercase letter)
    # Excludes all-caps words like 'XML' or 'HTML'
    pascal_pattern = re.compile(r'\b([A-Z][a-z]+[A-Z][A-Za-z]*|[A-Z][a-z]*[A-Z][A-Za-z]*)\b')
    
    # Find all RST files
    rst_files = list(Path(rst_dir).rglob("*.rst"))
    print(f"Found {len(rst_files)} RST files to scan")
    
    total_refs = 0
    total_pascal = 0
    multi_line_refs = 0
    consecutive_refs = 0
    
    for rst_file in rst_files:
        try:
            # Read the entire file content
            with open(rst_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Find all :ref: instances in the file
                ref_matches = list(ref_pattern.finditer(content))
                
                # Process each ref match
                for i, match in enumerate(ref_matches):
                    ref_text = match.group(1)
                    
                    # Determine if this is a multi-line reference
                    is_multi_line = '\n' in ref_text
                    if is_multi_line:
                        multi_line_refs += 1
                    
                    # Determine if this is part of consecutive references
                    is_consecutive = False
                    if i > 0:
                        prev_end = ref_matches[i-1].end()
                        current_start = match.start()
                        # If less than 10 characters between references, consider them consecutive
                        if current_start - prev_end < 10:
                            is_consecutive = True
                            consecutive_refs += 1
                    
                    # Get the line number by counting newlines before the match
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # Get context (up to 100 chars before and after)
                    start_context = max(0, match.start() - 100)
                    end_context = min(len(content), match.end() + 100)
                    context = content[start_context:end_context].replace('\n', ' ')
                    
                    # Add to our results with flags for multi-line and consecutive
                    refs_by_file[str(rst_file)].append((
                        line_num, 
                        context, 
                        ref_text,
                        'ref',  # Type of match
                        is_multi_line,
                        is_consecutive
                    ))
                    total_refs += 1
                    
                # Find all PascalCase words
                pascal_matches = list(pascal_pattern.finditer(content))
                
                # Process each PascalCase match
                for match in pascal_matches:
                    pascal_word = match.group(0)
                    
                    # Get the line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # Get context (up to 100 chars before and after)
                    start_context = max(0, match.start() - 100)
                    end_context = min(len(content), match.end() + 100)
                    context = content[start_context:end_context].replace('\n', ' ')
                    
                    # Add to our results
                    refs_by_file[str(rst_file)].append((
                        line_num,
                        context,
                        pascal_word,
                        'pascal',  # Type of match
                        False,     # Not multi-line
                        False      # Not consecutive
                    ))
                    total_pascal += 1
                        
        except Exception as e:
            print(f"Error processing {rst_file}: {e}")
    
    print(f"Found {total_refs} :ref: instances across {len(refs_by_file)} files")
    print(f"Found {total_pascal} PascalCase words")
    print(f"Multi-line references: {multi_line_refs}")
    print(f"Consecutive references: {consecutive_refs}")
    return refs_by_file

def clean_ref_text(text):
    """Clean up reference text by removing linefeeds and extra spaces"""
    # Replace linefeeds and multiple spaces with a single space
    cleaned = re.sub(r'\s+', ' ', text)
    # Trim leading/trailing whitespace
    cleaned = cleaned.strip()
    return cleaned

def write_results_to_csv(refs_by_file, output_file):
    """Write results to a CSV file in the format required for phrases.csv"""
    # Create a set to store unique phrases (to avoid duplicates)
    unique_phrases = set()
    
    # First collect all unique phrases
    for filename, refs in refs_by_file.items():
        for line_num, context, text, match_type, is_multi_line, is_consecutive in refs:
            # Clean up the text
            cleaned_text = clean_ref_text(text)
            
            # Only include PascalCase words
            if match_type == 'pascal':
                unique_phrases.add(cleaned_text)
    
    # Now write to CSV in the required format
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["EN", "SV", "PLURAL"])
        
        # Write each unique phrase
        for phrase in sorted(unique_phrases):
            writer.writerow([
                phrase,  # EN column
                phrase,  # SV column (same as EN for now)
                phrase   # PLURAL column (same as EN for now)
            ])
    
    print(f"Results written to {output_file}")

def main():
    # Paths
    rst_dir = "repos/koha-manual/source"
    output_file = "auto_phrases.csv"
    
    # Find all :ref: instances
    print(f"Scanning RST files in {rst_dir}...")
    refs_by_file = find_all_refs(rst_dir)
    
    # Write results to CSV
    write_results_to_csv(refs_by_file, output_file)
    
    # Also print some examples to the console
    print("\nExample :ref: instances:")
    multi_line_examples = 0
    consecutive_examples = 0
    pascal_examples = 0
    
    # First show some multi-line examples if they exist
    print("\nMulti-line reference examples:")
    for filename, refs in refs_by_file.items():
        for line_num, context, text, match_type, is_multi_line, is_consecutive in refs:
            if match_type == 'ref' and is_multi_line and multi_line_examples < 5:
                print(f"{os.path.basename(filename)}:{line_num} - {text}")
                multi_line_examples += 1
        if multi_line_examples >= 5:
            break
    
    # Then show some consecutive reference examples
    print("\nConsecutive reference examples:")
    for filename, refs in refs_by_file.items():
        for line_num, context, text, match_type, is_multi_line, is_consecutive in refs:
            if match_type == 'ref' and is_consecutive and consecutive_examples < 5:
                print(f"{os.path.basename(filename)}:{line_num} - {text}")
                consecutive_examples += 1
        if consecutive_examples >= 5:
            break
            
    # Show some PascalCase examples
    print("\nPascalCase word examples:")
    for filename, refs in refs_by_file.items():
        for line_num, context, text, match_type, is_multi_line, is_consecutive in refs:
            if match_type == 'pascal' and pascal_examples < 10:
                print(f"{os.path.basename(filename)}:{line_num} - {text}")
                pascal_examples += 1
        if pascal_examples >= 10:
            break
    
    print(f"\nSee {output_file} for complete results")

if __name__ == "__main__":
    main()
