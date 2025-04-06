"""
Unit tests for the translation caching functionality.
"""
import os
import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from pathlib import Path

from translate import (
    init_cache_db, 
    get_cache_hash, 
    get_from_cache, 
    add_to_cache, 
    translate_text,
    mark_cache_entry_used,
    delete_unused_cache_entries,
    delete_cache_entries_containing,
    clear_cache
)

class TestTranslateCache:
    """Test cases for the translation caching functionality."""
    
    @pytest.fixture
    def test_db_path(self, tmp_path):
        """Create a temporary database path for testing."""
        # Create a unique database path for each test to avoid interference
        import uuid
        return tmp_path / f"test_translation_cache_{uuid.uuid4()}.db"
    
    def test_init_cache_db(self, test_db_path):
        """Test that the cache database is initialized correctly."""
        # Initialize the database
        conn = init_cache_db(test_db_path)
        
        # Check that the connection is valid
        assert isinstance(conn, sqlite3.Connection)
        
        # Check that the table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translations'")
        tables = cursor.fetchall()
        
        assert len(tables) == 1
        assert tables[0][0] == 'translations'
        
        # Check that the index exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_hash'")
        indexes = cursor.fetchall()
        
        assert len(indexes) == 1
        assert indexes[0][0] == 'idx_hash'
        
        # Clean up
        conn.close()
    
    def test_get_cache_hash(self):
        """Test that cache hashes are generated correctly."""
        # Test that the same inputs produce the same hash
        hash1 = get_cache_hash("Hello world", "SV", "EN")
        hash2 = get_cache_hash("Hello world", "SV", "EN")
        
        assert hash1 == hash2
        
        # Test that different inputs produce different hashes
        hash3 = get_cache_hash("Hello world", "DE", "EN")
        hash4 = get_cache_hash("Hello world", "SV", "FR")
        hash5 = get_cache_hash("Goodbye world", "SV", "EN")
        
        assert hash1 != hash3
        assert hash1 != hash4
        assert hash1 != hash5
    
    def test_add_and_get_from_cache(self, test_db_path):
        """Test adding to and retrieving from the cache."""
        # Initialize the database
        conn = init_cache_db(test_db_path)
        
        # Add a translation to the cache
        add_to_cache("Hello world", "SV", "EN", "Hej världen", conn)
        
        # Retrieve the translation from the cache
        cached_translation = get_from_cache("Hello world", "SV", "EN", conn)
        
        assert cached_translation == "Hej världen"
        
        # Test that a different text returns None
        cached_translation = get_from_cache("Goodbye world", "SV", "EN", conn)
        
        assert cached_translation is None
        
        # Clean up
        conn.close()
    
    def test_update_existing_cache_entry(self, test_db_path):
        """Test updating an existing cache entry."""
        # Initialize the database
        conn = init_cache_db(test_db_path)
        
        # Add a translation to the cache
        add_to_cache("Hello world", "SV", "EN", "Hej världen", conn)
        
        # Update the translation
        add_to_cache("Hello world", "SV", "EN", "Hallå världen", conn)
        
        # Retrieve the translation from the cache
        cached_translation = get_from_cache("Hello world", "SV", "EN", conn)
        
        assert cached_translation == "Hallå världen"
        
        # Clean up
        conn.close()
    
    def test_translate_text_with_cache(self, test_db_path):
        """Test that translate_text uses the cache when available."""
        # Create a mock translator
        mock_translator = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "Hej världen"
        mock_translator.translate_text.return_value = mock_result
        
        # Create a real database connection for testing
        conn = init_cache_db(test_db_path)
        
        # Mock the get_translator function but use a real database
        with patch('translate.get_translator', return_value=mock_translator):
            # First translation should use the API and add to cache
            result1 = translate_text("Hello world", disable_cache=False, conn=conn)
            
            # Verify the translator was called
            mock_translator.translate_text.assert_called_once()
            assert result1 == "Hej världen"
            
            # Reset the mock
            mock_translator.translate_text.reset_mock()
            
            # Second translation should use the cache
            result2 = translate_text("Hello world", disable_cache=False, conn=conn)
            
            # Verify the translator was not called
            mock_translator.translate_text.assert_not_called()
            assert result2 == "Hej världen"
            
        # Clean up
        conn.close()
    
    def test_translate_text_with_disable_cache(self, test_db_path):
        """Test that translate_text doesn't use the cache when disabled."""
        # Create a mock translator
        mock_translator = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "Hej världen"
        mock_translator.translate_text.return_value = mock_result
        
        # Create a real database connection for testing
        conn = init_cache_db(test_db_path)
        
        with patch('translate.get_translator', return_value=mock_translator):
            # First translation with cache disabled
            translate_text("Hello world", disable_cache=True, conn=conn)
            
            # Verify the translator was called
            assert mock_translator.translate_text.call_count == 1
            
            # Add to cache manually
            add_to_cache("Hello world", "SV", "EN", "Hej världen", conn)
            
            # Reset the mock
            mock_translator.translate_text.reset_mock()
            
            # Second translation with cache disabled should still use the API
            translate_text("Hello world", disable_cache=True, conn=conn)
            
            # Verify the translator was called again
            assert mock_translator.translate_text.call_count == 1
            
        # Clean up
        conn.close()
    
    def test_translate_text_list_with_cache(self, test_db_path):
        """Test that translate_text handles lists correctly with caching."""
        # Generate unique test strings with a timestamp to avoid cache collisions
        import time
        timestamp = str(time.time())
        test_string1 = f"UniqueTest1_{timestamp}"
        test_string2 = f"UniqueTest2_{timestamp}"
        
        # Create a database connection
        conn = init_cache_db(test_db_path)
        
        # Create a mock translator with specific responses
        mock_translator = MagicMock()
        
        def mock_translate_side_effect(text, **kwargs):
            mock_result = MagicMock()
            if text == test_string1:
                mock_result.text = f"Translated1_{timestamp}"
            elif text == test_string2:
                mock_result.text = f"Translated2_{timestamp}"
            else:
                mock_result.text = f"Unknown_{text}"
            return mock_result
            
        mock_translator.translate_text.side_effect = mock_translate_side_effect
        
        with patch('translate.get_translator', return_value=mock_translator):
            # First call should translate both strings and cache them
            result = translate_text([test_string1, test_string2], disable_cache=False, conn=conn)
            
            # Verify both translations were done
            assert mock_translator.translate_text.call_count == 2
            assert result == [f"Translated1_{timestamp}", f"Translated2_{timestamp}"]
            
            # Reset the mock
            mock_translator.translate_text.reset_mock()
            
            # Second call should use the cache
            result2 = translate_text([test_string1, test_string2], disable_cache=False, conn=conn)
            
            # Verify the result is the same
            assert result2 == [f"Translated1_{timestamp}", f"Translated2_{timestamp}"]
            
            # Verify no new translations were done
            assert mock_translator.translate_text.call_count == 0
        
        # Clean up
        conn.close()
        
    def test_mark_cache_entry_used(self, test_db_path):
        """Test that marking a cache entry as used updates its timestamp."""
        # Create a database connection
        conn = init_cache_db(test_db_path)
        cursor = conn.cursor()
        
        # Add a translation to the cache
        add_to_cache("Test entry", "SV", "EN", "Testinmatning", conn)
        
        # Manually set an old timestamp to ensure it's different
        cache_hash = get_cache_hash("Test entry", "SV", "EN")
        cursor.execute(
            "UPDATE translations SET created_at = datetime('now', '-1 day') WHERE hash = ?", 
            (cache_hash,)
        )
        conn.commit()
        
        # Get the initial timestamp
        cursor.execute("SELECT created_at FROM translations WHERE hash = ?", (cache_hash,))
        initial_timestamp = cursor.fetchone()[0]
        
        # Mark the entry as used
        mark_cache_entry_used(cache_hash, conn)
        
        # Get the updated timestamp
        cursor.execute("SELECT created_at FROM translations WHERE hash = ?", (cache_hash,))
        updated_timestamp = cursor.fetchone()[0]
        
        # Verify the timestamp was updated
        assert initial_timestamp != updated_timestamp
        
        # Clean up
        conn.close()
        
    def test_delete_unused_cache_entries(self, test_db_path):
        """Test deleting unused cache entries."""
        # Create a database connection
        conn = init_cache_db(test_db_path)
        
        # Add some translations to the cache
        add_to_cache("Recent entry", "SV", "EN", "Ny inmatning", conn)
        add_to_cache("Old entry", "SV", "EN", "Gammal inmatning", conn)
        
        # Manually set the timestamp for the old entry to be in the past
        cache_hash = get_cache_hash("Old entry", "SV", "EN")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE translations SET created_at = datetime('now', '-31 days') WHERE hash = ?", 
            (cache_hash,)
        )
        conn.commit()
        
        # Delete entries older than 30 days
        deleted_count = delete_unused_cache_entries(30, conn)
        
        # Verify one entry was deleted
        assert deleted_count == 1
        
        # Verify the old entry is gone and the recent entry remains
        cursor.execute("SELECT COUNT(*) FROM translations")
        count = cursor.fetchone()[0]
        assert count == 1
        
        cursor.execute("SELECT source_text FROM translations")
        remaining_text = cursor.fetchone()[0]
        assert remaining_text == "Recent entry"
        
        # Clean up
        conn.close()
        
    def test_delete_cache_entries_containing(self, test_db_path):
        """Test deleting cache entries containing specific text."""
        # Create a database connection
        conn = init_cache_db(test_db_path)
        
        # Add some translations to the cache
        add_to_cache("Test apple", "SV", "EN", "Test äpple", conn)
        add_to_cache("Test banana", "SV", "EN", "Test banan", conn)
        add_to_cache("Orange fruit", "SV", "EN", "Apelsin frukt", conn)
        
        # Delete entries containing 'apple' in source or translation
        deleted_count = delete_cache_entries_containing("apple", conn)
        
        # Verify one entry was deleted
        assert deleted_count == 1
        
        # Delete entries containing 'Test' in source or translation
        deleted_count = delete_cache_entries_containing("Test", conn)
        
        # Verify one more entry was deleted
        assert deleted_count == 1
        
        # Verify only one entry remains
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM translations")
        count = cursor.fetchone()[0]
        assert count == 1
        
        cursor.execute("SELECT source_text FROM translations")
        remaining_text = cursor.fetchone()[0]
        assert remaining_text == "Orange fruit"
        
        # Clean up
        conn.close()
        
    def test_clear_cache(self, test_db_path):
        """Test clearing all cache entries."""
        # Create a database connection
        conn = init_cache_db(test_db_path)
        
        # Add some translations to the cache
        add_to_cache("Entry 1", "SV", "EN", "Inmatning 1", conn)
        add_to_cache("Entry 2", "SV", "EN", "Inmatning 2", conn)
        add_to_cache("Entry 3", "SV", "EN", "Inmatning 3", conn)
        
        # Verify we have 3 entries
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM translations")
        count = cursor.fetchone()[0]
        assert count == 3
        
        # Clear the cache
        deleted_count = clear_cache(conn)
        
        # Verify 3 entries were deleted
        assert deleted_count == 3
        
        # Verify the cache is empty
        cursor.execute("SELECT COUNT(*) FROM translations")
        count = cursor.fetchone()[0]
        assert count == 0
        
        # Clean up
        conn.close()
        
    def test_get_from_cache_updates_timestamp(self, test_db_path):
        """Test that getting an entry from cache updates its timestamp."""
        # Create a database connection
        conn = init_cache_db(test_db_path)
        
        # Add a translation to the cache with a manually set timestamp
        add_to_cache("Update test", "SV", "EN", "Uppdateringstest", conn)
        
        # Manually set an old timestamp
        cursor = conn.cursor()
        cache_hash = get_cache_hash("Update test", "SV", "EN")
        cursor.execute(
            "UPDATE translations SET created_at = datetime('now', '-1 hour') WHERE hash = ?", 
            (cache_hash,)
        )
        conn.commit()
        
        # Get the initial timestamp
        cursor.execute("SELECT created_at FROM translations WHERE hash = ?", (cache_hash,))
        initial_timestamp = cursor.fetchone()[0]
        
        # Get the entry from cache (should update timestamp)
        cached_translation = get_from_cache("Update test", "SV", "EN", conn)
        
        # Verify we got the correct translation
        assert cached_translation == "Uppdateringstest"
        
        # Get the updated timestamp
        cursor.execute("SELECT created_at FROM translations WHERE hash = ?", (cache_hash,))
        updated_timestamp = cursor.fetchone()[0]
        
        # Verify the timestamp was updated
        assert initial_timestamp != updated_timestamp
        
        # Clean up
        conn.close()
