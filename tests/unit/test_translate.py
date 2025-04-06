"""
Unit tests for the translate module.
"""
import pytest
from unittest.mock import patch, MagicMock

from translate import get_translator, translate_text, init_cache_db

class TestTranslate:
    """Test cases for the translate module."""
    
    def test_get_translator_with_api_key(self):
        """Test that get_translator returns a translator when API key is available."""
        with patch('os.getenv', return_value='fake_api_key'):
            with patch('deepl.Translator') as mock_translator_class:
                # Set up the mock
                mock_translator = MagicMock()
                mock_translator_class.return_value = mock_translator
                
                # Call the function
                translator = get_translator()
                
                # Verify the translator was created with the correct API key
                mock_translator_class.assert_called_once_with('fake_api_key')
                assert translator == mock_translator
    
    def test_get_translator_without_api_key(self):
        """Test that get_translator raises ValueError when API key is not available."""
        with patch('os.getenv', return_value=None):
            with pytest.raises(ValueError) as excinfo:
                get_translator()
            
            assert "DeepL API key not found" in str(excinfo.value)
    
    def test_translate_text_single_string(self):
        """Test translating a single string."""
        # Create a mock translator
        mock_translator = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "Hej världen"
        mock_translator.translate_text.return_value = mock_result
        
        with patch('translate.get_translator', return_value=mock_translator):
            # Disable cache for this test
            result = translate_text("Hello world", "SV", "EN", disable_cache=True)
            
            # Verify the translator was called with the correct parameters
            mock_translator.translate_text.assert_called_once_with(
                "Hello world", 
                target_lang="SV", 
                source_lang="EN"
            )
            
            # Verify the result
            assert result == "Hej världen"
    
    def test_translate_text_list_of_strings(self):
        """Test translating a list of strings."""
        # Create a mock translator
        mock_translator = MagicMock()
        
        def mock_translate_side_effect(text, **kwargs):
            mock_result = MagicMock()
            if text == "Hello":
                mock_result.text = "Hej"
            elif text == "World":
                mock_result.text = "Världen"
            return mock_result
        
        mock_translator.translate_text.side_effect = mock_translate_side_effect
        
        with patch('translate.get_translator', return_value=mock_translator):
            # Disable cache for this test
            result = translate_text(["Hello", "World"], "SV", "EN", disable_cache=True)
            
            # With the new implementation, translate_text is called once for each item in the list
            assert mock_translator.translate_text.call_count == 2
            
            # Verify the result
            assert result == ["Hej", "Världen"]
    
    def test_translate_text_with_exception(self):
        """Test that exceptions during translation are properly handled."""
        # Create a mock translator that raises an exception
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = Exception("API error")
        
        with patch('translate.get_translator', return_value=mock_translator):
            with pytest.raises(Exception) as excinfo:
                # Disable cache for this test
                translate_text("Hello world", "SV", "EN", disable_cache=True)
            
            assert "API error" in str(excinfo.value)
    
    def test_translate_text_default_parameters(self):
        """Test that default parameters are used correctly."""
        # Create a mock translator
        mock_translator = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "Hej världen"
        mock_translator.translate_text.return_value = mock_result
        
        with patch('translate.get_translator', return_value=mock_translator):
            # Disable cache for this test
            result = translate_text("Hello world", disable_cache=True)
            
            # Verify the translator was called with the default parameters
            mock_translator.translate_text.assert_called_once_with(
                "Hello world", 
                target_lang="SV", 
                source_lang="EN"
            )
            
            # Verify the result
            assert result == "Hej världen"
