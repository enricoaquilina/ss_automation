# Image Generator Test Plan

This document outlines the comprehensive test coverage for the Silicon Sentiments Image Generator component, ensuring all functionality from the "tests memory bank" is properly tested.

## Core Functionality Test Coverage

| Requirement | Test Files | Status |
|-------------|------------|--------|
| **Discord Authentication** | | |
| Authenticate with Discord Gateway | `test_discord_auth.py` | ✅ Implemented |
| Auth Discord Gateway (WebSockets) | `test_discord_auth.py`, `test_midjourney_workflow.py` | ✅ Implemented |
| **Command Communication** | | |
| Send Slash Commands | `test_slash_commands.py` | ✅ Implemented |
| Send Requests using Interactions API | `test_slash_commands.py`, `test_midjourney_workflow.py` | ✅ Implemented |
| **Message Handling** | | |
| Listen for Messages (WebSocket/Polling) | `test_midjourney_workflow.py`, `test_imagine_upscale_workflow.py` | ✅ Implemented |
| Listen for Generation/Upscale Messages | `test_midjourney_workflow.py`, `test_imagine_upscale_workflow.py` | ✅ Implemented |
| **Image Processing** | | |
| Upscale Message Images | `test_imagine_upscale_workflow.py`, `run_real_test.py` | ✅ Implemented |
| **Storage** | | |
| Save Upscaled Images to GridFS | `test_gridfs_storage.py` | ✅ Implemented |
| Downloads to Local Dir in Specific Dir | `test_storage.py`, `run_real_test.py` | ✅ Implemented |
| Download Metadata (Generation/Prompt/Upscales) | `test_gridfs_storage.py` | ✅ Implemented |
| **Upscale Correlation** | | |
| Verify Upscale Image Correlation | `test_upscale_correlation.py` | ✅ Implemented |
| Track Message Timestamps | `test_upscale_correlation.py` | ✅ Implemented |
| Match Prompts Between Grid and Upscales | `test_upscale_correlation.py` | ✅ Implemented |
| Maintain Grid Message References | `test_upscale_correlation.py` | ✅ Implemented |
| **Image Generation Options** | | |
| Use Different Aspect Ratios | `test_aspect_ratios.py` | ✅ Implemented |
| Use Different Versions | `test_midjourney_workflow.py` (via prompt parameters) | ✅ Implemented |
| Use Various Prompts | All generation tests | ✅ Implemented |

## Test Types

### Unit Tests
Unit tests verify individual components and methods in isolation:

- Error classes and handling
- Rate limiting functionality
- DateTime handling
- Prompt formatting
- Variant matching and naming
- Upscale button extraction and processing

### Integration Tests  
Integration tests verify the interaction between components and external services:

- Discord authentication and API communication
- Slash command formatting and sending
- Imagine/upscale workflow
- Storage mechanisms (filesystem and GridFS)
- End-to-end generation and upscaling process

### Live Tests
Tests that interact with the actual Discord/Midjourney services:

- `test_midjourney_live_workflow.py`: Complete workflow with real API
- `run_real_test.py`: Manual live testing tool

## Test Execution

### Running All Tests
```bash
cd components/image_generator/tests
./run_all_tests.sh all
```

### Running Specific Test Categories
```bash
# Unit tests only
./run_all_tests.sh unit

# Integration tests only
./run_all_tests.sh integration

# Live tests (uses Midjourney credits)
export FULLY_MOCKED=false
./run_all_tests.sh live
```

### Running Individual Tests
```bash
# Run a specific test file
python -m pytest integration/test_slash_commands.py -v

# Run a specific test case
python -m pytest integration/test_slash_commands.py::TestSlashCommands::test_imagine_command_format -v
```

## Adding New Tests

When adding new tests:

1. Determine the appropriate test category (unit, integration, live)
2. Follow existing naming conventions
3. Add proper documentation and assertions
4. Update this test plan document

## Mocking vs. Live Testing

Most tests should use mocking to avoid consuming Midjourney credits. Set the `FULLY_MOCKED=true` environment variable to ensure all tests use mocks.

For actual verification with the real API, use:
```bash
python run_real_test.py --prompt "your test prompt" --output-dir test_output
``` 