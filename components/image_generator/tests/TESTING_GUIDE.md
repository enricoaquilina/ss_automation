# Testing Guide - Image Generator Component

## Overview

This guide covers the refactored test suite for the Silicon Sentiments Image Generator component. The test suite has been reorganized for better CI/CD integration, clearer categorization, and simplified execution.

## Quick Start

### Running Tests Locally

```bash
# Navigate to the tests directory
cd components/image_generator/tests

# Run quick unit tests (< 10 seconds)
./run_tests.py --category quick

# Run all unit tests (< 30 seconds)
./run_tests.py --category unit

# Run integration tests with mocked APIs (< 2 minutes)
./run_tests.py --category integration

# Run end-to-end tests with live APIs (> 5 minutes, costs credits!)
./run_tests.py --category e2e

# List all available categories
./run_tests.py --list
```

### CI/CD Ready Commands

```bash
# CI mode (no confirmations, structured output)
./run_tests.py --category unit --ci --format json

# Force mock mode for all tests
./run_tests.py --category all --mock-mode

# Verbose output with fail-fast
./run_tests.py --category integration --verbose --fail-fast
```

## Test Categories

### 🚀 Quick Tests (`--category quick`)
- **Duration**: < 10 seconds
- **Purpose**: Fastest feedback during development
- **Contents**: Basic functionality, error handling, rate limiting
- **Safe for**: Continuous development, pre-commit hooks

### 🧪 Unit Tests (`--category unit`)
- **Duration**: < 30 seconds  
- **Purpose**: Isolated component testing
- **Contents**: All unit tests including mocks, validation, processing
- **Safe for**: Pull request validation, local development

### 🔗 Integration Tests (`--category integration`)
- **Duration**: < 2 minutes
- **Purpose**: Component interaction testing with mocked external APIs
- **Contents**: Storage, workflow, Discord integration (mocked)
- **Safe for**: CI/CD pipelines, comprehensive testing

### 🚀 End-to-End Tests (`--category e2e`)
- **Duration**: > 5 minutes
- **Purpose**: Full workflow testing with live APIs
- **Contents**: Real Discord/Midjourney API interactions
- **⚠️ Warning**: Consumes Midjourney credits, use sparingly

## Environment Setup

### Required Files

Create a `.env` file in `components/image_generator/`:

```bash
# Discord credentials (required for live tests)
DISCORD_USER_TOKEN=your_user_token_here
DISCORD_BOT_TOKEN=your_bot_token_here  
DISCORD_CHANNEL_ID=your_channel_id_here
DISCORD_GUILD_ID=your_guild_id_here

# MongoDB connection (optional, for GridFS tests)
MONGODB_URI=mongodb://username:password@hostname:port/database

# Test configuration
TEST_PROMPT="beautiful cosmic space dolphin, digital art style"
LOG_LEVEL=INFO
```

### Dependencies

Install Python dependencies:

```bash
cd components/image_generator
pip install -r requirements.txt
```

Required packages:
- `pytest>=7.0.0`
- `pytest-asyncio>=0.18.0`
- `aiohttp>=3.8.0`
- `python-dotenv>=0.19.0`
- `pymongo>=4.0.0` (optional, for MongoDB tests)

## CI/CD Integration

### GitHub Actions Workflow

The test suite includes a comprehensive GitHub Actions workflow (`.github/workflows/test.yml`) with:

#### Jobs Structure
1. **Unit Tests**: Fast tests on every push/PR
2. **Integration Tests**: Mocked integration tests on every push/PR  
3. **E2E Tests**: Live API tests only on main branch pushes
4. **Test Summary**: Aggregated results and artifacts

#### Branch Strategy
- **Feature branches/PRs**: Unit + Integration tests only
- **Main branch**: All tests including expensive E2E tests
- **Develop branch**: Full test suite

#### Secrets Configuration

Configure these secrets in your GitHub repository:

```
DISCORD_USER_TOKEN=your_discord_user_token
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_discord_channel_id
DISCORD_GUILD_ID=your_discord_guild_id
MONGODB_URI=your_mongodb_connection_string
```

### Local Pre-commit Setup

Add to your `.git/hooks/pre-commit`:

```bash
#!/bin/bash
cd components/image_generator/tests
./run_tests.py --category quick --ci
exit $?
```

## Advanced Usage

### Custom Test Runs

```bash
# Run specific test files
python -m pytest unit/test_rate_limiter.py -v

# Run tests with specific markers
python -m pytest -m "not slow" -v

# Run tests with coverage
python -m pytest --cov=src unit/ -v

# Debug mode with detailed output
python -m pytest unit/test_mock_client.py -v -s --log-cli-level=DEBUG
```

### Environment Variables

Control test behavior with environment variables:

```bash
# Force mock mode
export FULLY_MOCKED=true

# Enable live testing
export LIVE_TEST=true

# Custom output directory
export TEST_DOWNLOAD_DIR=/custom/path/test_output

# Verbose logging
export LOG_LEVEL=DEBUG
```

### Output Formats

