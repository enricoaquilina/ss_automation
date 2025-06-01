# Midjourney Integration Tests

This directory contains tests for the Silicon Sentiments image generation component, which integrates with Midjourney via Discord.

## Setup

Before running the tests, you need to set up your environment:

1. Create a `.env` file in the `components/image_generator` directory with your Discord credentials:

```
# Discord credentials
DISCORD_CHANNEL_ID=your_channel_id
DISCORD_GUILD_ID=your_guild_id
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_USER_TOKEN=your_user_token

# MongoDB connection (only needed if using GridFS storage)
MONGODB_URI=mongodb://username:password@hostname:port/database?authSource=admin

# Logging settings
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Test settings (only needed for tests)
TEST_PROMPT="beautiful cosmic space dolphin, digital art style"
TEST_POST_ID=your_test_post_id
```

2. Ensure you have valid Discord credentials:
   - `DISCORD_USER_TOKEN`: Your Discord user token (required)
   - `DISCORD_CHANNEL_ID`: The ID of the Discord channel where you'll send Midjourney commands
   - `DISCORD_GUILD_ID`: The ID of the Discord server (guild)

## Test Scripts

### Discord Authentication Test

To verify your Discord credentials are valid:

```bash
cd tests
python -m integration.test_discord_auth
```

### Running All Tests

There are several scripts available to run tests:

1. **Run all tests in mock mode** (no Midjourney credits used):
   ```bash
   cd components/image_generator
   ./tests/run_all_tests.sh 1
   ```

2. **Run Discord integration tests** (validates token but doesn't use Midjourney credits):
   ```bash
   cd components/image_generator
   ./run_discord_tests.sh
   ```

3. **Run all live tests** (uses Midjourney credits):
   ```bash
   cd components/image_generator
   ./run_live_tests.sh
   ```

4. **Run a single test with a specific prompt** (uses Midjourney credits):
   ```bash
   cd components/image_generator
   ./run_single_test.sh "your prompt here"
   ```
   If you don't provide a prompt, the script will offer a selection of safe prompts to choose from.

## Test Output

Test results and outputs are stored in the `test_output` directory, organized in timestamped folders (e.g., `20250510_081214`).

## Troubleshooting

### Authentication Failures

If you encounter authentication errors:

1. Check that your Discord token is valid and hasn't expired
2. Verify the channel and guild IDs are correct
3. Run the authentication test first to isolate token issues
4. Check if Discord is experiencing any API issues

### Moderation Issues

Midjourney has content moderation that may block certain prompts:

1. Use safe, family-friendly prompts like "beautiful cosmic space dolphin, digital art style"
2. Avoid potentially controversial or adult content
3. If a prompt is moderated, the test will be skipped instead of failing

### Missing Imports

If you see import errors:

1. Make sure you're running the tests from the correct directory
2. Check that the PYTHONPATH is set correctly
3. Try running the tests with the provided scripts instead of directly

## Discord WebSocket Errors

Common WebSocket errors:

- **Error 4004**: Authentication failed (invalid token)
- **Error 4008**: Rate limited (too many requests)
- **Error 4012**: Invalid API version
- **Error 4014**: Disallowed intents 