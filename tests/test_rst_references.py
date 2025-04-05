#!/usr/bin/env python3
"""
User-friendly test script for RST reference handling in translator.py

This script reads test cases from a JSON file (rst_test_cases.json) and tests
the RST reference handling in translator.py for each case. This makes it easy
to add new test cases without modifying the script.

To add a new test case:
1. Edit the rst_test_cases.json file
2. Add a new entry to the "test_cases" array with:
   - "name": A descriptive name for the test
   - "original": The original text with RST references
   - "translation": The translated text with issues (or null to test basic preservation)
   - "description": A brief description of what the test is checking

Example:
{
  "name": "My new test",
  "original": "See the :ref:`item-searching-label` for more information.",
  "translation": "See the :ref:`<item-searching-label>` for more information.",
  "description": "Tests handling of missing display text in simple references"
}
"""

import os
import re
import json
import sys
from translator import KohaTranslator

# Set paths for the translator
source_dir = os.path.join(os.getcwd(), 'repos/koha-manual/source')
po_dir = os.path.join(os.getcwd(), 'repos/koha-manual/locales')

# Initialize the translator with cache disabled to ensure tests don't use cached translations
translator = KohaTranslator(source_dir, po_dir, disable_cache=True)

def load_test_cases(json_file=None):
    """Load test cases from a JSON file"""
    if json_file is None:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_file = os.path.join(script_dir, 'rst_test_cases.json')
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('test_cases', [])
    except Exception as e:
        print(f"Error loading test cases: {e}")
        return []

def extract_po_content(text):
    """
    Extract the actual content from a PO file format string
    
    Args:
        text: Text in PO file format (with msgid/msgstr)
        
    Returns:
        tuple: (msgid_content, msgstr_content)
    """
    if not text or 'msgid' not in text:
        return text, None
    
    # Extract msgid content
    msgid_parts = []
    msgstr_parts = []
    current_part = None
    
    for line in text.split('\n'):
        if line.startswith('msgid'):
            current_part = msgid_parts
            # Extract content after msgid
            content = line[5:].strip().strip('"')
            if content:
                msgid_parts.append(content)
        elif line.startswith('msgstr'):
            current_part = msgstr_parts
            # Extract content after msgstr
            content = line[6:].strip().strip('"')
            if content:
                msgstr_parts.append(content)
        elif line.startswith('"') and current_part is not None:
            # Extract content from continuation lines
            content = line.strip().strip('"')
            if content:
                current_part.append(content)
    
    msgid_content = ''.join(msgid_parts)
    msgstr_content = ''.join(msgstr_parts) if msgstr_parts else None
    
    return msgid_content, msgstr_content

