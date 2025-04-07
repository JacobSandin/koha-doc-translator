import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the parent directory to the path so we can import the translate module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from translate import (
    get_locale_path,
    find_pot_file,
    find_all_pot_files,
    process_pot_file
)

class TestPotFileHandling:
    """Test cases for the .pot file handling functionality."""
    
    @pytest.fixture
    def mock_repo_path(self, tmp_path):
        """Create a temporary repository structure for testing."""
        # Create locale directory
        locale_path = tmp_path / "build" / "locale"
        locale_path.mkdir(parents=True, exist_ok=True)
        
        # Create some test .pot files
        (locale_path / "test1.pot").write_text("test content 1")
        (locale_path / "test2.pot").write_text("test content 2")
        (locale_path / "installation.pot").write_text("installation content")
        
        return tmp_path
    
    def test_get_locale_path_with_repo_path(self, mock_repo_path):
        """Test that get_locale_path returns the correct path when repo_path is provided."""
        expected_path = os.path.join(mock_repo_path, "build", "locale")
        result = get_locale_path(repo_path=mock_repo_path)
        assert result == expected_path
        
    def test_get_locale_path_with_pot_file_dir(self, tmp_path):
        """Test that get_locale_path returns pot_file_dir when provided."""
        custom_dir = tmp_path / "custom_pot_files"
        custom_dir.mkdir()
        result = get_locale_path(pot_file_dir=str(custom_dir))
        assert result == str(custom_dir)
    
    def test_find_pot_file_exact_match(self, mock_repo_path):
        """Test that find_pot_file finds an exact match with repo_path."""
        result = find_pot_file("test1", repo_path=mock_repo_path)
        expected_path = os.path.join(mock_repo_path, "build", "locale", "test1.pot")
        assert result == expected_path
        
    def test_find_pot_file_with_pot_file_dir(self, tmp_path):
        """Test that find_pot_file works with pot_file_dir."""
        # Create a test pot file in a custom directory
        custom_dir = tmp_path / "custom_pot_files"
        custom_dir.mkdir()
        test_pot_file = custom_dir / "custom.pot"
        test_pot_file.write_text("custom content")
        
        result = find_pot_file("custom", pot_file_dir=str(custom_dir))
        assert result == str(test_pot_file)
    
    def test_find_pot_file_partial_match(self, mock_repo_path):
        """Test that find_pot_file finds a partial match."""
        result = find_pot_file("install", repo_path=mock_repo_path)
        expected_path = os.path.join(mock_repo_path, "build", "locale", "installation.pot")
        assert result == expected_path
    
    def test_find_pot_file_no_match(self, mock_repo_path):
        """Test that find_pot_file returns None when no match is found."""
        result = find_pot_file("nonexistent", repo_path=mock_repo_path)
        assert result is None
    
    def test_find_pot_file_nonexistent_directory(self, tmp_path):
        """Test that find_pot_file handles nonexistent directories."""
        nonexistent_path = tmp_path / "nonexistent"
        result = find_pot_file("test", repo_path=nonexistent_path)
        assert result is None
    
    def test_find_all_pot_files(self, mock_repo_path):
        """Test that find_all_pot_files finds all .pot files with repo_path."""
        result = find_all_pot_files(repo_path=mock_repo_path)
        assert len(result) == 3
        
        # Check that all expected files are in the result
        expected_files = ["test1.pot", "test2.pot", "installation.pot"]
        for file in expected_files:
            expected_path = os.path.join(mock_repo_path, "build", "locale", file)
            assert expected_path in result
            
    def test_find_all_pot_files_with_pot_file_dir(self, tmp_path):
        """Test that find_all_pot_files works with pot_file_dir."""
        # Create test pot files in a custom directory
        custom_dir = tmp_path / "custom_pot_files"
        custom_dir.mkdir()
        (custom_dir / "file1.pot").write_text("content 1")
        (custom_dir / "file2.pot").write_text("content 2")
        
        result = find_all_pot_files(pot_file_dir=str(custom_dir))
        assert len(result) == 2
        
        # Check that all expected files are in the result
        expected_files = ["file1.pot", "file2.pot"]
        for file in expected_files:
            expected_path = os.path.join(str(custom_dir), file)
            assert expected_path in result
    
    def test_find_all_pot_files_empty_directory(self, tmp_path):
        """Test that find_all_pot_files returns an empty list for directories with no .pot files."""
        empty_locale_path = tmp_path / "build" / "locale"
        empty_locale_path.mkdir(parents=True, exist_ok=True)
        
        result = find_all_pot_files(repo_path=tmp_path)
        assert result == []
    
    def test_find_all_pot_files_nonexistent_directory(self, tmp_path):
        """Test that find_all_pot_files handles nonexistent directories."""
        nonexistent_path = tmp_path / "nonexistent"
        result = find_all_pot_files(repo_path=nonexistent_path)
        assert result == []
    
    def test_process_pot_file(self, mock_repo_path):
        """Test that process_pot_file returns True (placeholder implementation)."""
        pot_file = os.path.join(mock_repo_path, "build", "locale", "test1.pot")
        result = process_pot_file(pot_file)
        assert result is True
