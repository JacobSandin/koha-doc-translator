# KOHA Manual Translator

A Python application to translate the KOHA manual from English to Swedish using DeepL API. This tool works directly with the RST source files from the official KOHA manual repository and preserves all formatting, directives, and technical terminology while creating a parallel directory structure for the translated content.

<img src="https://koha.se/wp-content/uploads/2016/12/cropped-koha-logga-green-only-logo-768x461.jpg" alt="KOHA Logo" width="300">

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output](#output)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

The KOHA Manual Translator is designed to facilitate the translation of the KOHA Integrated Library System documentation from English to Swedish. It leverages DeepL's professional translation API to produce high-quality translations while preserving the technical integrity of the documentation.

## Features

- Uses DeepL's professional translation API for high-quality translations
- Works directly with RST (reStructuredText) source files from the official KOHA manual
- Preserves all RST formatting and directives during translation
- Maintains technical terms and KOHA-specific terminology through a custom glossary
- Creates a parallel directory structure for translated files
- Translates all manual content while preserving document structure
- Supports incremental translation (only translates new or modified content)
- Integrates with the official KOHA manual localization workflow

## Requirements

- Python 3.7 or higher
- DeepL API key (Pro account recommended for large volumes)
- Git
- Internet connection for API access

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/JacobSandin/koha-doc-translator.git
   cd koha-doc-translator
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the required repositories:
   ```bash
   python setup_repos.py
   ```
   This will clone the necessary KOHA repositories into the `repos` directory:
   - koha-manual (source RST files)
   - koha-manual-l10n (cloned inside koha-manual as "locales" directory)

4. Copy the example environment file and add your DeepL API key:
   ```bash
   cp .env_example .env
   # Edit the .env file to add your DeepL API key
   ```

## Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
DEEPL_API_KEY=your_api_key_here
```

### Custom Terminology

The translator uses a glossary to maintain consistent translations of technical terms. You can edit the `phrases.csv` file to add or modify terms:

```csv
EN,SV
"KOHA","KOHA"
"circulation","cirkulation"
```

## Usage

### Basic Usage

To run the translator with default settings:

```bash
python translator.py --translate --all
```

### Command Line Options

**Translator Script:**
```bash
python translator.py [OPTIONS]
```

Translator Options:
- `--translate`: Run the translation process
- `--lang CODE`: Language code (default: sv)
- `--file FILENAME`: Process specific file (without .rst extension)
- `--all`: Process all files (required for bulk translation)
- `--phrases PATH`: Path to phrases CSV file (default: phrases.csv)
- `--ref-phrases PATH`: Path to reference phrases CSV file (default: ref_phrases.csv)
- `--translate-all`: Translate all strings, even if they already exist in PO file
- `--debug`: Enable debug mode with full text output
- `--log-file PATH`: Specify custom log file path

**Status Script:**
```bash
python status.py [OPTIONS]
```

Status Options:
- `--lang CODE`: Language code (default: sv)
- `--file FILENAME`: Check specific file (without .rst extension)
- `--source-dir PATH`: Path to RST source files
- `--po-dir PATH`: Path to PO files directory

### Examples

Check translation status:
```bash
python status.py
```

Check status for a specific file:
```bash
python status.py --file enhancedcontentpreferences
```

Translate a specific file:
```bash
python translator.py --translate --file enhancedcontentpreferences
```

Translate all files, including already translated strings:
```bash
python translator.py --translate --all --translate-all
```

Build the Swedish manual (from within the koha-manual directory):
```bash
make -e SPHINXOPTS="-q -D language='sv' -d build/doctrees" BUILDDIR="build/sv" singlehtml
```

## Output

The translated files will be created in the KOHA manual localization repository structure under `repos/koha-manual/locales`. The translation process generates and updates PO files that can be used with the official KOHA manual build system.

## Technical Details

### Project Structure

```
koha-doc-translator/
├── .env                  # Environment variables (not in repo)
├── .env_example          # Example environment file
├── .gitignore            # Git ignore file
├── README.md             # English documentation
├── README-SV.md          # Swedish documentation
├── TRANSLATION_PROCESS.md # Documentation for non-technical users
├── phrases.csv           # Glossary terms for translation
├── ref_phrases.csv       # Reference phrases for translation
├── requirements.txt      # Python dependencies
├── setup_repos.py        # Repository setup script
├── translator.py         # Main translation script
├── status.py             # Translation status reporting script
├── build_sv_manual.py    # Script to build the Swedish manual
├── extract_ref_display_text_from_rst.py # Utility script for references
├── remove_fuzzy_flags.py # Utility script for PO files
├── log/                  # Directory for log files
└── repos/                # Contains cloned repositories
    └── koha-manual/      # Source RST files
        ├── source/       # Original RST files
        └── locales/      # Localization files (koha-manual-l10n)
```

### Translation Process

1. The script scans the source RST files in the KOHA manual repository
2. For each file, it extracts translatable content while preserving formatting
3. It checks if translations already exist in the PO files
4. New or modified content is sent to DeepL for translation
5. The glossary ensures consistent terminology
6. Translated content is written back to PO files in the localization repository
7. The status script can be used to check translation progress and identify missing translations

The translation process handles special cases like escaped characters in RST files (e.g., `\_\_\_`) and ensures all content is properly extracted and translated.

## Glossary and Reference Files

### phrases.csv

The `phrases.csv` file contains a glossary of Koha-specific terms and their translations. This ensures consistent terminology throughout the manual. The file has a simple format:

```
English term,Swedish translation
```

For example:
```
patron,låntagare
checkout,utlån
hold,reservation
```

The translator uses this file as a glossary with the DeepL API to enforce consistent translations of technical terms regardless of context.

### ref_phrases.csv

The `ref_phrases.csv` file specifically handles references within the RST documentation. In RST files, references look like `:ref:`label`` and are used for internal linking. This file helps translate these references correctly.

You might not want to override `ref_phrases.csv` when:
1. You've carefully curated reference translations that should be preserved
2. You're working with a specific version of the manual where reference IDs are stable
3. You want to maintain consistency in how references are translated across updates

The `extract_ref_display_text_from_rst.py` utility script can help generate this file by extracting reference labels and their display text from RST files.

## Troubleshooting

### Common Issues

- **API Key Issues**: Ensure your DeepL API key is correctly set in the `.env` file
- **Repository Access**: If you can't access the repositories, check your network connection and GitLab/GitHub access
- **Translation Errors**: For specific translation errors, check the console output for details

### Logs

The translator outputs detailed logs to the console during operation. For persistent logs, redirect the output to a file:

```bash
python translator.py --translate --all > translation_log.txt 2>&1
```

## Contributing

Contributions are welcome! To contribute to this project:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows the project's style guidelines and includes appropriate tests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
