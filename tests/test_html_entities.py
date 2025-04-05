#!/usr/bin/env python3
"""
Test script for HTML entity handling in translations

This script tests how HTML entities are handled in translations.
"""

import os
import sys
import unittest
from translator import KohaTranslator

# Set paths for the translator
source_dir = os.path.join(os.getcwd(), 'repos/koha-manual/source')
po_dir = os.path.join(os.getcwd(), 'repos/koha-manual/locales')

class TestHtmlEntities(unittest.TestCase):
    """Test HTML entity handling in translations"""
    
    def setUp(self):
        """Set up the test environment"""
        # Disable cache to ensure tests don't use cached translations
        self.translator = KohaTranslator(source_dir, po_dir, disable_cache=True)
    
    def test_html_entity_conversion(self):
        """Test that HTML entities are properly converted back to their original characters"""
        # Original text with > characters
        original = "For example: *Get there:* More > Administration > System preferences"
        
        # Translation with HTML entities
        translation = "Till exempel: *Sökväg:* Mer &gt; Administration &gt; Systeminställningar*"
        
        # What the translation should be after processing
        expected = "Till exempel: *Sökväg:* Mer > Administration > Systeminställningar*"
        
        # Process the translation
        processed = self.translator.convert_html_entities(translation)
        
        # Check if HTML entities were properly converted
        self.assertEqual(processed, expected, 
                         f"HTML entities were not properly converted:\n"
                         f"Expected: {expected}\n"
                         f"Got: {processed}")
    
    def test_other_html_entities(self):
        """Test other common HTML entities"""
        test_cases = [
            # Translation with entities, Expected result
            ("A &amp; B", "A & B"),
            ("A &lt; B", "A < B"),
            ("A &gt; B", "A > B"),
            ("A &amp; B &lt; C &gt; D", "A & B < C > D"),
            ("A &quot;quoted&quot; text", "A \"quoted\" text"),
            ("A &apos;quoted&apos; text", "A 'quoted' text"),
        ]
        
        for translation, expected in test_cases:
            with self.subTest(translation=translation):
                processed = self.translator.convert_html_entities(translation)
                self.assertEqual(processed, expected, 
                                f"HTML entities were not properly converted:\n"
                                f"Translation: {translation}\n"
                                f"Expected: {expected}\n"
                                f"Got: {processed}")

def main():
    """Run the tests"""
    unittest.main()

if __name__ == "__main__":
    main()
