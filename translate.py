#!/usr/bin/env python3
"""
translate.py - Module for translating text using the DeepL API.
"""

import os
import deepl
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_translator():
    """
    Initialize and return a DeepL translator client using the API key from environment variables.
    
    Returns:
        deepl.Translator: A configured DeepL translator client.
        
    Raises:
        ValueError: If the DeepL API key is not found in environment variables.
    """
    api_key = os.getenv("DEEPL_API_KEY")
    if not api_key:
        raise ValueError("DeepL API key not found. Please set the DEEPL_API_KEY environment variable.")
    
    return deepl.Translator(api_key)

def translate_text(text, target_lang="SV", source_lang="EN"):
    """
    Translate text using the DeepL API.
    
    Args:
        text (str or list): The text to translate. Can be a single string or a list of strings.
        target_lang (str): The target language code (default: "SV" for Swedish).
        source_lang (str): The source language code (default: "EN" for English).
        
    Returns:
        str or list: The translated text. If input was a list, returns a list of translations.
        
    Raises:
        Exception: If there's an error during translation.
    """
    try:
        translator = get_translator()
        
        # Handle both single strings and lists of strings
        if isinstance(text, list):
            result = translator.translate_text(
                text, 
                target_lang=target_lang, 
                source_lang=source_lang
            )
            return [item.text for item in result]
        else:
            result = translator.translate_text(
                text, 
                target_lang=target_lang, 
                source_lang=source_lang
            )
            return result.text
    
    except Exception as e:
        # Log the error and re-raise
        print(f"Error during translation: {e}")
        raise

if __name__ == "__main__":
    # This module is not meant to be run directly
    pass