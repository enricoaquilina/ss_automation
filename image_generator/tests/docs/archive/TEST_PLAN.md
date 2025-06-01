# Image Generator Test Plan

## Overview

This test plan outlines the test strategy for the Silicon Sentiments image generation service, which uses Midjourney to generate images for posts. The tests are organized into unit tests and integration tests to ensure comprehensive coverage of the codebase.

## Test Structure

- **Unit Tests**: Located in `tests/unit/`, these tests focus on testing individual functions and classes in isolation, using mocks for external dependencies.
- **Integration Tests**: Located in `tests/integration/`, these tests verify that different components work together correctly, often involving actual database operations and API calls.

## Running Tests

Use the `run_tests.py` script to execute tests:

```bash
# Run all tests
./run_tests.py

# Run only unit tests
./run_tests.py --type unit

# Run only integration tests
./run_tests.py --type integration

# Run a specific test file
./run_tests.py --test tests/unit/test_datetime_handling.py

# Run tests with a specific post ID
./run_tests.py --post-id 66b88b70b2979f6117b347f2
```

## Unit Tests

### 1. Datetime Handling (`test_datetime_handling.py`)

Tests related to the datetime handling functionality that previously caused issues:

- Tests for correct handling of datetime objects in upscale operations
- Tests for epoch time conversion and usage
- Tests for time-related calculations and comparisons

### 2. Variant Matching (`test_variant_matching.py`)

Tests related to the variant matching and grouping functionality:

- Tests for identifying upscale buttons in Discord messages
- Tests for detecting variant indices from buttons
- Tests for matching variants by message ID
- Tests for grouping variants by message ID patterns
- Tests for validating variant indices

### 3. GridFS Operations (`test_gridfs_operations.py`)

Tests related to GridFS file storage and retrieval:

- Tests for saving files to GridFS
- Tests for retrieving files from GridFS
- Tests for deleting files from GridFS
- Tests for handling generation data in the database
- Tests for file I/O operations

## Integration Tests

### 1. Post Regeneration (`test_regenerate_post.py`)

End-to-end tests for post image regeneration:

- Tests for database connection
- Tests for finding and validating posts
- Tests for cleaning post data
- Tests for regenerating post images
- Tests for verifying generation integrity
- Tests for message ID association
- Tests for variant size checking

## Existing Tests (Legacy)

The codebase already contained some test files that should be integrated into this new test structure:

- `test_prompt_formatting.py`: Tests for prompt formatting functionality
- `test_upscale_buttons.py`: Tests for detecting upscale buttons

## Future Test Additions

Consider adding tests for:

1. Error handling and recovery
2. Rate limiting and throttling
3. Midjourney API error scenarios
4. Image quality validation
5. End-to-end workflow with mocked Midjourney responses

## Test Data

Some tests require a valid post ID to function correctly. The integration tests can be configured with a specific post ID using the `--post-id` parameter.

## Continuous Integration

These tests should be integrated into the CI/CD pipeline to ensure code changes don't break existing functionality. 