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
    translate_text
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
        # Use a completely different approach that doesn't rely on mocking the translator
        # Instead, we'll directly add items to the cache and then check if they're used
        
        # Create a database connection
        conn = init_cache_db(test_db_path)
        
        # Add translations directly to the cache
        add_to_cache("Hello", "SV", "EN", "Hej", conn)
        add_to_cache("World", "SV", "EN", "Världen", conn)
        
        # Create a mock translator that will fail if called
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = Exception("This should not be called")
        
        with patch('translate.get_translator', return_value=mock_translator):
            # This should use the cache and not call the translator
            result = translate_text(["Hello", "World"], disable_cache=False, conn=conn)
            
            # Verify the result is correct
            assert result == ["Hej", "Världen"]
            
            # Verify the translator was not called
            mock_translator.translate_text.assert_not_called()
        
        # Clean up
        conn.close()
