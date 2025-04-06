"""
Configuration file for pytest.
Contains shared fixtures and setup for tests.
"""
import os
import sys
import pytest

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Add your fixtures here as needed
# Example:
# @pytest.fixture
# def sample_data():
#     return {"key": "value"}
