#!/usr/bin/env python3
"""
Script to find all :ref: instances in RST files, including multi-line references
and consecutive references
"""

import os
import re
from pathlib import Path
import csv
from collections import defaultdict

def find_all_refs(rst_dir):
    """Find all :ref: instances in RST files, including multi-line references"""
    # Dictionary to store results
    refs_by_file = defaultdict(list)
    
    # Regular expressions for finding references
    # This pattern will match both :ref:`label` and :ref:`text<label>` formats
    # Using re.DOTALL to match across line breaks
    ref_pattern = re.compile(r':ref:`([^`]+)`', re.DOTALL)
    
    # Find all RST files
    rst_files = list(Path(rst_dir).rglob("*.rst"))
    print(f"Found {len(rst_files)} RST files to scan")
    
    total_refs = 0
    multi_line_refs = 0
    consecutive_refs = 0
    
    for rst_file in rst_files:
        try:
            # Read the entire file content
            with open(rst_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Find all :ref: instances in the file
                matches = list(ref_pattern.finditer(content))
                
                # Process each match
                for i, match in enumerate(matches):
                    ref_text = match.group(1)
                    
                    # Determine if this is a multi-line reference
                    is_multi_line = '\n' in ref_text
                    if is_multi_line:
                        multi_line_refs += 1
                    
                    # Determine if this is part of consecutive references
                    is_consecutive = False
                    if i > 0:
                        prev_end = matches[i-1].end()
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
                        is_multi_line,
                        is_consecutive
                    ))
                    total_refs += 1
                        
        except Exception as e:
            print(f"Error processing {rst_file}: {e}")
    
    print(f"Found {total_refs} :ref: instances across {len(refs_by_file)} files")
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
    """Write results to a CSV file"""
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["File", "Line Number", "Ref Text"])
        
        for filename, refs in sorted(refs_by_file.items()):
            for line_num, context, ref_text, is_multi_line, is_consecutive in refs:
                # Clean up the reference text
                cleaned_ref = clean_ref_text(ref_text)
                # Format as :ref:`text`
                formatted_ref = f":ref:`{cleaned_ref}`"
                
                writer.writerow([
                    filename, 
                    line_num, 
                    formatted_ref
                ])
    
    print(f"Results written to {output_file}")

def main():
    # Paths
    rst_dir = "repos/koha-manual/source"
    output_file = "all_refs.csv"
    
    # Find all :ref: instances
    print(f"Scanning RST files in {rst_dir}...")
    refs_by_file = find_all_refs(rst_dir)
    
    # Write results to CSV
    write_results_to_csv(refs_by_file, output_file)
    
    # Also print some examples to the console
    print("\nExample :ref: instances:")
    multi_line_examples = 0
    consecutive_examples = 0
    
    # First show some multi-line examples if they exist
    print("\nMulti-line reference examples:")
    for filename, refs in refs_by_file.items():
        for line_num, context, ref_text, is_multi_line, is_consecutive in refs:
            if is_multi_line and multi_line_examples < 5:
                print(f"{os.path.basename(filename)}:{line_num} - {ref_text}")
                multi_line_examples += 1
        if multi_line_examples >= 5:
            break
    
    # Then show some consecutive reference examples
    print("\nConsecutive reference examples:")
    for filename, refs in refs_by_file.items():
        for line_num, context, ref_text, is_multi_line, is_consecutive in refs:
            if is_consecutive and consecutive_examples < 5:
                print(f"{os.path.basename(filename)}:{line_num} - {ref_text}")
                consecutive_examples += 1
        if consecutive_examples >= 5:
            break
    
    print(f"\nSee {output_file} for complete results")

if __name__ == "__main__":
    main()
