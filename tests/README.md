# Test Framework

This directory contains the test framework for the koha-doc-translator project.

## Structure

- `unit/`: Contains unit tests that test individual components in isolation
- `integration/`: Contains integration tests that test multiple components working together
- `conftest.py`: Contains shared fixtures and configuration for tests

## Running Tests

To run all tests:

```bash
pytest
```

To run a specific test file:

```bash
pytest tests/unit/test_file.py
```

To run tests with coverage:

```bash
pytest --cov=.
```

## Adding Tests

When adding new tests:

1. Place unit tests in the `unit/` directory
2. Place integration tests in the `integration/` directory
3. Follow the naming convention: `test_*.py` for test files
4. Add any shared fixtures to `conftest.py`