def test_reference(test_case):
    """
    Test RST reference handling for a given test case
    
    Args:
        test_case: Dictionary containing test case details
    """
    name = test_case.get('name', 'Unnamed test')
    original_text = test_case.get('original', '')
    translation = test_case.get('translation')
    description = test_case.get('description', '')
    
    print(f"\n{'=' * 80}")
    print(f"TEST: {name}")
    print(f"{'=' * 80}")
    
    if description:
        print(f"Description: {description}\n")
    
    # Check if this is a PO file format test
    is_po_format = 'msgid' in original_text and 'msgstr' in original_text
    
    if is_po_format:
        # Extract the actual content from the PO format
        msgid_content, _ = extract_po_content(original_text)
        _, msgstr_content = extract_po_content(translation) if translation else (None, None)
        
        print("Original text (extracted from msgid):")
        print(msgid_content)
        
        # Process the extracted content
        print("\nPreserving references:")
        tagged_text, placeholders = translator.preserve_rst_references_with_mustache(msgid_content)
        print(tagged_text)
        
        if msgstr_content:
            print("\nTranslated text with issues (extracted from msgstr):")
            print(msgstr_content)
            
            # For the Swedish-style references, we need to convert them to the mustache format
            # before we can restore them
            if '<' in msgstr_content and '>' in msgstr_content:
                modified_translation = msgstr_content
                for pid, data in placeholders.items():
                    if isinstance(data, dict) and data.get('type') == 'complex':
                        label = data.get('label', '')
                        # Replace the Swedish-style reference with the mustache tag format
                        # Handle cases where the label might be split across lines
                        label_parts = label.split('-')
                        if len(label_parts) > 1:
                            # Try different variations of how the label might be split
                            for i in range(1, len(label_parts)):
                                prefix = '-'.join(label_parts[:i])
                                suffix = '-'.join(label_parts[i:])
                                modified_translation = modified_translation.replace(
                                    f":ref:`<{prefix}-\n{suffix}>`", 
                                    f":ref:`{{{{RST_LABEL_{pid}}}}}`"
                                )
                        
                        # Also try the standard format
                        modified_translation = modified_translation.replace(
                            f":ref:`<{label}>`", 
                            f":ref:`{{{{RST_LABEL_{pid}}}}}`"
                        )
                
                print("\nModified translation with mustache tags:")
                print(modified_translation)
                
                print("\nRestoring references:")
                restored_text = translator.restore_rst_references_from_mustache(modified_translation, placeholders)
            else:
                print("\nRestoring references:")
                restored_text = translator.restore_rst_references_from_mustache(msgstr_content, placeholders)
            
            print(restored_text)
            
            print("\nVerification:")
            # Check for unrestored references
            has_unrestored_refs = False
            
            # Check for unrestored complex references
            if ":ref:`<" in restored_text or "{{RST_LABEL_" in restored_text:
                has_unrestored_refs = True
                
            # Check for unrestored URL references
            if "{{RST_URL_" in restored_text:
                has_unrestored_refs = True
                
            # Check for unrestored simple references
            if "{{RST_SIMPLEREF_" in restored_text:
                has_unrestored_refs = True
                
            # Check for unrestored substitution references
            if "{{RST_SUBST_" in restored_text:
                has_unrestored_refs = True
                
            if not has_unrestored_refs:
                print("✅ SUCCESS: References restored correctly")
            else:
                print("❌ FAILURE: References not restored correctly")
        else:
            # If no translation is provided, just test the basic preservation and restoration
            print("\nRestoring references (without simulated issues):")
            restored_text = translator.restore_rst_references_from_mustache(tagged_text, placeholders)
            print(restored_text)
            
            print("\nVerification:")
            if restored_text == msgid_content:
                print("✅ SUCCESS: Restored text matches original text")
            else:
                print("❌ FAILURE: Restored text does not match original text")
    else:
        # Regular text format (not PO file)
        print("Original text:")
        print(original_text)
        
        print("\nPreserving references:")
        tagged_text, placeholders = translator.preserve_rst_references_with_mustache(original_text)
        print(tagged_text)
        
        if translation:
            print("\nTranslated text with issues:")
            print(translation)
            
            # For the Swedish-style references, we need to convert them to the mustache format
            # before we can restore them
            if '<' in translation and '>' in translation:
                modified_translation = translation
                for pid, data in placeholders.items():
                    if isinstance(data, dict) and data.get('type') == 'complex':
                        label = data.get('label', '')
                        # Handle cases where the label might be split across lines
                        label_parts = label.split('-')
                        if len(label_parts) > 1:
                            # Try different variations of how the label might be split
                            for i in range(1, len(label_parts)):
                                prefix = '-'.join(label_parts[:i])
                                suffix = '-'.join(label_parts[i:])
                                modified_translation = modified_translation.replace(
                                    f":ref:`<{prefix}-\n{suffix}>`", 
                                    f":ref:`{{{{RST_LABEL_{pid}}}}}`"
                                )
                        
                        # Also try the standard format
                        modified_translation = modified_translation.replace(
                            f":ref:`<{label}>`", 
                            f":ref:`{{{{RST_LABEL_{pid}}}}}`"
                        )
                
                print("\nModified translation with mustache tags:")
                print(modified_translation)
                
                print("\nRestoring references:")
                restored_text = translator.restore_rst_references_from_mustache(modified_translation, placeholders)
            else:
                print("\nRestoring references:")
                restored_text = translator.restore_rst_references_from_mustache(translation, placeholders)
            
            print(restored_text)
            
            print("\nVerification:")
            # Check for unrestored references
            has_unrestored_refs = False
            
            # Check for unrestored complex references
            if ":ref:`<" in restored_text or "{{RST_LABEL_" in restored_text:
                has_unrestored_refs = True
                
            # Check for unrestored URL references
            if "{{RST_URL_" in restored_text:
                has_unrestored_refs = True
                
            # Check for unrestored simple references
            if "{{RST_SIMPLEREF_" in restored_text:
                has_unrestored_refs = True
                
            # Check for unrestored substitution references
            if "{{RST_SUBST_" in restored_text:
                has_unrestored_refs = True
                
            if not has_unrestored_refs:
                print("✅ SUCCESS: References restored correctly")
            else:
                print("❌ FAILURE: References not restored correctly")
        else:
            # If no translation is provided, just test the basic preservation and restoration
            print("\nRestoring references (without simulated issues):")
            restored_text = translator.restore_rst_references_from_mustache(tagged_text, placeholders)
            print(restored_text)
            
            print("\nVerification:")
            if restored_text == original_text:
                print("✅ SUCCESS: Restored text matches original text")
            else:
                print("❌ FAILURE: Restored text does not match original text")
                print("\nDifferences:")
                for i, (a, b) in enumerate(zip(original_text, restored_text)):
                    if a != b:
                        print(f"Position {i}: '{a}' vs '{b}'")

def main():
    """Main function to run the tests"""
    # Load test cases from JSON file
    test_cases = load_test_cases()
    
    if not test_cases:
        print("No test cases found. Please check the rst_test_cases.json file.")
        return
    
    # Run all tests
    for test_case in test_cases:
        test_reference(test_case)
    
    print(f"\n{'=' * 80}")
    print(f"All tests completed. Tested {len(test_cases)} cases.")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
