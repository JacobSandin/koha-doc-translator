# Koha Doc Translator Testing Framework

This directory contains a comprehensive testing framework for the Koha Doc Translator, focusing particularly on RST reference handling in translations.

## Overview

The testing framework is designed to help verify that RST references are correctly preserved and restored during the translation process. It addresses several common issues:

1. Complex references with display text and label (`:ref:`text<label>`)
2. Simple references with just a label (`:ref:`label`)
3. References with missing display text (`:ref:`<label>`)
4. References that span multiple lines in PO files
5. URL references (`` `text <url>`_ ``)
6. Substitution references (`|name|`)
7. Various edge cases like extra spaces, broken references, etc.

## Files in the Testing Framework

- **test_rst_references.py**: The main test script that reads test cases from the JSON file and tests RST reference handling.
- **rst_test_cases.json**: Contains test cases for various RST reference scenarios.
- **mock_translator.py**: A mocking framework for testing specific functions in translator.py without needing the full environment.
- **example_test.py**: Example script demonstrating how to use the mocking framework.
- **add_test_case.py**: Utility script for adding new test cases to the JSON file.

## How to Use the Testing Framework

### Running All Tests

The easiest way to run all tests is to use the `run_tests.py` script in the root directory:

```bash
# Run all tests with minimal output (just pass/fail status)
cd /home/jacsan/utv/git/koha-doc-translator
python run_tests.py

# Run all tests with detailed debug output
python run_tests.py --debug
```

This script will automatically run all test modules in the tests directory, including:
- The mocking framework tests
- The RST reference tests
- Any example tests

By default, the script only shows which tests are being run and whether they pass or fail. Use the `--debug` option to see detailed output from each test, which is helpful when diagnosing issues.

### Running Individual Test Scripts

If you want to run specific test scripts individually:

```bash
# Run the RST reference tests
cd /home/jacsan/utv/git/koha-doc-translator
python -m tests.test_rst_references

# Run the mocking framework tests
python -m tests.mock_translator

# Run the example tests
python -m tests.example_test
```

### Adding New Test Cases

You can add new test cases to the JSON file using the utility script:

```bash
# Basic example
cd /home/jacsan/utv/git/koha-doc-translator
python -m tests.add_test_case --name "My Test" --original "Original text with :ref:`references <label>`" --translation "Translated text with :ref:`<label>`" --description "Description of the test"

# Example with a complex reference
python -m tests.add_test_case \
  --name "Complex Reference Test" \
  --original "When using the :ref:`item search <item-searching-label>`, you can select items." \
  --translation "När du använder :ref:`<item-searching-label>` kan du välja exemplar." \
  --description "Tests handling of missing display text in complex references"

# Example with a multiline reference
python -m tests.add_test_case \
  --name "Multiline Reference Test" \
  --original "When using the :ref:`item search <item-searching-label>`, you can now select\nitems and send them directly to the :ref:`batch item modification tool\n<batch-item-modification-label>`." \
  --translation "När du använder :ref:`<item-searching-label>` kan du nu välja exemplar\noch skicka dem direkt till :ref:`<batch-item-modification-\nlabel>`." \
  --description "Tests handling of references that span multiple lines"

# Example with a PO file format
python -m tests.add_test_case \
  --name "PO File Format Test" \
  --original 'msgid ""\n"When using the :ref:`item search <item-searching-label>`, you can now select"\nmsgstr ""' \
  --translation 'msgid ""\n"When using the :ref:`item search <item-searching-label>`, you can now select"\nmsgstr ""\n"När du använder :ref:`<item-searching-label>` kan du nu välja exemplar"' \
  --description "Tests handling of PO file format with msgid/msgstr"
```

### Creating Custom Tests

You can create your own test scripts using the mocking framework:

```python
# test_custom.py
from tests.mock_translator import MockKohaTranslator, run_custom_test

# Test with a basic example
original_text = "Text with :ref:`reference <label>`"
translation = "Text with :ref:`<label>`"
run_custom_test(original_text, translation)

# Test with a real example from the Koha documentation
original_text = "The system preference :ref:`BlockExpiredPatronOpacActions <blockexpiredpatronopacactions-label>` controls what a patron can do after their account has expired."
translation = "Systeminställningen :ref:`<blockexpiredpatronopacactions-label>` styr vad en låntagare kan göra efter att deras konto har löpt ut."
run_custom_test(original_text, translation)

# Test with a specific expected output
original_text = "See the :ref:`notices and slips <notices-and-slips-label>` tool."
translation = "Se verktyget :ref:`<notices-and-slips-label>`."
expected_output = "Se verktyget :ref:`notices and slips <notices-and-slips-label>`."
run_custom_test(original_text, translation, expected_output)
```

To run your custom test script:

```bash
cd /home/jacsan/utv/git/koha-doc-translator
python -m tests.test_custom  # assuming you saved the script as test_custom.py in the tests directory
```

### Testing Specific Functions

You can also test specific functions in the translator.py file:

```python
# test_specific_function.py
from tests.mock_translator import MockKohaTranslator

# Create a mock translator instance
mock = MockKohaTranslator()
mock.setUp()

# Test the fix_rst_formatting function
text_with_issues = "This is * italic * text with ** bold ** markers."
fixed_text = mock.translator.fix_rst_formatting(text_with_issues)
print(f"Original: {text_with_issues}")
print(f"Fixed: {fixed_text}")

# Test the preserve_rst_references_with_mustache function
text_with_refs = "See the :ref:`item-searching-label` for more information."
tagged_text, placeholders = mock.translator.preserve_rst_references_with_mustache(text_with_refs)
print(f"Original: {text_with_refs}")
print(f"Tagged: {tagged_text}")
print(f"Placeholders: {placeholders}")
```

To run this script:

```bash
cd /home/jacsan/utv/git/koha-doc-translator
python -m tests.test_specific_function  # assuming you saved the script as test_specific_function.py in the tests directory
```

## RST Reference Issues Addressed

The testing framework specifically addresses the following issues with RST references in translations:

### 1. Missing Display Text in Complex References

**Problem**: In some translations (particularly Swedish), the display text in complex references is missing, resulting in references like `:ref:`<label>`` instead of `:ref:`text<label>``

**Solution**: The `restore_rst_references_from_mustache` method in translator.py has been enhanced to detect and fix this issue by restoring the original display text.

### 2. Multiline References in PO Files

**Problem**: RST references often span multiple lines in PO files, which can complicate the preservation and restoration process.

**Solution**: The testing framework includes test cases with multiline references and the code has been improved to handle these cases correctly.

### 3. URL References with HTML Entities

**Problem**: URL references sometimes have HTML entities (e.g., `&lt;` and `&gt;`) instead of actual angle brackets.

**Solution**: The `fix_rst_formatting` method in translator.py includes fixes for URL references with HTML entities.

## Example Test Cases

The `rst_test_cases.json` file includes various test cases for different scenarios, such as:

- Basic complex references
- Simple references
- Multiple references in the same text
- URL references
- Substitution references
- References with missing display text
- References with extra spaces
- Broken references with missing closing backticks
- Multiline references in PO files
- Real PO file examples

## Fixing RST References in Translations

When you run the translator with the `--translate` option, it will automatically apply the fixes for RST references:

```bash
python translator.py --translate --file whatsnew
```

This will ensure that RST references are correctly preserved and restored in the translated text, even if the translator (e.g., DeepL) modifies or removes parts of the references.

## Adding Your Own Test Cases

If you encounter new issues with RST references in translations, you can add them as test cases to help verify that the fixes work correctly:

1. Use the `add_test_case.py` script to add the test case to the JSON file
2. Run the tests to verify that the issue is correctly handled
3. If needed, modify the code in translator.py to fix the issue

## Troubleshooting

If you encounter issues with the testing framework or RST references in translations, try the following:

1. Check the log file for any error messages
2. Run the tests with specific test cases to isolate the issue
3. Use the mocking framework to test specific functions in isolation
4. Check the PO file for any unusual formatting or structure

If you need to modify the code to fix a new issue, make sure to add test cases that verify the fix works correctly.