```bash
# JSON output for CI systems
./run_tests.py --category unit --format json

# JUnit XML for test reporting tools
./run_tests.py --category integration --format junit

# Console output (default)
./run_tests.py --category unit --format console
```

## Test Development Guidelines

### Adding New Tests

1. **Choose the right category**:
   - Unit tests: Fast, isolated, no external dependencies
   - Integration: Component interactions, mocked external APIs
   - E2E: Full workflows with live APIs

2. **Follow naming conventions**:
   - `test_*.py` for test files
   - `test_*` for test functions
   - Use descriptive names

3. **Use appropriate fixtures**:
   - `mock_midjourney_client` for unit tests
   - `midjourney_client` for live tests
   - `filesystem_storage` or `gridfs_storage` for storage tests

### Test Structure Example

```python
import pytest
import pytest_asyncio

class TestFeatureName:
    """Test class for specific feature"""
    
    def test_unit_functionality(self, mock_midjourney_client):
        """Unit test with mocked dependencies"""
        # Test implementation
        pass
        
    @pytest_asyncio.async_test
    async def test_integration_workflow(self, mock_midjourney_client):
        """Integration test with async operations"""
        # Test implementation
        pass
        
    @pytest.mark.skip(reason="Expensive live test")
    async def test_live_api_integration(self, midjourney_client):
        """Live test that consumes API credits"""
        # Test implementation
        pass
```

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure PYTHONPATH is set correctly
export PYTHONPATH="$PYTHONPATH:$(pwd)/.."

# Or run from the correct directory
cd components/image_generator/tests
```

#### Authentication Failures
```bash
# Test Discord credentials
python -c "import os; print('Token available:', bool(os.environ.get('DISCORD_USER_TOKEN')))"

# Run auth validation test
python -m pytest integration/test_discord_auth.py -v
```

#### MongoDB Connection Issues
```bash
# Test MongoDB connection
python -c "from pymongo import MongoClient; MongoClient(os.environ.get('MONGODB_URI')).admin.command('ping')"

# Skip MongoDB tests
./run_tests.py --category unit  # MongoDB not required for unit tests
```

### Performance Issues

#### Slow Test Execution
- Use `--category quick` for fastest feedback
- Enable parallel execution with pytest-xdist: `pip install pytest-xdist`
- Use `--fail-fast` to stop on first failure

#### High Memory Usage
- Run tests in smaller batches
- Clean test output regularly: `rm -rf test_output/* test_logs/*`
- Monitor with: `./run_tests.py --category unit --verbose`

### Debugging Failed Tests

```bash
# Run single test with full output
python -m pytest unit/test_rate_limiter.py::TestRateLimiter::test_specific_method -v -s

# Enable debug logging
python -m pytest unit/test_mock_client.py -v --log-cli-level=DEBUG

# Capture stdout/stderr
python -m pytest integration/test_storage.py -v -s --capture=no
```

## Migration from Legacy Test System

### Backward Compatibility

The legacy `run_all_tests.sh` remains functional during the transition period. To migrate:

1. **Update your local workflow**:
   ```bash
   # Old way
   ./run_all_tests.sh 1
   
   # New way  
   ./run_tests.py --category unit
   ```

2. **Update CI scripts**:
   ```yaml
   # Old CI configuration
   - run: ./tests/run_all_tests.sh 1
   
   # New CI configuration
   - run: ./tests/run_tests.py --category unit --ci
   ```

3. **Update documentation references**:
   - Replace references to old test scripts
   - Update team onboarding guides
   - Update README files

### Key Differences

| Aspect | Legacy System | New System |
|--------|---------------|------------|
| Interface | Bash script with numbered options | Python script with named categories |
| Categories | Numbered choices (1-10) | Named categories (unit, integration, e2e) |
| CI Integration | Basic bash output | Structured JSON/JUnit output |
| Parallelization | Manual | Automatic where safe |
| Environment Validation | Basic checks | Comprehensive validation |
| Report Generation | Console only | Multiple formats |

## Best Practices

### Development Workflow

1. **Start with quick tests**: `./run_tests.py --category quick`
2. **Run full unit tests**: `./run_tests.py --category unit`
3. **Run integration tests before PR**: `./run_tests.py --category integration`
4. **Reserve E2E tests for final validation**: Manual trigger only

### CI/CD Workflow

1. **Every commit**: Quick + Unit tests
2. **Pull requests**: Unit + Integration tests
3. **Main branch**: Full test suite including E2E
4. **Release candidates**: Manual E2E test validation

### Cost Management

- **Use mock mode by default**: `--mock-mode` flag
- **Limit E2E tests**: Only on main branch or manual trigger
- **Monitor API usage**: Track Midjourney credit consumption
- **Use test budgets**: Set limits on expensive test execution

## Support and Feedback

- **Issues**: Report test-related issues in the project issue tracker
- **Documentation**: Contribute improvements to this guide
- **Feature requests**: Suggest test infrastructure improvements

For more detailed information about specific test categories or troubleshooting, see the individual test documentation files in the `docs/` directory.