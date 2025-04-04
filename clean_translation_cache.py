#!/usr/bin/env python3
"""
Script to clean the translation cache by removing entries with placeholder patterns like '%value%'
"""

import os
import sqlite3
import re
from pathlib import Path
import argparse
import logging

def setup_logging(debug_mode=False):
    """Set up logging to both console and file"""
    # Create log directory if it doesn't exist
    log_dir = Path('log')
    try:
        log_dir.mkdir(exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create log directory: {e}")
        # Fall back to current directory if log dir can't be created
        log_dir = Path('.')
    
    # Set up root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Clear any existing handlers
    for handler in logger.handlers[::]:
        logger.removeHandler(handler)
    
    # Create console handler with a potentially higher log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Create formatter and add it to the handlers
    console_formatter = logging.Formatter('%(message)s')  # Simpler format for console
    console_handler.setFormatter(console_formatter)
    
    # Add the handlers to the logger
    logger.addHandler(console_handler)
    
    return logger

def get_cache_db_path():
    """Get the path to the translation cache database"""
    cache_dir = Path('cache')
    if not cache_dir.exists():
        cache_dir = Path('.')
        
    db_path = cache_dir / 'translation_cache.db'
    return db_path

def clean_cache(pattern=r'%\w+%', dry_run=False, verbose=False):
    """
    Clean the translation cache by removing entries with the specified pattern
    
    Args:
        pattern: Regular expression pattern to match in translations
        dry_run: If True, only show what would be deleted without actually deleting
        verbose: If True, show more detailed information
    """
    db_path = get_cache_db_path()
    
    if not db_path.exists():
        logging.error(f"Translation cache database not found at {db_path}")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if the translations table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translations'")
        if not cursor.fetchone():
            logging.error("Translations table not found in the database")
            conn.close()
            return
        
        # Get all translations
        cursor.execute('SELECT source_text_hash, source_text, translated_text FROM translations')
        all_translations = cursor.fetchall()
        
        if not all_translations:
            logging.info("No translations found in the cache")
            conn.close()
            return
        
        logging.info(f"Found {len(all_translations)} total translations in the cache")
        
        # Compile the pattern
        pattern_re = re.compile(pattern)
        
        # Find translations matching the pattern
        to_delete = []
        for hash_val, source, translation in all_translations:
            if pattern_re.search(translation):
                to_delete.append((hash_val, source, translation))
                if verbose:
                    logging.info(f"Found match: {source[:50]}... -> {translation[:50]}...")
        
        if not to_delete:
            logging.info(f"No translations found matching the pattern '{pattern}'")
            conn.close()
            return
        
        logging.info(f"Found {len(to_delete)} translations matching the pattern '{pattern}'")
        
        if dry_run:
            logging.info("Dry run - no translations were deleted")
        else:
            # Delete the matching translations
            for hash_val, _, _ in to_delete:
                cursor.execute('DELETE FROM translations WHERE source_text_hash = ?', (hash_val,))
            
            conn.commit()
            logging.info(f"Deleted {len(to_delete)} translations from the cache")
        
        conn.close()
        
    except Exception as e:
        logging.error(f"Error cleaning translation cache: {e}")

def main():
    parser = argparse.ArgumentParser(description='Clean the translation cache by removing entries with placeholder patterns')
    parser.add_argument('--pattern', default=r'%\w+%', help='Regular expression pattern to match in translations (default: %%\\w+%%)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--verbose', action='store_true', help='Show more detailed information')
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    logging.info("Translation Cache Cleaner")
    logging.info(f"Pattern: {args.pattern}")
    logging.info(f"Dry run: {args.dry_run}")
    
    clean_cache(args.pattern, args.dry_run, args.verbose)

if __name__ == "__main__":
    main()
