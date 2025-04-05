#!/usr/bin/env python3
"""
Example script demonstrating how to use the mocking framework

This script shows how to use the mocking framework to test specific functions
in translator.py with custom test cases.
"""

from tests.mock_translator import MockKohaTranslator, run_custom_test

def main():
    """Main function demonstrating the use of the mocking framework"""
    print("=== Testing with built-in test cases ===")
    # Create an instance of the mock translator
    mock = MockKohaTranslator()
    mock.setUp()
    
    # Run a specific test
    print("\nTesting preserve_rst_references_with_mustache:")
    mock.test_preserve_rst_references_with_mustache()
    
    print("\n=== Testing with custom test cases ===")
    # Test with a custom case
    original_text = "When using the :ref:`item search <item-searching-label>`, you can select items."
    translation = "När du använder :ref:`<item-searching-label>` kan du välja exemplar."
    
    print("\nCustom test case 1:")
    run_custom_test(original_text, translation)
    
    # Test with another custom case
    original_text = "The system preference :ref:`BlockExpiredPatronOpacActions <blockexpiredpatronopacactions-label>` controls what a patron can do after their account has expired."
    translation = "Systeminställningen :ref:`<blockexpiredpatronopacactions-label>` styr vad en låntagare kan göra efter att deras konto har löpt ut."
    
    print("\nCustom test case 2:")
    run_custom_test(original_text, translation)
    
    # Test with a multiline reference
    original_text = """When using the :ref:`item search <item-searching-label>`, you can now select
items and send them directly to the :ref:`batch item modification tool
<batch-item-modification-label>` or to the :ref:`batch item deletion tool
<batch-item-deletion-label>`."""
    translation = """När du använder :ref:`<item-searching-label>` kan du nu välja exemplar
och skicka dem direkt till :ref:`<batch-item-modification-
label>` eller till :ref:`<batch-item-deletion-label>`."""
    
    print("\nCustom test case 3 (multiline):")
    run_custom_test(original_text, translation)

if __name__ == "__main__":
    main()
