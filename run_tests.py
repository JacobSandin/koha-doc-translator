#!/usr/bin/env python3
"""
Run all tests for the Koha Doc Translator

This script runs all the tests in the testing framework to verify that
RST references are correctly handled in translations.
"""

import os
import sys
import unittest
import importlib.util
import time
import argparse
from unittest.mock import patch

def import_module_from_path(module_name, file_path):
    """Import a module from a file path"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_test_module(module_path, module_name, debug=False):
    """Run tests from a module"""
    if debug:
        print(f"\n{'=' * 80}")
        print(f"Running tests from {module_name}")
        print(f"{'=' * 80}")
    else:
        print(f"Running {module_name}... ", end="")
    
    # Import the module
    module = import_module_from_path(module_name, module_path)
    
    # Capture the original stdout if not in debug mode
    original_stdout = None
    if not debug:
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
    
    try:
        # If the module has a run_tests function, use it
        if hasattr(module, 'run_tests'):
            result = module.run_tests()
        # Otherwise, try to run unittest on it
        else:
            suite = unittest.TestLoader().loadTestsFromModule(module)
            result = unittest.TextTestRunner(verbosity=2 if debug else 0).run(suite)
        
        # Restore stdout if it was redirected
        if not debug and original_stdout:
            sys.stdout.close()
            sys.stdout = original_stdout
            
        if hasattr(result, 'wasSuccessful') and not result.wasSuccessful():
            print("FAILED")
            return False
        else:
            print("OK")
            return True
    except Exception as e:
        # Restore stdout if it was redirected
        if not debug and original_stdout:
            sys.stdout.close()
            sys.stdout = original_stdout
        print(f"ERROR: {str(e)}")
        return False

def run_example_test(module_path, module_name, debug=False):
    """Run an example test script"""
    if debug:
        print(f"\n{'=' * 80}")
        print(f"Running example test from {module_name}")
        print(f"{'=' * 80}")
    else:
        print(f"Running example {module_name}... ", end="")
    
    # Capture the original stdout if not in debug mode
    original_stdout = None
    if not debug:
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
    
    try:
        # Import and run the module
        module = import_module_from_path(module_name, module_path)
        if hasattr(module, 'main'):
            module.main()
        
        # Restore stdout if it was redirected
        if not debug and original_stdout:
            sys.stdout.close()
            sys.stdout = original_stdout
        print("OK")
        return True
    except Exception as e:
        # Restore stdout if it was redirected
        if not debug and original_stdout:
            sys.stdout.close()
            sys.stdout = original_stdout
        print(f"ERROR: {str(e)}")
        return False

def run_all_tests(debug=False):
    """Run all tests in the testing framework"""
    start_time = time.time()
    
    # Get the root directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(root_dir, 'tests')
    
    # Make sure the tests directory exists
    if not os.path.isdir(tests_dir):
        print(f"Error: Tests directory not found at {tests_dir}")
        return False
    
    # Find all test modules
    test_modules = []
    example_modules = []
    
    for file in os.listdir(tests_dir):
        if file.endswith('.py') and not file.startswith('__'):
            module_path = os.path.join(tests_dir, file)
            module_name = file[:-3]  # Remove .py extension
            
            # Categorize modules
            if module_name == 'mock_translator':
                test_modules.insert(0, (module_path, module_name))  # Run first
            elif module_name == 'test_rst_references':
                test_modules.append((module_path, module_name))
            elif module_name == 'example_test':
                example_modules.append((module_path, module_name))
            elif module_name.startswith('test_'):
                test_modules.append((module_path, module_name))
            elif not module_name.startswith('add_test_case'):  # Skip utility scripts
                example_modules.append((module_path, module_name))
    
    # Run test modules
    if debug:
        print(f"Found {len(test_modules)} test modules and {len(example_modules)} example modules")
    else:
        print(f"Running {len(test_modules)} test modules and {len(example_modules)} example modules:")
    
    # Track failures
    failures = 0
    
    # Run test modules
    for module_path, module_name in test_modules:
        if not run_test_module(module_path, module_name, debug):
            failures += 1
    
    # Run example modules
    for module_path, module_name in example_modules:
        if not run_example_test(module_path, module_name, debug):
            failures += 1
    
    # Print summary
    end_time = time.time()
    duration = end_time - start_time
    
    if failures > 0:
        print(f"\nTests completed with {failures} failures in {duration:.2f} seconds")
        return False
    else:
        print(f"\nAll tests passed in {duration:.2f} seconds")
        return True

def fix_imports_in_file(file_path):
    """Fix import statements in a file to use the correct module path"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace direct imports from mock_translator with tests.mock_translator
    if 'from mock_translator import' in content:
        content = content.replace('from mock_translator import', 'from tests.mock_translator import')
        
        # Write the fixed content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed imports in {file_path}")

def prepare_tests():
    """Prepare the tests by fixing imports and ensuring the environment is set up correctly"""
    # Get the root directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(root_dir, 'tests')
    
    # Fix imports in all Python files in the tests directory
    for file in os.listdir(tests_dir):
        if file.endswith('.py') and not file.startswith('__'):
            file_path = os.path.join(tests_dir, file)
            fix_imports_in_file(file_path)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run tests for the Koha Doc Translator')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    
    # Add the current directory and tests directory to the path
    root_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(root_dir)
    sys.path.append(os.path.join(root_dir, 'tests'))
    
    # Prepare the tests
    prepare_tests()
    
    # Run all tests
    success = run_all_tests(debug=args.debug)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
