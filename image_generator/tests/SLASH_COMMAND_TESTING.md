# Testing Discord Slash Commands with Real API Interactions

This guide explains how to test Midjourney slash commands using the Discord Interactions API.

## Why Proper Slash Commands Matter

Discord has largely deprecated traditional "plaintext" commands (like typing `/imagine` in chat). Instead, applications should use the proper Interactions API to send slash commands. 

According to the UseAPI documentation:

1. Using the proper Interactions API approach is more reliable
2. Plaintext commands may be rejected by Discord
3. The Interactions API provides better feedback about command execution

## Prerequisites

1. **Discord Tokens and IDs**
   - Discord User Token - For sending slash commands via the interactions API
   - Discord Bot Token (optional) - For receiving messages and WebSocket events
   - Discord Channel ID - Where Midjourney bot is active
   - Discord Guild/Server ID (optional) - The server containing the channel

2. **Environment Setup**
   - Python 3.7+ with required packages
   - Valid Discord credentials

## Setting Up Your Environment

Create a `.env` file in one of these locations:
- Root directory: `/mongodb/silicon_sentiments/.env`
- Component directory: `/mongodb/silicon_sentiments/components/image_generator/.env`

With the following content:
```
DISCORD_TOKEN="your_user_token_here"
DISCORD_BOT_TOKEN="your_bot_token_here"  # Optional, can be the same as user token
DISCORD_CHANNEL_ID="your_channel_id"
DISCORD_GUILD_ID="your_guild_id"  # Optional but recommended
```

## Running the Tests

We've created a specialized test script and a runner script to test slash commands with real API interactions.

### Using the Runner Script

```bash
cd /mongodb/silicon_sentiments/components/image_generator
bash tests/integration/run_slash_command_test.sh
```

The script will:
1. Ask for Discord credentials if no `.env` file is found
2. Prompt you to choose which test to run:
   - Token validation only (no Midjourney credits used)
   - Slash command sending test (minimal Midjourney credits used)
   - Full generation and tracking test (uses Midjourney credits)

### Running Tests Manually

You can also run individual tests directly:

```bash
# Set the PYTHONPATH
cd /mongodb/silicon_sentiments/components/image_generator
export PYTHONPATH=$PWD

# Run specific tests
python -m pytest tests/integration/test_slash_commands.py::TestSlashCommands::test_validate_token -v
python -m pytest tests/integration/test_slash_commands.py::TestSlashCommands::test_send_imagine_command -v

# To run the full generation test (uses Midjourney credits)
export RUN_FULL_API_TEST=true
python -m pytest tests/integration/test_slash_commands.py::TestSlashCommands::test_generate_and_track -v
```

## Understanding the Tests

Our test script (`test_slash_commands.py`) implements several tests:

1. **Token Validation**: Tests that your Discord token works for authentication.

2. **Slash Command Sending**: Tests the direct sending of an `/imagine` command via the Discord Interactions API. This verifies our client is using the correct API approach, not plaintext commands.

3. **Generation and Tracking**: A comprehensive test that:
   - Sends an `/imagine` command
   - Tracks message flow following the UseAPI recommendations
   - Detects which of the 7 possible cases occurs (happy path, moderation, etc.)

## Interpreting Test Results

After running the tests, you'll see logging output explaining what happened:

### For Slash Command Sending

- Success: The command was successfully sent via the Interactions API
- Failure: The command was rejected by Discord, possibly due to invalid token or rate limiting

### For Generation and Tracking

The test will report which of these outcomes occurred:

1. **Happy path**: Generation completed, grid image produced with upscale buttons
2. **Pre-moderation**: No message appeared in the channel (prompt likely violated content policy)
3. **Post-moderation**: Generation started but was stopped mid-way
4. **Ephemeral moderation**: Generation started but message was deleted or hidden
5. **Invalid request**: Request was rejected or malformed
6. **Job queued**: Generation was queued (too many concurrent jobs)
7. **Queue full**: All slots are full, job couldn't be queued

## Troubleshooting

### Authentication Failures

- Verify your Discord token is correct and still valid
- Ensure the channel ID is correct and your account has access to it
- Check if your token is properly formatted (no extra quotes or spaces)

### Rate Limiting

- Discord limits how often you can make API calls
- If you get rate limited, wait a few minutes before trying again
- For production use, implement proper rate limiting and backoff

### Test Failures

If the slash command test fails but the token validation passes:
- Discord might be enforcing the interactions API more strictly
- Your account may have limited permissions
- The `MidjourneyClient` implementation might need updating 