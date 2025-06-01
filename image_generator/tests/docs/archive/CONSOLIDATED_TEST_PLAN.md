# Consolidated Image Generator Test Plan

## Current Test Structure

The image generator currently has tests in multiple locations:

1. `tests/unit/` - Unit tests for individual components
2. `tests/integration/` - Integration tests for end-to-end functionality
3. `src/tests/` - Additional test files:
   - `manual_test_upscale_processing.py` - Manual tests for upscale processing
   - `test_upscale_processing.py` - Unit tests for upscale processing

## Proposed Consolidated Structure

We will consolidate all tests into the existing `tests/` directory at the component root, while maintaining the separation between different test types:

```
components/image_generator/tests/
├── unit/                        # Unit tests for individual components
│   ├── test_content_aware_prompt_generator.py
│   ├── test_variation_name_handling.py
│   ├── test_gridfs_operations.py
│   ├── test_variant_matching.py
│   ├── test_datetime_handling.py
│   ├── test_prompt_formatting.py
│   ├── test_upscale_buttons.py
│   └── test_upscale_processing.py  # Moved from src/tests
├── integration/                # Integration tests for end-to-end functionality
│   ├── test_variation_naming_integration.py
│   └── test_regenerate_post.py
├── manual/                     # Manual tests that require user interaction or monitoring
│   └── manual_test_upscale_processing.py  # Moved from src/tests
├── fixtures/                   # Common test fixtures and mock data
│   └── test_data.py
├── conftest.py                 # Common pytest configuration and fixtures
├── __init__.py
├── run_tests.py                # Main test runner
├── run_tests.sh                # Shell script for running tests
└── README.md                   # Updated documentation
```

## Migration Plan

1. **Create new directories**:
   - Create a `manual/` directory for manual tests
   - Create a `fixtures/` directory for common test data and fixtures

2. **Move existing tests**:
   - Move `src/tests/test_upscale_processing.py` to `tests/unit/`
   - Move `src/tests/manual_test_upscale_processing.py` to `tests/manual/`

3. **Update imports**:
   - Update import paths in moved files to reflect their new location
   - Review and update any relative imports

4. **Create common fixtures**:
   - Extract common test setup code into fixtures
   - Create a `conftest.py` file for pytest fixtures

5. **Update test runner**:
   - Update `run_tests.py` to discover and run tests from the new locations
   - Add support for running manual tests with an explicit flag

## Implementation Notes

1. **Import Paths**:
   - Tests should use absolute imports from the package root
   - For example: `from image_generator.services.generation_service import GenerationService`

2. **Test Dependencies**:
   - All test dependencies should be isolated from production code
   - Mock external services where appropriate

3. **Test Documentation**:
   - Each test file should have a docstring explaining its purpose
   - Complex test cases should include comments explaining their intent

## Benefits of Consolidation

1. **Improved Organization**:
   - All tests in one location
   - Clear separation between test types

2. **Simplified Discovery**:
   - One place to look for all tests
   - Easier to see test coverage

3. **Consistent Patterns**:
   - Standardized import patterns
   - Consistent test structure

4. **Easier Maintenance**:
   - Test-related changes in one location
   - Reusable fixtures and setup code

## Next Steps

After consolidation, we recommend:

1. **Increase test coverage**:
   - Identify and address gaps in test coverage
   - Add more tests for edge cases

2. **Automate test runs**:
   - Add CI/CD integration for automated testing
   - Set up test reports and coverage metrics

3. **Improve documentation**:
   - Document test patterns and best practices
   - Create examples for writing new tests 