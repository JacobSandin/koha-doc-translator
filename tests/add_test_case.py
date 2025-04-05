#!/usr/bin/env python3
"""
Utility script for adding new test cases to the JSON file

This script provides a simple command-line interface for adding new test cases
to the rst_test_cases.json file without having to edit the JSON directly.
"""

import os
import json
import argparse

def load_test_cases(json_file='rst_test_cases.json'):
    """Load test cases from a JSON file"""
    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), json_file)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading test cases: {e}")
        return {"test_cases": []}

def save_test_cases(data, json_file='rst_test_cases.json'):
    """Save test cases to a JSON file"""
    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), json_file)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Test cases saved to {json_file}")
    except Exception as e:
        print(f"Error saving test cases: {e}")

def add_test_case(name, original, translation=None, description=None):
    """Add a new test case to the JSON file"""
    # Load existing test cases
    data = load_test_cases()
    
    # Create the new test case
    new_case = {
        "name": name,
        "original": original,
        "translation": translation,
        "description": description or f"Test case for {name}"
    }
    
    # Add the new test case
    data["test_cases"].append(new_case)
    
    # Save the updated test cases
    save_test_cases(data)
    
    print(f"Added new test case: {name}")

def main():
    """Main function for the command-line interface"""
    parser = argparse.ArgumentParser(description='Add a new test case to the JSON file')
    parser.add_argument('--name', required=True, help='Name of the test case')
    parser.add_argument('--original', required=True, help='Original text with RST references')
    parser.add_argument('--translation', help='Translated text with issues (optional)')
    parser.add_argument('--description', help='Description of the test case (optional)')
    
    args = parser.parse_args()
    
    add_test_case(args.name, args.original, args.translation, args.description)

if __name__ == "__main__":
    main()
