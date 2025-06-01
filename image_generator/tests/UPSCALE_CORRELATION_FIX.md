# Midjourney Client Upscale Correlation Fix

## Problem Summary

The image generator component had an issue where upscaled images were sometimes incorrectly matched to the wrong prompt/grid image. Specifically, when generating multiple images in sequence, upscales from a previous prompt could be mistakenly downloaded and saved as if they belonged to the current prompt.

## Root Causes

1. **Weak Correlation Tracking**: The original implementation didn't properly track which upscale belonged to which grid image.
2. **Missing Timestamp Filtering**: Upscale detection didn't filter out older messages, allowing it to match stale upscales.
3. **Insufficient Prompt Matching**: The code didn't verify that upscale messages contained the same prompt as the original grid.
4. **Missing Grid Message References**: The metadata stored with upscales didn't always include references to their parent grid images.

## Implemented Solutions

### 1. Improved Upscale Detection Logic

Updated the `_fallback_get_upscale_result` method in `client.py` to:

- Use timestamps to filter out older messages
- Track processed message IDs to avoid duplicates
- Match prompt text between upscales and grid images
- Include reference to the parent grid message ID

```python
async def _fallback_get_upscale_result(self, variant, start_time=None):
    # Track when the upscale was initiated
    # Filter messages by timestamp
    # Match by prompt content
    # Keep track of message IDs to prevent duplicates
    # Include grid message ID in metadata for correlation
```

### 2. Enhanced Metadata Storage

Updated the `storage.py` file to:

- Store consistent timestamps across grid and upscale files
- Create standardized metadata files with proper correlation between grid images and upscales
- Store prompt text separately in a plain text file for easy reference
- Include grid message ID in all upscale metadata

```python
async def save_grid(self, data: bytes, metadata: Dict[str, Any]):
    # Create timestamp-based directories
    # Save grid metadata
    # Save prompt text file
    # Initialize upscale tracking
```

```python
async def save_upscale(self, data: bytes, metadata: Dict[str, Any]):
    # Use consistent timestamp from grid
    # Include grid_message_id reference
    # Update consolidated upscales file
    # Maintain correlation between upscales and grid
```

### 3. Added Correlation Verification

Created new tests to verify that correlation works correctly:

- `test_upscale_correlation.py`: Tests timestamp tracking, prompt matching, and message ID correlation
- `test_upscale_correlation.sh`: Script to run tests and verify the entire workflow

## Testing Strategy

1. **Unit Tests**: Testing individual correlation mechanisms (timestamp, prompt matching, ID tracking)
2. **Integration Tests**: Testing the entire workflow of correlation between grid and upscales
3. **Mock Tests**: Testing with simulated data to verify behavior in controlled scenarios
4. **Real Tests**: Testing with actual API calls to verify end-to-end behavior

## Results

The improvements successfully address the issue:

- Upscaled images now correctly match their parent grid images
- All metadata now includes proper correlation information
- Timestamp filtering prevents matching stale upscales
- Prompt matching ensures semantic correlation between grid and upscales
- Message ID tracking prevents processing duplicate messages

## Future Work

1. **Database Correlation**: Enhance database storage to maintain parent-child relationships
2. **Additional Validation**: Add more validation steps during image saving
3. **Retry Mechanisms**: Improve error handling and retry logic for failed upscales
4. **Logging Improvements**: Add more detailed logging for correlation debugging

## Test Verification

Run the integration tests to verify the fix:

```bash
cd components/image_generator/tests
./test_upscale_correlation.sh
```

Run the real test with the improved client:

```bash
cd components/image_generator
python run_real_test.py --prompt "Your test prompt" --output-dir ./test_output
``` 