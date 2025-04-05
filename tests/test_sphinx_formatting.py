#!/usr/bin/env python3
"""
Test script for Sphinx formatting issues in translations

This script specifically tests for proper spacing after Sphinx formatting markers
like **Bold:** in translations.
"""

import os
import sys
import unittest
import re
from translator import KohaTranslator

# Set paths for the translator
source_dir = os.path.join(os.getcwd(), 'repos/koha-manual/source')
po_dir = os.path.join(os.getcwd(), 'repos/koha-manual/locales')

class TestSphinxFormatting(unittest.TestCase):
    """Test Sphinx formatting in translations"""
    
    def setUp(self):
        """Set up the test environment"""
        # Disable cache to ensure tests don't use cached translations
        self.translator = KohaTranslator(source_dir, po_dir, disable_cache=True)
    
    def test_fix_rst_formatting(self):
        """Test the fix_rst_formatting method for adding space after formatting markers"""
        test_cases = [
            # Text with issues, Expected result
            ("**Username:**Ange", "**Username:** Ange"),
            ("**Password:**Ange", "**Password:** Ange"),
            ("**Library:**Detta", "**Library:** Detta"),
            ("1. **Username:**Ange", "1. **Username:** Ange"),
            ("2.**Password:**Ange", "2. **Password:** Ange"),
            ("*Sökväg:*Mer", "*Sökväg:* Mer"),
            ("*Alternativ:*Välj", "*Alternativ:* Välj"),
        ]
        
        for text_with_issues, expected in test_cases:
            with self.subTest(text_with_issues=text_with_issues):
                # Test the fix_rst_formatting method
                fixed_text = self.translator.fix_rst_formatting(text_with_issues)
                
                # Check if the spacing was properly fixed
                self.assertEqual(fixed_text, expected, 
                                f"RST formatting was not properly fixed:\n"
                                f"Text with issues: {text_with_issues}\n"
                                f"Expected: {expected}\n"
                                f"Got: {fixed_text}")
    
    def test_italic_colon_spacing(self):
        """Test that italic text followed by colon has proper spacing after it"""
        test_cases = [
            # Original text, Text with issues, Expected result
            ("*Get there:* More", "*Sökväg:*Mer", "*Sökväg:* Mer"),
            ("*Options:* Select", "*Alternativ:*Välj", "*Alternativ:* Välj"),
        ]
        
        for original, text_with_issues, expected in test_cases:
            with self.subTest(original=original, text_with_issues=text_with_issues):
                # Fix the formatting using the translator's method
                fixed_text = self.translator.fix_rst_formatting(text_with_issues)
                
                # Check if the formatting was properly fixed
                self.assertEqual(fixed_text, expected, 
                                f"Sphinx formatting was not properly fixed:\n"
                                f"Original: {original}\n"
                                f"Text with issues: {text_with_issues}\n"
                                f"Expected: {expected}\n"
                                f"Got: {fixed_text}")
    
    def test_real_world_examples(self):
        """Test real-world examples from the PO files"""
        test_cases = [
            # Original text, Text with issues, Expected result
            (
                "1. **Username:** Enter the username you created for the patron 2. **Password:** Enter the password you created",
                "1. **Username:**Ange det användarnamn som du skapade för låntagaren 2.**Password:**Ange det lösenord du skapade",
                "1. **Username:** Ange det användarnamn som du skapade för låntagaren 2. **Password:** Ange det lösenord du skapade"
            ),
            (
                "3. **Library:** This is the library staff interface you want to log into.",
                "3.**Library:**Detta är det gränssnitt för bibliotekspersonal som du vill logga in på.",
                "3. **Library:** Detta är det gränssnitt för bibliotekspersonal som du vill logga in på."
            ),
        ]
        
        for original, text_with_issues, expected in test_cases:
            with self.subTest(original=original, text_with_issues=text_with_issues):
                # Fix the formatting using the translator's method
                fixed_text = self.translator.fix_rst_formatting(text_with_issues)
                
                # Check if the formatting was properly fixed
                self.assertEqual(fixed_text, expected, 
                                f"Sphinx formatting was not properly fixed:\n"
                                f"Original: {original}\n"
                                f"Text with issues: {text_with_issues}\n"
                                f"Expected: {expected}\n"
                                f"Got: {fixed_text}")

def main():
    """Run the tests"""
    unittest.main()

if __name__ == "__main__":
    main()
