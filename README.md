# KOHA Manual Translator

A Python application to translate the KOHA manual from English to Swedish using DeepL API. Works directly with the RST source files from the official KOHA manual repository.

## Setup

1. Clone the KOHA manual repository:
```bash
git clone https://gitlab.com/koha-community/koha-manual.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory and add your DeepL API key:
```
DEEPL_API_KEY=your_api_key_here
```

4. Update the `manual_source` path in `translator.py` to point to your local KOHA manual source directory.

5. Run the translator:
```bash
python translator.py
```

## Features

- Uses DeepL's professional translation API
- Works directly with RST source files from the official KOHA manual
- Preserves all RST formatting and directives
- Maintains technical terms and KOHA-specific terminology
- Creates a parallel directory structure for translated files
- Translates all manual content while preserving document structure

## Output

The translated files will be created in a `manual-sv` directory parallel to the source directory, maintaining the same directory structure as the original manual.
