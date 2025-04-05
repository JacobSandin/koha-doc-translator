#!/usr/bin/env python3
"""
Test script for URL reference handling in translations

This script tests how URL references are handled in translations.
"""

import os
import sys
import unittest
from translator import KohaTranslator

# Set paths for the translator
source_dir = os.path.join(os.getcwd(), 'repos/koha-manual/source')
po_dir = os.path.join(os.getcwd(), 'repos/koha-manual/locales')

class TestUrlReferences(unittest.TestCase):
    """Test URL reference handling in translations"""
    
    def setUp(self):
        """Set up the test environment"""
        # Disable cache to ensure tests don't use cached translations
        self.translator = KohaTranslator(source_dir, po_dir, disable_cache=True)
    
    def test_url_reference_restoration(self):
        """Test that URL references are properly restored from placeholders"""
        # Original text with URL reference
        original = "The `Koha manual <http://manual.koha-community.org/>`__ is managed by the documentation team."
        
        # First preserve the references
        tagged_text, placeholders = self.translator.preserve_rst_references_with_mustache(original)
        
        # Verify the text was properly tagged
        self.assertIn("{{RST_URL_URL_REF_", tagged_text)
        
        # Simulate a translation with the placeholder
        translation = "Koha-handboken {{RST_URL_URL_REF_0}}`__ hanteras av dokumentationsteamet."
        
        # Restore the references
        restored_text = self.translator.restore_rst_references_from_mustache(translation, placeholders)
        
        # Expected result after restoration
        expected = "Koha-handboken `Koha manual <http://manual.koha-community.org/>`__ hanteras av dokumentationsteamet."
        
        # Check if URL references were properly restored
        self.assertEqual(restored_text, expected, 
                         f"URL references were not properly restored:\n"
                         f"Expected: {expected}\n"
                         f"Got: {restored_text}")
    
    def test_real_world_url_reference(self):
        """Test with the exact real-world example from the PO file"""
        # Original text from the PO file
        original = "The `Koha manual <http://manual.koha-community.org/>`__ is managed by the documentation team, but that doesn't mean we can't all participate in making the best manual possible."
        
        # First preserve the references
        tagged_text, placeholders = self.translator.preserve_rst_references_with_mustache(original)
        
        # Translation with the placeholder issue
        translation = "Koha-handboken {{RST_URL_URL_REF_0}}`__ hanteras av dokumentationsteamet, men det betyder inte att vi inte alla kan delta i att göra den bästa möjliga handboken."
        
        # Restore the references
        restored_text = self.translator.restore_rst_references_from_mustache(translation, placeholders)
        
        # Expected result after restoration
        expected = "Koha-handboken `Koha manual <http://manual.koha-community.org/>`__ hanteras av dokumentationsteamet, men det betyder inte att vi inte alla kan delta i att göra den bästa möjliga handboken."
        
        # Check if URL references were properly restored
        self.assertEqual(restored_text, expected, 
                         f"URL references were not properly restored:\n"
                         f"Expected: {expected}\n"
                         f"Got: {restored_text}")

def main():
    """Run the tests"""
    unittest.main()

if __name__ == "__main__":
    main()
