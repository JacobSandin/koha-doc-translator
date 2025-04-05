#!/usr/bin/env python3
"""
Mocking framework for testing translator.py functions

This module provides a framework for testing the functions in translator.py
with various translations without needing to set up the full environment.
It allows you to:
1. Mock the KohaTranslator class and its dependencies
2. Test specific functions in isolation
3. Easily add test cases for different translation scenarios
"""

import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import translator.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the translator module
from translator import KohaTranslator

class MockKohaTranslator(unittest.TestCase):
    """
    Mock class for testing KohaTranslator functions
    
    This class provides methods for testing specific functions in the KohaTranslator
    class without needing to set up the full environment.
    """
    
    def setUp(self):
        """Set up the test environment"""
        # Create a mock instance of KohaTranslator
        self.mock_source_dir = '/mock/source/dir'
        self.mock_po_dir = '/mock/po/dir'
        
        # Create a patched instance of KohaTranslator
        with patch.object(KohaTranslator, '__init__', return_value=None):
            self.translator = KohaTranslator(self.mock_source_dir, self.mock_po_dir)
            
            # Set up any necessary attributes
            self.translator.source_dir = self.mock_source_dir
            self.translator.po_dir = self.mock_po_dir
            self.translator.glossary_id = None
            self.translator.deepl_api_key = 'mock_api_key'
    
    def load_test_cases(self, json_file='rst_test_cases.json'):
        """Load test cases from a JSON file"""
        try:
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), json_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('test_cases', [])
        except Exception as e:
            print(f"Error loading test cases: {e}")
            return []
    
    def test_preserve_rst_references_with_mustache(self):
        """Test the preserve_rst_references_with_mustache function"""
        test_cases = self.load_test_cases()
        
        for test_case in test_cases:
            name = test_case.get('name', 'Unnamed test')
            original_text = test_case.get('original', '')
            
            # Skip PO format tests for this function
            if 'msgid' in original_text and 'msgstr' in original_text:
                continue
                
            # Test the function
            with self.subTest(name=name):
                tagged_text, placeholders = self.translator.preserve_rst_references_with_mustache(original_text)
                
                # Basic verification
                self.assertIsNotNone(tagged_text)
                if ':ref:' in original_text or '|' in original_text or ('`' in original_text and '<' in original_text and '>`' in original_text):
                    self.assertNotEqual(tagged_text, original_text, f"No references were preserved in {name}")
                    self.assertTrue(len(placeholders) > 0, f"No placeholders were created in {name}")
    
    def test_restore_rst_references_from_mustache(self):
        """Test the restore_rst_references_from_mustache function"""
        test_cases = self.load_test_cases()
        
        for test_case in test_cases:
            name = test_case.get('name', 'Unnamed test')
            original_text = test_case.get('original', '')
            translation = test_case.get('translation')
            
            # Skip PO format tests for this function
            if 'msgid' in original_text and 'msgstr' in original_text:
                continue
                
            # Test the function
            with self.subTest(name=name):
                # First preserve the references
                tagged_text, placeholders = self.translator.preserve_rst_references_with_mustache(original_text)
                
                # Then restore them
                if translation:
                    # If we have a translation with issues, we need to modify it to use our placeholders
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
                        
                        restored_text = self.translator.restore_rst_references_from_mustache(modified_translation, placeholders)
                    else:
                        restored_text = self.translator.restore_rst_references_from_mustache(translation, placeholders)
                    
                    # Verify that the references were restored correctly
                    self.assertNotIn(":ref:`<", restored_text, f"References not restored correctly in {name}")
                    self.assertNotIn("{{RST_LABEL_", restored_text, f"Placeholders not restored correctly in {name}")
                else:
                    # If no translation is provided, just test the basic preservation and restoration
                    restored_text = self.translator.restore_rst_references_from_mustache(tagged_text, placeholders)
                    
                    # Verify that the restored text matches the original
                    self.assertEqual(restored_text, original_text, f"Restored text does not match original in {name}")
    
    def test_fix_rst_formatting(self):
        """Test the fix_rst_formatting function"""
        # Test cases specifically for fix_rst_formatting
        test_cases = [
            {
                "name": "Fix italic markers",
                "input": "This is * italic * text with * spacing issues*.",
                "expected": "This is *italic* text with *spacing issues*."
            },
            {
                "name": "Fix bold markers",
                "input": "This is ** bold ** text with ** spacing issues**.",
                "expected": "This is **bold** text with **spacing issues**."
            },
            {
                "name": "Fix missing bold markers",
                "input": "This is **bold text without closing markers.",
                "expected": "This is **bold text without closing markers**."
            },
            {
                "name": "Fix missing italic markers",
                "input": "This is *italic text without closing markers.",
                "expected": "This is *italic text without closing markers*."
            },
            {
                "name": "Fix URL references",
                "input": "See `Koha website<https://koha-community.org/>`_",
                "expected": "See `Koha website <https://koha-community.org/>`_"
            },
            {
                "name": "Fix URL references with HTML entities",
                "input": "See `Koha website &lt;https://koha-community.org/&gt;`_",
                "expected": "See `Koha website <https://koha-community.org/>`_"
            }
        ]
        
        for test_case in test_cases:
            name = test_case.get('name', 'Unnamed test')
            input_text = test_case.get('input', '')
            expected_text = test_case.get('expected', '')
            
            # Test the function
            with self.subTest(name=name):
                fixed_text = self.translator.fix_rst_formatting(input_text)
                self.assertEqual(fixed_text, expected_text, f"fix_rst_formatting failed for {name}")

    def test_with_custom_case(self, original_text, translation=None, expected_output=None):
        """
        Test with a custom case provided by the user
        
        Args:
            original_text: The original text with RST references
            translation: The translated text with issues (optional)
            expected_output: The expected output after restoration (optional)
        """
        # First preserve the references
        tagged_text, placeholders = self.translator.preserve_rst_references_with_mustache(original_text)
        
        print(f"Original text: {original_text}")
        print(f"Tagged text: {tagged_text}")
        print(f"Placeholders: {placeholders}")
        
        if translation:
            # If we have a translation with issues, we need to modify it to use our placeholders
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
                
                print(f"Modified translation: {modified_translation}")
                restored_text = self.translator.restore_rst_references_from_mustache(modified_translation, placeholders)
            else:
                restored_text = self.translator.restore_rst_references_from_mustache(translation, placeholders)
            
            print(f"Restored text: {restored_text}")
            
            if expected_output:
                self.assertEqual(restored_text, expected_output, "Restored text does not match expected output")
            else:
                self.assertNotIn(":ref:`<", restored_text, "References not restored correctly")
                self.assertNotIn("{{RST_LABEL_", restored_text, "Placeholders not restored correctly")
        else:
            # If no translation is provided, just test the basic preservation and restoration
            restored_text = self.translator.restore_rst_references_from_mustache(tagged_text, placeholders)
            
            print(f"Restored text: {restored_text}")
            
            if expected_output:
                self.assertEqual(restored_text, expected_output, "Restored text does not match expected output")
            else:
                self.assertEqual(restored_text, original_text, "Restored text does not match original")

def run_tests():
    """Run all tests"""
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

def run_custom_test(original_text, translation=None, expected_output=None):
    """
    Run a custom test with the provided text
    
    Args:
        original_text: The original text with RST references
        translation: The translated text with issues (optional)
        expected_output: The expected output after restoration (optional)
    """
    test = MockKohaTranslator()
    test.setUp()
    test.test_with_custom_case(original_text, translation, expected_output)

if __name__ == '__main__':
    # If run directly, run all tests
    run_tests()
