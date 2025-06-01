# Midjourney Integration Testing Documentation

## 1. Overview

This document outlines the comprehensive testing strategy for the Midjourney image generation workflow, focusing on ensuring all 4 upscale variants are properly generated, processed, and stored in both the filesystem and MongoDB.

## 2. Original Issue

The system was only generating and storing 3 variants instead of the expected 4 upscale variants when using the Midjourney API via Discord. Investigation revealed several issues:

1. Parameter inconsistency between `message_id` and `grid_message_id` in function calls
2. Missing client implementation (only a symlink existed pointing to a non-existent file)
3. Inconsistent API parameter handling across the codebase
4. Failure to process all 4 variants in the upscale workflow

## 3. Implemented Solutions

### 3.1 Client Implementation

Created a robust `MidjourneyClient` class that:
- Supports both older and newer API formats
- Uses consistent parameter naming
- Operates in both mock mode and real API mode
- Properly handles all 4 upscale variants
- Includes comprehensive error handling

### 3.2 Testing Components

A multi-layered testing approach with:

1. **Unit Tests** for API call construction verification
2. **Mock Client Tests** for workflow validation without real API calls
3. **Integration Tests** for actual Discord API interactions
4. **Workflow Verification** for end-to-end system validation

## 4. Test Components Details

### 4.1 Unit Tests (`test_midjourney_message_sending.py`)

Tests that ensure Discord API calls are constructed properly:

| Test | Purpose | Status | Notes |
|------|---------|--------|-------|
| `test_send_generation_command` | Verify generation command API construction | ✅ PASS | Tests Discord message construction with proper command format |
| `test_button_click` | Verify button clicks for upscale requests | ✅ PASS | Tests interaction with upscale buttons using correct custom IDs |
| `test_process_all_upscale_buttons` | Process all 4 upscale buttons | ✅ PASS | Confirms all 4 (U1-U4) button clicks are properly issued |
| `test_get_message` | Verify message retrieval | ✅ PASS | Tests API call to Discord for getting message content |

### 4.2 Mock Client Tests (`test_mock_client.py`)

Tests the complete workflow without real API calls:

| Test | Purpose | Status | Notes |
|------|---------|--------|-------|
| Grid Generation | Create grid image | ✅ PASS | Successfully generates grid image with 4 variants |
| MongoDB Storage | Save grid to MongoDB | ✅ PASS | Correctly stores grid metadata with grid_message_id |
| Process Variants | Process all 4 upscale variants | ✅ PASS | All variants (0-3) are processed |
| MongoDB Variants | Store all variants in MongoDB | ✅ PASS | All variants stored with correct grid_message_id reference |
| Filesystem Storage | Save all images to filesystem | ✅ PASS | All variants saved with proper metadata |

### 4.3 Integration Tests (`test_midjourney_api.py`)

Tests for actual Discord API interactions:

| Test | Purpose | Status | Notes |
|------|---------|--------|-------|
| `test_01_send_generate_command` | Test sending generation command | ✅ PASS | Verifies real API request construction |
| `test_02_process_grid_and_upscale` | Test upscale button processing | ✅ PASS | Confirms proper handling of all 4 buttons |
| `test_03_verify_parameter_consistency` | Test parameter consistency | ✅ PASS | Ensures grid_message_id is used consistently |

### 4.4 Workflow Verification (`verify_midjourney_workflow.py`)

Complete end-to-end verification:

| Test | Purpose | Status | Notes |
|------|---------|--------|-------|
| Generate Grid | Create grid image | ✅ PASS | Grid image generation succeeds |
| Process All Variants | Handle all 4 variants | ✅ PASS | All 4 variants (U1-U4) are processed |
| MongoDB Verification | Verify all records | ✅ PASS | All records correctly stored with proper relationships |
| Variant Indices | Check all variant indices | ✅ PASS | Indices 0-3 all exist in the database |

## 5. Test Results

### 5.1 Mock Client Test Results

The mock client tests successfully:
- Generated grid images for both v6.0 and v7.0
- Processed all 4 upscale variants for each version
- Stored proper metadata including `grid_message_id` references
- Created filesystem files with correct naming conventions
- Saved all data to MongoDB with proper relationships

**Output Files:**
- Grid: `v6.0_grid.png` (with metadata)
- Variants: `v6.0_variant_0.png` through `v6.0_variant_3.png` (with metadata)

### 5.2 Unit Test Results

All unit tests passed, confirming:
- Proper API call construction for image generation
- Correct handling of upscale button interactions
- Complete processing of all 4 variant requests
- Proper parameter passing between components

### 5.3 Live Workflow Test

For testing with real API calls, a new integration test has been created: `test_midjourney_live_workflow.py` which:
- Loads credentials from a `.env` file
- Makes actual API calls to Discord/Midjourney
- Generates real images with a unique test ID
- Processes all 4 upscale variants
- Verifies correct data in MongoDB
- Stores downloaded images for inspection

To run this test:

1. Create a `.env` file in the components directory with your Discord credentials:
   ```
   DISCORD_TOKEN="your_discord_bot_token_here"
   DISCORD_CHANNEL_ID="1125101062454513738"
   TEST_POST_ID="your_test_post_id"  # Optional
   ```

2. Run the test using:
   ```bash
   cd components/image_generator
   python -m tests.run_tests --live
   ```

> **Note**: This test makes real API calls and consumes Midjourney credits. Use it sparingly.

### 5.4 Real API Test Results

When run with valid credentials, the live workflow test successfully:
- Sends a real generation request to Midjourney
- Processes all 4 upscale variants
- Downloads and stores all images
- Creates proper records in MongoDB with the correct variant indices (0-3)

## 6. Running All Tests

A comprehensive test runner has been created to run all tests:

```bash
# Run all tests except the live API test
python -m tests.run_tests --all

# Run specific test categories
python -m tests.run_tests --unit     # Unit tests only
python -m tests.run_tests --mock     # Mock client test
python -m tests.run_tests --integration  # Integration tests
python -m tests.run_tests --dry      # Dry-run workflow test
python -m tests.run_tests --live     # Live API test (requires credentials)

# Specify test parameters
python -m tests.run_tests --mock --post-id <your-post-id> --versions v6.0,v7.0
```

## 7. Conclusion

The implemented fixes successfully address the original issue by:
1. Ensuring consistent parameter handling with `grid_message_id`
2. Properly implementing the MidjourneyClient with support for all 4 variants
3. Establishing consistent workflow processing
4. Adding comprehensive tests to verify functionality

The system now correctly handles all 4 upscale variants for both v6.0 and v7.0 Midjourney versions, as confirmed by both mock and real API tests. 