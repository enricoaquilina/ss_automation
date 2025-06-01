# Silicon Sentiments Image Generator

This component integrates with Midjourney via Discord to generate AI images for the Silicon Sentiments project.

## Setup

1. **Create Environment File**

   Create a `.env` file in the `components/image_generator` directory with your Discord credentials:

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

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Validate Discord Credentials

Before using the component, verify your Discord credentials:

```bash
cd components/image_generator
./run_discord_tests.sh
```

This will validate your token without consuming Midjourney credits.

### Generate a Single Image

To generate a single image with a specific prompt:

```bash
cd components/image_generator
./run_single_test.sh "your prompt here"
```

If you don't provide a prompt, the script will offer a selection of safe prompts to choose from.

### Run All Tests

For comprehensive testing:

```bash
cd components/image_generator
./run_live_tests.sh
```

This will run all tests, including live Midjourney API calls which consume credits.

## Test Scripts

| Script | Description |
|--------|-------------|
| `run_discord_tests.sh` | Validates Discord credentials and runs basic Discord integration tests |
| `run_single_test.sh` | Generates a single image with the specified prompt |
| `run_live_tests.sh` | Runs all tests with live Midjourney API calls |
| `tests/run_all_tests.sh` | Comprehensive test runner with multiple options |

## Directory Structure

- `src/`: Source code for the component
- `tests/`: Test files and utilities
  - `integration/`: Integration tests
  - `unit/`: Unit tests
  - `test_output/`: Generated test output (images, logs)
- `docs/`: Documentation

## Troubleshooting

### Authentication Issues

If you encounter "Discord token validation failed" errors:

1. Ensure your Discord user token is valid and up-to-date
2. Check that your channel and guild IDs are correct
3. Try logging out and back into Discord to refresh your token

### Discord WebSocket Error 4004

This error indicates an authentication failure:

1. Your token may have expired
2. The token format might be incorrect
3. The Discord API may have changed

### Content Moderation

Midjourney has content moderation that may block certain prompts:

1. Use safe, family-friendly prompts
2. Avoid potentially controversial content
3. If a prompt is moderated, try one of the pre-defined safe prompts

## Development Notes

- The component uses Discord websockets for real-time communication
- Upscale correlation ensures that upscaled images match their parent grid
- Grid messages and upscale variants are tracked to maintain proper relationships
- Tests can run in mock mode (no API calls) or live mode (uses Midjourney credits)

See [tests/README.md](tests/README.md) for more detailed testing information. 