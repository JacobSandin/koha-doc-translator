#!/usr/bin/env python3
"""
Test script for RST formatting issues in translations

This script tests for proper spacing after RST formatting markers like **bold:**,
*italic:*, and other Sphinx formatting signs. It only fails if the original text
has a space after the formatting marker but the translated text doesn't.
"""

import os
import sys
import unittest
import re
from translator import KohaTranslator

# Set paths for the translator
source_dir = os.path.join(os.getcwd(), 'repos/koha-manual/source')
po_dir = os.path.join(os.getcwd(), 'repos/koha-manual/locales')

class TestRstFormatting(unittest.TestCase):
    """Test RST formatting in translations"""
    
    def setUp(self):
        """Set up the test environment"""
        # Disable cache to ensure tests don't use cached translations
        self.translator = KohaTranslator(source_dir, po_dir, disable_cache=True)
    
    def check_missing_space_after_formatting(self, original, translated):
        """Check if the original has space after formatting but translated doesn't"""
        # Check for missing space after **Bold:** pattern
        bold_pattern = r'\*\*[^*:]+:\*\*\s'
        bold_pattern_no_space = r'\*\*[^*:]+:\*\*[^\s]'
        
        # Check for missing space after *Italic:* pattern
        italic_pattern = r'\*[^*:]+:\*\s'
        italic_pattern_no_space = r'\*[^*:]+:\*[^\s]'
        
        # Check for missing space after number and formatting
        number_pattern = r'\d+\.\s+\*\*'
        number_pattern_no_space = r'\d+\.\*\*'
        
        # Check if original has space but translated doesn't
        has_issue = False
        
        # Check bold formatting
        if (re.search(bold_pattern, original) and 
            re.search(bold_pattern_no_space, translated)):
            has_issue = True
            
        # Check italic formatting
        if (re.search(italic_pattern, original) and 
            re.search(italic_pattern_no_space, translated)):
            has_issue = True
            
        # Check numbering with formatting
        if (re.search(number_pattern, original) and 
            re.search(number_pattern_no_space, translated)):
            has_issue = True
            
        # Check for missing space after colon in general
        colon_space_pattern = r':\s'
        colon_no_space_pattern = r':[^\s:]'
        
        # Find all colons in original and check if they have spaces after them
        for match in re.finditer(r':', original):
            pos = match.start()
            # Check if there's a space after the colon in original
            if pos + 1 < len(original) and original[pos + 1].isspace():
                # Find corresponding position in translated
                # This is approximate - we count colons up to this position
                colon_count = original[:pos+1].count(':')
                # Find the nth colon in translated
                translated_colons = [m.start() for m in re.finditer(':', translated)]
                if len(translated_colons) >= colon_count:
                    translated_pos = translated_colons[colon_count - 1]
                    # Check if there's no space after this colon in translated
                    if (translated_pos + 1 < len(translated) and 
                        not translated[translated_pos + 1].isspace()):
                        has_issue = True
        
        return has_issue
    
    def test_formatting_spacing(self):
        """Test that formatting has proper spacing after markers"""
        # Test cases with improper spacing after formatting markers
        test_cases = [
            # Original text, Text with formatting issues
            ("**Username:** Enter the username", "**Username:**Ange användarnamnet"),
            ("**Password:** Enter the password", "**Password:**Ange lösenordet"),
            ("**Library:** This is the library", "**Library:**Detta är biblioteket"),
            ("*Get there:* More information", "*Sökväg:*Mer information"),
            ("1. **Username:** Enter", "1.**Username:**Ange"),
            ("options are either: *my library*", "alternativen är antingen:*my library*"),
        ]
        
        for original, translated in test_cases:
            with self.subTest(original=original, translated=translated):
                # Check if there's a missing space after formatting
                has_issue = self.check_missing_space_after_formatting(original, translated)
                
                # If there's an issue, the test should fail
                if has_issue:
                    # Fix the formatting using the translator's method
                    fixed_text = self.translator.fix_rst_formatting(translated)
                    
                    # Check if the issue was fixed
                    has_issue_after_fix = self.check_missing_space_after_formatting(original, fixed_text)
                    
                    # The test should fail if the issue wasn't fixed
                    self.assertFalse(has_issue_after_fix, 
                                    f"RST formatting issue was not fixed:\n"
                                    f"Original: {original}\n"
                                    f"Translated: {translated}\n"
                                    f"Fixed: {fixed_text}\n"
                                    f"Issue: Missing space after formatting marker")
    
    def test_real_world_examples(self):
        """Test real-world examples from the PO files"""
        # Real examples from the PO files
        test_cases = [
            # Original text, Text with formatting issues
            (
                "1. **Username:** Enter the username you created for the patron 2. **Password:** Enter the password you created",
                "1. **Username:**Ange det användarnamn som du skapade för låntagaren 2.**Password:**Ange det lösenord du skapade"
            ),
            (
                "3. **Library:** This is the library staff interface you want to log into. The options are either: *my library*",
                "3.**Library:**Detta är det gränssnitt för bibliotekspersonal som du vill logga in på. Alternativen är antingen:*my library*"
            ),
        ]
        
        for original, translated in test_cases:
            with self.subTest(original=original, translated=translated):
                # Check if there's a missing space after formatting
                has_issue = self.check_missing_space_after_formatting(original, translated)
                
                # If there's an issue, the test should fail
                if has_issue:
                    # Fix the formatting using the translator's method
                    fixed_text = self.translator.fix_rst_formatting(translated)
                    
                    # Check if the issue was fixed
                    has_issue_after_fix = self.check_missing_space_after_formatting(original, fixed_text)
                    
                    # The test should fail if the issue wasn't fixed
                    self.assertFalse(has_issue_after_fix, 
                                    f"RST formatting issue was not fixed:\n"
                                    f"Original: {original}\n"
                                    f"Translated: {translated}\n"
                                    f"Fixed: {fixed_text}\n"
                                    f"Issue: Missing space after formatting marker")

def main():
    """Run the tests"""
    unittest.main()

if __name__ == "__main__":
    main()
