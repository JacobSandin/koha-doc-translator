import os
import sys
import re
import pytest
from pathlib import Path

# Add the parent directory to the path so we can import the translate module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class TestPotRegexValidation:
    """Test cases for regex validation patterns in .pot files."""
    
    @pytest.fixture
    def sample_pot_path(self):
        """Get the path to the sample.pot file."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fixtures_dir = os.path.join(script_dir, "fixtures")
        return os.path.join(fixtures_dir, "sample.pot")
    
    def extract_msgid_with_regex(self, pot_file_path):
        """
        Extract msgid entries with their associated regex patterns from a .pot file.
        
        Args:
            pot_file_path (str): Path to the .pot file
            
        Returns:
            list: List of tuples (msgid, regex_success, regex_fail)
        """
        with open(pot_file_path, 'r') as f:
            content = f.read()
        
        # Split the content into message blocks
        blocks = re.split(r'\n\n', content)
        
        results = []
        for block in blocks:
            # Skip header or empty blocks
            if not block.strip() or block.startswith('#,') or 'msgid ""' in block and 'msgstr ""' in block and '"Project-Id-Version' in block:
                continue
            
            # Extract msgid
            msgid_match = re.search(r'msgid "(.*?)"', block)
            if not msgid_match:
                continue
            
            msgid = msgid_match.group(1)
            
            # Extract regex patterns
            regex_success = None
            regex_fail = None
            
            success_match = re.search(r'# regex_success "(.*?)"', block)
            if success_match:
                regex_success = success_match.group(1)
            
            fail_match = re.search(r'# regex_fail "(.*?)"', block)
            if fail_match:
                regex_fail = fail_match.group(1)
            
            if msgid and (regex_success or regex_fail):
                results.append((msgid, regex_success, regex_fail))
        
        return results
    
    def test_extract_regex_patterns(self, sample_pot_path):
        """Test that regex patterns can be extracted from the .pot file."""
        patterns = self.extract_msgid_with_regex(sample_pot_path)
        
        # Verify we found patterns
        assert len(patterns) > 0
        
        # Check a few specific entries
        for msgid, regex_success, regex_fail in patterns:
            if msgid == "Installation":
                assert regex_success == "^Installation$"
                assert regex_fail == "^installation$"
            elif msgid == "Prerequisites":
                assert regex_success == "^Förutsättningar$"
                assert regex_fail == "^Krav$"
    
    def test_validate_translations_with_regex(self, sample_pot_path):
        """Test that translations can be validated using the regex patterns."""
        patterns = self.extract_msgid_with_regex(sample_pot_path)
        
        # Create a mapping of msgid to expected translations
        translation_map = {
            "Installation": {
                "success": "Installation",
                "fail": "installation"
            },
            "This chapter provides instructions for installing Koha.": {
                "success": "Detta kapitel ger instruktioner för installation av Koha.",
                "fail": "Detta kapitel ger instruktioner för att installera Koha."
            },
            "Prerequisites": {
                "success": "Förutsättningar",
                "fail": "Krav"
            },
            "The following prerequisites are required for installation:": {
                "success": "Följande förutsättningar krävs för installation:",
                "fail": "Följande krav krävs för installation"
            },
            "Linux operating system": {
                "success": "Linux-operativsystem",
                "fail": "Linux operativ system"
            },
            "Apache web server": {
                "success": "Apache webbserver",
                "fail": "Apache web server"
            },
            "MySQL or MariaDB database server": {
                "success": "MySQL eller MariaDB databasserver",
                "fail": "MySQL eller MariaDB databas server"
            },
            "Perl programming language": {
                "success": "Programmeringsspråket Perl",
                "fail": "Perl programmeringsspråk"
            }
        }
        
        # Test validation for each pattern
        for msgid, regex_success, regex_fail in patterns:
            if not regex_success or not regex_fail:
                continue
            
            # Get the appropriate translations for this msgid
            if msgid in translation_map:
                success_translation = translation_map[msgid]["success"]
                fail_translation = translation_map[msgid]["fail"]
                
                # Test success pattern
                success_pattern = re.compile(regex_success)
                assert success_pattern.match(success_translation) is not None, f"Success pattern '{regex_success}' failed to match '{success_translation}' for msgid '{msgid}'"
                
                # Test fail pattern
                fail_pattern = re.compile(regex_fail)
                assert fail_pattern.match(fail_translation) is not None, f"Fail pattern '{regex_fail}' failed to match '{fail_translation}' for msgid '{msgid}'"
                
                # Cross-check (success pattern should not match fail translation)
                assert success_pattern.match(fail_translation) is None, f"Success pattern '{regex_success}' incorrectly matched '{fail_translation}' for msgid '{msgid}'"
    
    def test_all_entries_have_regex(self, sample_pot_path):
        """Test that all msgid entries in the sample have regex patterns."""
        with open(sample_pot_path, 'r') as f:
            content = f.read()
        
        # Get all msgid entries (excluding the header)
        msgid_pattern = re.compile(r'msgid "((?!Project-Id-Version).+?)"')
        msgids = msgid_pattern.findall(content)
        
        # Get all entries with regex patterns
        patterns = self.extract_msgid_with_regex(sample_pot_path)
        pattern_msgids = [p[0] for p in patterns]
        
        # Verify all msgids have patterns
        for msgid in msgids:
            if msgid:  # Skip empty msgid
                assert msgid in pattern_msgids, f"msgid '{msgid}' does not have regex patterns"
