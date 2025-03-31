# How the Koha Manual Translation Process Works

This document explains how the Koha Manual translation process works in a way that's easy to understand for librarians and non-technical users.

## Overview

The Koha Manual Translator is a tool that automatically translates the Koha Manual from English to Swedish using the DeepL translation service. It's designed to preserve the special formatting and technical terms found in the manual while creating high-quality translations.

## The Translation Workflow

Here's what happens when you run the translation tool:

### 1. Preparation

Before translation begins, the tool:

- **Sets up the necessary files**: The tool works with two main sets of files:
  - The original English manual files (in RST format)
  - The translation files (in PO format) where translations are stored

- **Loads the glossary**: A glossary of Koha-specific terms is loaded to ensure consistent translations. For example, the term "patron" is always translated as "låntagare" in Swedish.

### 2. Reading the Source Files

The tool reads through the English manual files and carefully identifies what text should be translated:

- **Identifies what to translate**: The tool is smart about what it translates:
  - It translates the main content text
  - It skips formatting codes and special instructions
  - It preserves section headers and references
  - It recognizes when text spans multiple lines

- **Prepares text for translation**: Before sending text to be translated, the tool:
  - Joins multi-line paragraphs
  - Standardizes spacing
  - Preserves special references and links

### 3. Translation Process

Once the tool knows what to translate, it:

- **Sends text to DeepL**: The text is sent to the DeepL translation service

- **Applies the glossary**: The tool uses a special dictionary of Koha terms to ensure consistent translations

- **Handles technical limitations**: If the DeepL service is busy or has temporary issues, the tool:
  - Waits and tries again
  - Spaces out requests to avoid overloading the service
  - Logs any problems for review

### 4. Managing Translations

After getting translations from DeepL, the tool:

- **Updates translation files**: The translations are saved in special PO files

- **Handles existing translations**: The tool is smart about existing translations:
  - By default, it keeps existing translations and only translates new content
  - With the `--translate-all` option, it will create fresh translations for everything
  - It logs both the old and new translations when replacing existing ones

- **Matches text intelligently**: The tool uses a two-step process to match translations:
  - First, it looks for exact matches
  - Then, it looks for matches with minor formatting differences
  - If no match is found, it creates a new translation entry

### 5. Tracking Progress

The tool keeps detailed records of the translation process:

- **Console output**: Shows a summary of what's happening

- **Log files**: Creates detailed logs with timestamps in the `log/` directory

- **Translation statistics**: Can generate reports showing how much of the manual has been translated

## Special Features

### Translation Analysis

The tool can analyze and report on translation progress:

- **Per-file statistics**: Shows how much of each file has been translated
- **Overall progress**: Calculates the total percentage of the manual that's been translated
- **Visual indicators**: Displays progress bars to easily see translation status

### Smart Handling of Manual Updates

When the English manual is updated, the tool:

- **Identifies new content**: Finds text that hasn't been translated yet
- **Preserves existing work**: Keeps existing translations that are still valid
- **Updates only what's needed**: Translates only the new or changed content

## Common Challenges and Solutions

### 1. Preserving Special Formatting

**Challenge**: The Koha manual contains special formatting codes and references that shouldn't be translated.

**Solution**: The tool recognizes and preserves these special elements, ensuring they work correctly in the translated version.

### 2. Consistent Terminology

**Challenge**: Technical terms need to be translated consistently throughout the manual.

**Solution**: The glossary system ensures that Koha-specific terms are always translated the same way, regardless of context.

### 3. Handling Large Documents

**Challenge**: Translating the entire manual at once could be overwhelming.

**Solution**: The tool can translate individual files or sections, making it easier to manage large translation projects.

### 4. Tracking Changes

**Challenge**: When retranslating content, it's important to see what's changing.

**Solution**: When using the `--translate-all` option, the tool shows both the old and new translations, making it easy to review changes.

## Practical Benefits

1. **Time-saving**: Automates the tedious process of manual translation
2. **Consistency**: Ensures technical terms are translated the same way throughout
3. **Quality**: Uses DeepL, one of the best translation services available
4. **Flexibility**: Can translate the entire manual or just specific sections
5. **Transparency**: Logs all activities so you can see exactly what's happening

## Conclusion

The Koha Manual Translator provides an efficient way to translate the Koha manual while preserving its structure and ensuring terminology consistency. It balances automation with careful handling of technical content, making it possible to maintain high-quality translations of this complex documentation.
