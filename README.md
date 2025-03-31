# KOHA Manual Translator

A Python application to translate the KOHA manual from English to Swedish using DeepL API. This tool works directly with the RST source files from the official KOHA manual repository and preserves all formatting, directives, and technical terminology while creating a parallel directory structure for the translated content.

![KOHA Logo](https://koha-community.org/files/2013/09/cropped-kohabanner3.jpg)

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
   - koha-manual-l10n (localization files)

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

```bash
python translator.py [OPTIONS]
```

Options:
- `--status`: Show translation status
- `--translate`: Run the translation process
- `--lang CODE`: Language code (default: sv)
- `--file FILENAME`: Process specific file (without .rst extension)
- `--all`: Process all files (required for bulk translation)
- `--phrases PATH`: Path to phrases CSV file (default: phrases.csv)
- `--translate-all`: Translate all strings, even if they already exist in PO file

### Examples

Check translation status:
```bash
python translator.py --status
```

Translate a specific file:
```bash
python translator.py --translate --file 01_introduction
```

Translate all files, including already translated strings:
```bash
python translator.py --translate --all --translate-all
```

## Output

The translated files will be created in the KOHA manual localization repository structure under `repos/koha-manual-l10n`. The translation process generates and updates PO files that can be used with the official KOHA manual build system.

## Technical Details

### Project Structure

```
koha-doc-translator/
├── .env                  # Environment variables (not in repo)
├── .env_example          # Example environment file
├── .gitignore            # Git ignore file
├── README.md             # English documentation
├── README-SV.md          # Swedish documentation
├── phrases.csv           # Glossary terms
├── requirements.txt      # Python dependencies
├── setup_repos.py        # Repository setup script
├── translator.py         # Main translation script
└── repos/                # Contains cloned repositories
    ├── koha-manual/      # Source RST files
    └── koha-manual-l10n/ # Localization files
```

### Translation Process

1. The script scans the source RST files in the KOHA manual repository
2. For each file, it extracts translatable content while preserving formatting
3. It checks if translations already exist in the PO files
4. New or modified content is sent to DeepL for translation
5. The glossary ensures consistent terminology
6. Translated content is written back to PO files in the localization repository

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
