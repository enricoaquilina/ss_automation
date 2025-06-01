# Troubleshooting Guide

This guide covers common issues you might encounter when using the Discord-Midjourney image generator component and provides solutions to resolve them.

## Connection Issues

### WebSocket Disconnections

**Symptoms:**
- Frequent "WebSocket closed" messages in logs
- Operations failing halfway through
- Timeouts during WebSocket operations

**Solutions:**
1. Check your internet connection stability
2. Ensure your Discord tokens are valid and have not expired
3. Verify the bot has proper permissions in the Discord server
4. Try reconnecting the client:
   ```python
   # Reinitialize the client
   await client.close()
   await client.initialize()
   ```

### Authentication Failures

**Symptoms:**
- "Failed to connect with user token" error
- "Session ID not available" errors
- "401 Unauthorized" HTTP responses

**Solutions:**
1. Regenerate your Discord user token
2. Verify the bot token is correctly copied from the Discord Developer Portal
3. Check that your bot is still in the server
4. Ensure the server and channel IDs are correct
5. Check your `.env` file locations

## Image Generation Issues

### Generation Not Starting

**Symptoms:**
- No response after sending /imagine command
- Timeout waiting for grid message
- Connection to Discord seems fine but nothing happens

**Solutions:**
1. Verify Midjourney bot is in the channel and functioning
2. Check your Midjourney subscription status
3. Ensure the channel is not read-only
4. Try a very simple prompt without any parameters

### Missing Upscale Results

**Symptoms:**
- Only some variants are upscaled successfully
- Upscale operation times out
- Same image URL for different variants

**Solutions:**
1. Increase the timeout for upscale operations:
   ```python
   # In the generate.py script
   # Add a longer timeout parameter to the upscale call
   await client.upscale_all_variants(generation.grid_message_id, timeout=120)
   ```
2. Add a longer delay between upscales
3. Check if the Midjourney bot is rate limiting your requests

## Storage Issues

### File System Storage Problems

**Symptoms:**
- "Permission denied" errors when saving files
- Files saved with incorrect names
- Missing metadata files

**Solutions:**
1. Check if the output directory exists and has write permissions
2. Make sure you're not using reserved characters in your prompts
3. Verify that you have sufficient disk space

### GridFS Storage Issues

**Symptoms:**
- MongoDB connection errors
- "Failed to save to GridFS" error messages
- Missing or corrupt files in MongoDB

**Solutions:**
1. Check your MongoDB connection string in the `.env` file
2. Verify that MongoDB is running and accessible
3. Make sure the database and collections exist with proper permissions
4. Check that pymongo is installed:
   ```bash
   pip install pymongo
   ```

## Discord API Rate Limits

**Symptoms:**
- HTTP 429 "Too Many Requests" errors
- Operations failing with "rate limit exceeded" messages
- Increasing delays between operations

**Solutions:**
1. Add delays between operations:
   ```python
   # Add a 30-second delay
   import asyncio
   await asyncio.sleep(30)
   ```
2. Reduce the number of concurrent operations
3. Spread operations across multiple Discord channels
4. Upgrade to a higher tier Discord account

## Model Version Issues

**Symptoms:**
- Wrong model version used in generation
- Files saved with incorrect model names
- Unexpected image styles

**Solutions:**
1. Explicitly specify the model version in your prompt:
   ```
   --v 7.0   # For Midjourney v7.0
   --niji 6  # For Niji 6
   ```
2. Check the client code for default model versions
3. Verify that file prefixes match the model version used

## Environment Configuration Issues

**Symptoms:**
- "Missing required environment variables" errors
- Tokens not being loaded properly
- Different behavior on different systems

**Solutions:**
1. Check all possible `.env` file locations:
   - `./.env` (in the root directory)
   - `./components/image_generator/.env`
   - `./components/image_generator/src/.env`
2. Make sure all environment variables are correctly defined:
   ```
   DISCORD_CHANNEL_ID=your_channel_id
   DISCORD_GUILD_ID=your_guild_id
   DISCORD_BOT_TOKEN=your_bot_token
   DISCORD_USER_TOKEN=your_user_token
   MONGODB_URI=your_mongodb_uri  # Only if using GridFS
   ```
3. Try specifying the env file directly:
   ```bash
   python generate.py --prompt "test" --env-file /path/to/your/.env
   ```

## Additional Resources

If you're still experiencing issues:

1. Check the [Discord API Documentation](https://discord.com/developers/docs/intro)
2. Review the [Midjourney Discord server](https://discord.gg/midjourney) for announcements about changes or issues
3. Update to the latest version of the integration code
4. Try a simplified workflow to isolate where the issue is occurring 