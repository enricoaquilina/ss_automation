# Midjourney Testing Guide

This guide explains how to run the Midjourney integration tests, which test the complete workflow from image generation to upscaling.

## Prerequisites

1. **Discord Tokens and IDs**
   - Discord User Token - For sending commands and interactions
   - Discord Bot Token - For receiving messages and events
   - Discord Channel ID - Where Midjourney bot is active
   - Discord Guild/Server ID - The server containing the channel

2. **MongoDB Instance**
   - For storing test results and verification

## Configuration

Create a `.env` file in one of these locations:
- Root directory: `/mongodb/silicon_sentiments/.env`
- Component directory: `/mongodb/silicon_sentiments/components/image_generator/.env`
- Component src directory: `/mongodb/silicon_sentiments/components/image_generator/src/.env`

Copy this template and fill in your actual values:
```
# Discord authentication
DISCORD_TOKEN="your_user_token_here"
DISCORD_BOT_TOKEN="your_bot_token_here"
DISCORD_CHANNEL_ID="your_channel_id"
DISCORD_GUILD_ID="your_guild_id"

# MongoDB connection
MONGODB_URI="mongodb://username:password@host:port/database?authSource=admin"

# Test specific settings
FULLY_MOCKED=false
TEST_POST_ID=""
```

## Running Tests

### Run the full live test:

```bash
cd /mongodb/silicon_sentiments
source venv/bin/activate
cd components/image_generator
PYTHONPATH=/mongodb/silicon_sentiments/components/image_generator python -m pytest tests/integration/test_midjourney_live_workflow.py -v
```

### Running in mock mode (no real API calls):

Edit your `.env` file and set:
```
FULLY_MOCKED=true
```

Then run the test as shown above.

## Test Details

The Midjourney live workflow test:

1. **Image Generation**
   - Sends a real `/imagine` command to Midjourney using Discord's interactions API
   - Uses proper interaction payloads (not plaintext commands)
   - Waits for the grid image to be generated

2. **Image Upscaling**
   - Uses the upscale_all_variants method to upscale all 4 variants
   - Saves images to both filesystem and MongoDB

3. **Verification**
   - Verifies that all images were correctly stored
   - Checks relationships between grid and variations

## Troubleshooting

1. **Invalid Token**: If you see authentication errors, check your Discord tokens
2. **Connection Issues**: Ensure you have network access to Discord
3. **Rate Limiting**: Don't run too many tests in succession to avoid Discord rate limits
4. **Import Errors**: Make sure PYTHONPATH is set correctly

## Known Issues

- Plain text commands are not supported and will fail
- Always use the proper Discord Interactions API approach
