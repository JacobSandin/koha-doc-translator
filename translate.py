#!/usr/bin/env python3
"""
translate.py - Module for translating text using the DeepL API with SQLite caching.
"""

import os
import sys
import sqlite3
import hashlib
import argparse
import deepl
import glob
from dotenv import load_dotenv
from pathlib import Path

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

def init_cache_db(db_path=None):
    """
    Initialize the SQLite database for caching translations.
    
    Args:
        db_path (str, optional): Path to the SQLite database file. 
                                If None, uses default path in cache directory.
    
    Returns:
        sqlite3.Connection: Connection to the SQLite database.
    """
    if db_path is None:
        # Create cache directory if it doesn't exist
        cache_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'cache'
        cache_dir.mkdir(exist_ok=True)
        db_path = cache_dir / 'translation_cache.db'
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS translations (
        id INTEGER PRIMARY KEY,
        source_text TEXT NOT NULL,
        target_lang TEXT NOT NULL,
        source_lang TEXT NOT NULL,
        translated_text TEXT NOT NULL,
        hash TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create index on hash for faster lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON translations(hash)")
    
    conn.commit()
    return conn

def get_cache_hash(text, target_lang, source_lang):
    """
    Generate a unique hash for a translation request.
    
    Args:
        text (str): The text to translate.
        target_lang (str): The target language code.
        source_lang (str): The source language code.
    
    Returns:
        str: A unique hash for this translation request.
    """
    # Create a string that uniquely identifies this translation request
    unique_str = f"{text}|{target_lang}|{source_lang}"
    
    # Generate a hash of this string
    return hashlib.md5(unique_str.encode('utf-8')).hexdigest()

def get_from_cache(text, target_lang, source_lang, conn=None):
    """
    Check if a translation is already in the cache.
    
    Args:
        text (str): The text to translate.
        target_lang (str): The target language code.
        source_lang (str): The source language code.
        conn (sqlite3.Connection, optional): Connection to the SQLite database.
                                           If None, a new connection is created.
    
    Returns:
        str or None: The cached translation if found, None otherwise.
    """
    close_conn = False
    if conn is None:
        conn = init_cache_db()
        close_conn = True
    
    cursor = conn.cursor()
    
    # Generate a hash for this translation request
    cache_hash = get_cache_hash(text, target_lang, source_lang)
    
    # Check if this translation is already in the cache
    cursor.execute(
        "SELECT translated_text FROM translations WHERE hash = ?", 
        (cache_hash,)
    )
    
    result = cursor.fetchone()
    
    # If found, mark this entry as used by updating its timestamp
    if result:
        mark_cache_entry_used(cache_hash, conn)
    
    if close_conn:
        conn.close()
    
    return result[0] if result else None

def add_to_cache(text, target_lang, source_lang, translated_text, conn=None):
    """
    Add a translation to the cache.
    
    Args:
        text (str): The source text.
        target_lang (str): The target language code.
        source_lang (str): The source language code.
        translated_text (str): The translated text.
        conn (sqlite3.Connection, optional): Connection to the SQLite database.
                                           If None, a new connection is created.
    """
    close_conn = False
    if conn is None:
        conn = init_cache_db()
        close_conn = True
    
    cursor = conn.cursor()
    
    # Generate a hash for this translation request
    cache_hash = get_cache_hash(text, target_lang, source_lang)
    
    # Add this translation to the cache
    try:
        cursor.execute(
            """INSERT INTO translations 
               (source_text, target_lang, source_lang, translated_text, hash) 
               VALUES (?, ?, ?, ?, ?)""", 
            (text, target_lang, source_lang, translated_text, cache_hash)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # If this translation is already in the cache, update it
        cursor.execute(
            """UPDATE translations 
               SET translated_text = ? 
               WHERE hash = ?""", 
            (translated_text, cache_hash)
        )
        conn.commit()
    
    if close_conn:
        conn.close()

def mark_cache_entry_used(cache_hash, conn=None):
    """
    Mark a cache entry as used by updating its timestamp.
    
    Args:
        cache_hash (str): The hash of the cache entry to mark.
        conn (sqlite3.Connection, optional): Connection to the SQLite database.
                                           If None, a new connection is created.
    """
    close_conn = False
    if conn is None:
        conn = init_cache_db()
        close_conn = True
    
    cursor = conn.cursor()
    
    # Update the timestamp to mark it as used
    cursor.execute(
        "UPDATE translations SET created_at = CURRENT_TIMESTAMP WHERE hash = ?", 
        (cache_hash,)
    )
    conn.commit()
    
    if close_conn:
        conn.close()

def delete_unused_cache_entries(days_old=30, conn=None):
    """
    Delete cache entries that haven't been used for a specified number of days.
    
    Args:
        days_old (int): Delete entries older than this many days.
        conn (sqlite3.Connection, optional): Connection to the SQLite database.
                                           If None, a new connection is created.
                                           
    Returns:
        int: Number of entries deleted.
    """
    close_conn = False
    if conn is None:
        conn = init_cache_db()
        close_conn = True
    
    cursor = conn.cursor()
    
    # Delete entries older than days_old
    cursor.execute(
        "DELETE FROM translations WHERE created_at < datetime('now', ?)", 
        (f"-{days_old} days",)
    )
    
    # Get the number of rows deleted
    deleted_count = cursor.rowcount
    conn.commit()
    
    if close_conn:
        conn.close()
    
    return deleted_count

def delete_cache_entries_containing(text, conn=None):
    """
    Delete cache entries where source_text or translated_text contains the specified text.
    
    Args:
        text (str): The text to search for.
        conn (sqlite3.Connection, optional): Connection to the SQLite database.
                                           If None, a new connection is created.
                                           
    Returns:
        int: Number of entries deleted.
    """
    close_conn = False
    if conn is None:
        conn = init_cache_db()
        close_conn = True
    
    cursor = conn.cursor()
    
    # Delete entries containing the specified text
    cursor.execute(
        "DELETE FROM translations WHERE source_text LIKE ? OR translated_text LIKE ?", 
        (f"%{text}%", f"%{text}%")
    )
    
    # Get the number of rows deleted
    deleted_count = cursor.rowcount
    conn.commit()
    
    if close_conn:
        conn.close()
    
    return deleted_count

def clear_cache(conn=None):
    """
    Clear all entries from the cache.
    
    Args:
        conn (sqlite3.Connection, optional): Connection to the SQLite database.
                                           If None, a new connection is created.
                                           
    Returns:
        int: Number of entries deleted.
    """
    close_conn = False
    if conn is None:
        conn = init_cache_db()
        close_conn = True
    
    cursor = conn.cursor()
    
    # Get the count before deleting
    cursor.execute("SELECT COUNT(*) FROM translations")
    count = cursor.fetchone()[0]
    
    # Delete all entries
    cursor.execute("DELETE FROM translations")
    conn.commit()
    
    if close_conn:
        conn.close()
    
    return count

def translate_text(text, target_lang="SV", source_lang="EN", disable_cache=False, conn=None):
    """
    Translate text using the DeepL API with caching.
    
    Args:
        text (str or list): The text to translate. Can be a single string or a list of strings.
        target_lang (str): The target language code (default: "SV" for Swedish).
        source_lang (str): The source language code (default: "EN" for English).
        disable_cache (bool): If True, don't use the cache (default: False).
        conn (sqlite3.Connection, optional): Connection to the SQLite database.
                                           If None, a new connection is created.
        
    Returns:
        str or list: The translated text. If input was a list, returns a list of translations.
        
    Raises:
        Exception: If there's an error during translation.
    """
    try:
        # Handle both single strings and lists of strings
        if isinstance(text, list):
            # For lists, we need to translate each item separately
            translations = []
            
            # Create a single connection for all items in the list
            local_conn = None
            if not disable_cache and conn is None:
                local_conn = init_cache_db()
            
            for item in text:
                translations.append(translate_text(item, target_lang, source_lang, disable_cache, 
                                                 conn=local_conn if not disable_cache else None))
            
            # Close the connection if we created it
            if local_conn is not None:
                local_conn.close()
                
            return translations
        
        # For single strings, check the cache first (unless disabled)
        close_conn = False
        local_conn = conn
        
        if not disable_cache:
            if local_conn is None:
                local_conn = init_cache_db()
                close_conn = True
                
            cached_translation = get_from_cache(text, target_lang, source_lang, local_conn)
            
            if cached_translation:
                print(f"Using cached translation for: {text[:50]}{'...' if len(text) > 50 else ''}")
                
                # Only close if we created the connection
                if close_conn:
                    local_conn.close()
                    
                return cached_translation
        
        # If not in cache or cache is disabled, use the DeepL API
        translator = get_translator()
        result = translator.translate_text(
            text, 
            target_lang=target_lang, 
            source_lang=source_lang
        )
        translated_text = result.text
        
        # Add to cache (unless disabled)
        if not disable_cache and local_conn is not None:
            add_to_cache(text, target_lang, source_lang, translated_text, local_conn)
            
            # Only close if we created the connection
            if close_conn:
                local_conn.close()
        
        return translated_text
    
    except Exception as e:
        # Log the error and re-raise
        print(f"Error during translation: {e}")
        raise

def get_locale_path(pot_file_dir=None, repo_path=None):
    """
    Get the path to the locale directory containing .pot files.
    
    Args:
        pot_file_dir (str, optional): Direct path to a directory containing .pot files.
                                     If provided, this takes precedence over repo_path.
        repo_path (str, optional): Path to the koha-manual repository.
                                  If None and pot_file_dir is None, uses the default path relative to this script.
    
    Returns:
        str: The path to the directory containing .pot files.
    """
    if pot_file_dir:
        # If a specific pot file directory is provided, use it directly
        return pot_file_dir
    
    if repo_path is None:
        # Default path is repos/koha-manual relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_path = os.path.join(script_dir, 'repos', 'koha-manual')
    
    # Construct the path to the locale directory
    locale_path = os.path.join(repo_path, 'build', 'locale')
    return locale_path

def find_pot_file(filename, pot_file_dir=None, repo_path=None):
    """
    Check if a file exists as a .pot file in the specified directory.
    
    Args:
        filename (str): The name of the file to check for (without extension).
        pot_file_dir (str, optional): Direct path to a directory containing .pot files.
                                     If provided, this takes precedence over repo_path.
        repo_path (str, optional): Path to the koha-manual repository.
                                  If None and pot_file_dir is None, uses the default path relative to this script.
    
    Returns:
        str or None: The full path to the .pot file if found, None otherwise.
    """
    locale_path = get_locale_path(pot_file_dir, repo_path)
    
    # Check if the directory exists
    if not os.path.isdir(locale_path):
        print(f"Warning: Directory not found at {locale_path}")
        return None
    
    # Look for the .pot file
    pot_file = os.path.join(locale_path, f"{filename}.pot")
    
    if os.path.isfile(pot_file):
        return pot_file
    
    # If not found directly, try to find it using glob
    pot_files = glob.glob(os.path.join(locale_path, f"*{filename}*.pot"))
    
    if pot_files:
        # Return the first match
        return pot_files[0]
    
    return None

def find_all_pot_files(pot_file_dir=None, repo_path=None):
    """
    Find all .pot files in the specified directory.
    
    Args:
        pot_file_dir (str, optional): Direct path to a directory containing .pot files.
                                     If provided, this takes precedence over repo_path.
        repo_path (str, optional): Path to the koha-manual repository.
                                  If None and pot_file_dir is None, uses the default path relative to this script.
    
    Returns:
        list: A list of paths to all .pot files found.
    """
    locale_path = get_locale_path(pot_file_dir, repo_path)
    
    # Check if the directory exists
    if not os.path.isdir(locale_path):
        print(f"Warning: Directory not found at {locale_path}")
        return []
    
    # Find all .pot files
    pot_files = glob.glob(os.path.join(locale_path, "*.pot"))
    
    return pot_files

def process_pot_file(pot_file_path, target_lang="SV", source_lang="EN", disable_cache=False):
    """
    Process a single .pot file for translation.
    
    Args:
        pot_file_path (str): Path to the .pot file to process.
        target_lang (str): Target language code.
        source_lang (str): Source language code.
        disable_cache (bool): Whether to disable the translation cache.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    print(f"Processing .pot file: {pot_file_path}")
    # TODO: Implement .pot file translation
    print(f"Translation of .pot files is not yet implemented.")
    return True

def parse_args():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Translate text using DeepL API with caching.")
    parser.add_argument("text", nargs='?', help="Text to translate")
    
    # File translation options
    file_group = parser.add_argument_group('File Translation')
    file_group.add_argument("--file", help="Name of a .pot file to translate")
    file_group.add_argument("--all", action="store_true", help="Process all .pot files in the specified directory")
    file_group.add_argument("--pot-file-dir", help="Directory containing .pot files (default: repos/koha-manual/build/locale)")
    
    # Translation options
    parser.add_argument("--target-lang", default="SV", help="Target language code (default: SV)")
    parser.add_argument("--source-lang", default="EN", help="Source language code (default: EN)")
    parser.add_argument("--disable-cache", action="store_true", help="Disable caching")
    
    # Cache management options
    cache_group = parser.add_argument_group('Cache Management')
    cache_group.add_argument("--cache-delete-unused", type=int, metavar="DAYS", 
                          help="Delete cache entries unused for specified number of days")
    cache_group.add_argument("--cache-delete-entry-containing", metavar="TEXT",
                          help="Delete cache entries containing the specified text")
    cache_group.add_argument("--cache-clear", action="store_true", 
                          help="Clear all cache entries")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    try:
        # Handle cache management options
        if args.cache_clear:
            count = clear_cache()
            print(f"Cleared {count} entries from the translation cache.")
            sys.exit(0)
            
        if args.cache_delete_unused is not None:
            count = delete_unused_cache_entries(args.cache_delete_unused)
            print(f"Deleted {count} unused entries older than {args.cache_delete_unused} days from the translation cache.")
            sys.exit(0)
            
        if args.cache_delete_entry_containing:
            count = delete_cache_entries_containing(args.cache_delete_entry_containing)
            print(f"Deleted {count} entries containing '{args.cache_delete_entry_containing}' from the translation cache.")
            sys.exit(0)
        
        # Handle all files translation
        if args.all:
            pot_files = find_all_pot_files(args.pot_file_dir)
            if not pot_files:
                pot_dir = args.pot_file_dir if args.pot_file_dir else "repos/koha-manual/build/locale"
                print(f"No .pot files found in {pot_dir}")
                sys.exit(1)
            
            print(f"Found {len(pot_files)} .pot files to process")
            success_count = 0
            
            for pot_file in pot_files:
                if process_pot_file(pot_file, args.target_lang, args.source_lang, args.disable_cache):
                    success_count += 1
            
            print(f"Successfully processed {success_count} out of {len(pot_files)} .pot files")
            sys.exit(0)
        
        # Handle single file translation
        elif args.file:
            pot_file = find_pot_file(args.file, args.pot_file_dir)
            if pot_file:
                process_pot_file(pot_file, args.target_lang, args.source_lang, args.disable_cache)
            else:
                pot_dir = args.pot_file_dir if args.pot_file_dir else "repos/koha-manual/build/locale"
                print(f"Error: Could not find .pot file for '{args.file}' in {pot_dir}")
                sys.exit(1)
        
        # Handle text translation
        elif args.text:
            translated_text = translate_text(
                args.text, 
                args.target_lang, 
                args.source_lang, 
                args.disable_cache
            )
            
            print(f"Original: {args.text}")
            print(f"Translated: {translated_text}")
        else:
            # If no text/file is provided and no cache management options are specified,
            # show help message
            parser = argparse.ArgumentParser()
            parse_args()
            parser.print_help()
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)