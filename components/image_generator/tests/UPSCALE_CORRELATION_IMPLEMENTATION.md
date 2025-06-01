# Upscale Correlation Implementation

## Overview

This document describes the implementation details of the upscale correlation fix in the Silicon Sentiments image generator component. The fix addresses the issue where upscales were being downloaded from previous prompts instead of the current generation.

## Implemented Changes

### 1. Enhanced Upscale Detection Logic

The `_fallback_get_upscale_result` method in `client.py` has been enhanced to:

- Filter messages by timestamp to prevent matching older upscales
- Track processed message IDs to avoid duplicate processing
- Match prompt content between upscales and their parent grid images
- Include and track grid message ID references for proper correlation

Key improvements:
```python
# Convert to timestamp for comparison
start_timestamp = datetime.fromtimestamp(start_time).isoformat()

# Keep track of processed message IDs
processed_msg_ids = set()
self.matched_message_ids = set()

# Extract and match prompt from grid message
grid_prompt = None
if current_grid_id:
    grid_message = await self._get_message_details(current_grid_id)
    # Extract prompt for correlation checking

# Filter by timestamp
if msg_time and msg_time < start_timestamp:
    # Skip old messages

# Check prompt matching
if grid_prompt and "**" in msg.get("content", ""):
    # Extract and compare prompt text
```

### 2. Added Upscale-Grid Message Mapping

Created a mapping mechanism to track which upscaled images belong to which grid message:

```python
# Store this upscale's reference to its parent grid
if hasattr(self, 'upscale_grid_mapping') and current_grid_id:
    if not isinstance(self.upscale_grid_mapping, dict):
        self.upscale_grid_mapping = {}
    self.upscale_grid_mapping[msg.get('id')] = {
        "grid_message_id": current_grid_id,
        "variant": variant,
        "timestamp": time.time()
    }
```

### 3. Enhanced Metadata Storage

The `FileSystemStorage` class in `storage.py` has been enhanced to:

- Use consistent timestamps between grid and upscale files
- Create consolidated metadata files that link grid images to their upscales
- Include grid message ID references in upscale metadata

Key improvements:
```python
# Create consolidated metadata file
consolidated_path = os.path.join(target_dir, f"generation_{timestamp}.json")
consolidated_data = {
    "timestamp": timestamp,
    "prompt": prompt,
    "grid_message_id": metadata.get("grid_message_id", ""),
    "grid_path": grid_path,
    "upscales": []  # Populated by upscale_variant calls
}

# Update upscale metadata
enhanced_metadata = {
    **metadata,
    "timestamp": timestamp,
    "storage_path": upscale_path,
    "type": "upscale",
    "grid_message_id": metadata.get("grid_message_id", "")
}
```

### 4. Comprehensive Testing

Added new tests to verify correct correlation:

- `test_upscale_correlation.py`: Unit tests for timestamp filtering, prompt matching, message ID tracking, and metadata correlation
- `test_upscale_correlation.sh`: Script to run correlation tests in isolation
- `run_correlation_tests.sh`: Script to test the entire workflow with real or mock data

### 5. Run Script Enhancements

Modified `run_real_test.py` to:

- Add a `--mock` flag for test runs without real API calls
- Add a `--skip-upscale` option to test just grid generation
- Improve prompt correlation in the fallback upscale detection

## Testing the Fix

The fix can be tested using the following commands:

1. **Unit tests only**:
```bash
cd components/image_generator/tests
./test_upscale_correlation.sh
```

2. **Mock integration test** (no API calls):
```bash
cd components/image_generator/tests
./run_correlation_tests.sh
```

3. **Live integration test** (uses real API):
```bash
cd components/image_generator/tests
./run_correlation_tests.sh -l -p "your test prompt"
```

## Conclusion

The implementation fixes the issue by ensuring that upscales are correctly matched to their parent grid images using multiple correlation mechanisms (timestamp, prompt matching, message ID tracking). The enhanced metadata storage also ensures that the relationship between grid images and their upscales is properly maintained in both the filesystem and any downstream applications. 