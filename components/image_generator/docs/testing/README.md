# Testing Guide

This guide explains how to run tests for the Discord-Midjourney image generator component.

## Testing Prerequisites

Before running tests, make sure you have:

1. Installed all requirements from `requirements.txt`
2. Set up a `.env` file with valid Discord credentials
3. Activated your Python virtual environment (if using one)

## Setting Up Your .env File

Create a `.env` file with the following variables:
```
DISCORD_CHANNEL_ID=your_channel_id
DISCORD_GUILD_ID=your_guild_id
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_USER_TOKEN=your_user_token
MONGODB_URI=your_mongodb_uri  # Only needed for GridFS tests
```

You can have multiple `.env` files for different environments:
- `./.env` (in the root directory)
- `./components/image_generator/.env`
- `./components/image_generator/src/.env`

## Test Organization

Tests are organized into the following directory structure:

```
tests/
├── conftest.py            # Shared pytest fixtures
├── fixtures/              # Test data fixtures
├── integration/           # Integration tests with external systems
├── unit/                  # Isolated unit tests
├── pytest.ini             # Pytest configuration
├── run_tests.sh           # Script for running tests
└── various .md files      # Test documentation
```

## Running Tests

### Using the Run Script

The simplest way to run tests is using the provided `run_tests.sh` script:

```bash
cd components/image_generator
# Run all tests (excluding live tests)
./tests/run_tests.sh

# Run only unit tests
./tests/run_tests.sh --unit

# Run only integration tests
./tests/run_tests.sh --integration

# Run live tests (will make actual API calls)
./tests/run_tests.sh --live
```

### Running Specific Tests

To run specific test files or test cases:

```bash
cd components/image_generator
# Run a specific test file
python -m pytest tests/unit/test_upscale_buttons.py -v

# Run a specific test class
python -m pytest tests/unit/test_prompt_formatting.py::TestPromptFormatting -v

# Run a specific test method
python -m pytest tests/unit/test_prompt_formatting.py::TestPromptFormatting::test_model_prefix_detection -v
```

## Test Categories

### Unit Tests

Unit tests check isolated functionality without external dependencies:

- **Model Detection**: Tests for detecting v7.0 and niji models from prompts
- **Variant Matching**: Tests for matching grid variations with upscale buttons
- **Upscale Button Detection**: Tests for extracting upscale buttons from messages
- **GridFS Operations**: Tests for MongoDB storage (mocked)
- **Message Processing**: Tests for handling Discord message formats

### Integration Tests

Integration tests check interactions with external services:

- **Storage**: Tests file and MongoDB storage implementations
- **Midjourney Client**: Tests interactions with Discord/Midjourney API
- **Variation Naming**: Tests correct naming of image variations

### Live Tests

Some tests require actual API calls to Discord and Midjourney. These are marked with the `live` marker and are skipped by default. Use the `--live` flag with the run script to include them.

## Testing with the Generate Script

For end-to-end testing with real API calls:

```bash
cd components/image_generator
python generate.py --prompt "test prompt" --output-dir test_output
```

You can also test different model types:

```bash
# Test with Midjourney v7.0
python generate.py --prompt "landscape, dramatic lighting --v 7.0" --output-dir test_output

# Test with Niji 6
python generate.py --prompt "anime style character --niji" --output-dir test_output
```

## Testing GridFS Integration

To test the GridFS integration:

```bash
# Make sure MongoDB is running and accessible
python generate.py --prompt "test prompt" --gridfs --post-id "your_post_id"
```

## Cleanup After Testing

You can use the cleanup script to remove old test files:

```bash
python cleanup.py --dry-run  # See what would be removed without deleting

# To actually delete files:
python cleanup.py --all
```

## Common Test Issues

### Connection Issues
- Check your Discord tokens
- Ensure the bot is in the server
- Verify the guild and channel IDs

### Rate Limiting
- Add delays between tests (at least 60 seconds)
- Use different Discord accounts for testing
- Run fewer concurrent tests

### Missing Images
- Check if the output directory exists
- Verify the Discord bot has proper permissions
- Increase timeout settings for slow connections

### Test Fixture Issues
- If a test is failing because of missing fields in API responses, check the fixtures in `tests/fixtures/`
- Update test data in `test_data.py` if Discord/Midjourney API responses have changed

## Further Documentation

For more detailed test documentation, see:
- `tests/MIDJOURNEY_TESTING.md` - General testing approach
- `tests/TEST_PLAN.md` - Comprehensive test plan
- `tests/CONSOLIDATED_TEST_PLAN.md` - Test tracking
- `tests/SUMMARY.md` - Test results summary 