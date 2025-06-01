#!/usr/bin/env python3
"""
Simple Coroutine Test for MidjourneyClient

This script demonstrates correct async usage and verifies session ID handling.
"""

import os
import sys
import asyncio
import logging
import dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("coroutine_test")

# Add src directory to path
current_dir = Path(__file__).parent.absolute()
src_dir = current_dir.parent / 'src'
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(current_dir))  # Add tests directory to path

# Import client and mock client
try:
    from src.client import MidjourneyClient
    from mock_midjourney_client import MockMidjourneyClient
except ImportError:
    try:
        from client import MidjourneyClient
        from mock_midjourney_client import MockMidjourneyClient
    except ImportError:
        logger.error("Failed to import MidjourneyClient. Check path configuration.")
        sys.exit(1)

async def test_client_initialization():
    """Test client initialization and proper session ID setup"""
    # Load environment variables
    dotenv_path = Path(current_dir.parent / '.env')
    if dotenv_path.exists():
        dotenv.load_dotenv(dotenv_path)
        logger.info(f"Loaded environment from {dotenv_path}")
    
    # Check if we're in mocked mode
    mocked = os.environ.get('FULLY_MOCKED', 'false').lower() == 'true'
    if mocked:
        logger.info("Running in MOCKED mode. Using placeholder credentials.")
        discord_token = "mock_token"
        bot_token = "mock_bot_token"
        channel_id = "123456789"
        guild_id = "987654321"
    else:
        # Get credentials from environment
        discord_token = os.environ.get('DISCORD_TOKEN')
        bot_token = os.environ.get('DISCORD_BOT_TOKEN', discord_token)
        channel_id = os.environ.get('DISCORD_CHANNEL_ID')
        guild_id = os.environ.get('DISCORD_GUILD_ID', '')
        
        if not discord_token or not channel_id:
            logger.error("Missing required environment variables")
            logger.error("Please set DISCORD_TOKEN and DISCORD_CHANNEL_ID")
            return False
    
    # Create client - use mock client if in mocked mode
    logger.info("Creating client...")
    if mocked:
        client = MockMidjourneyClient(
            user_token=discord_token,
            bot_token=bot_token, 
            channel_id=channel_id,
            guild_id=guild_id
        )
        logger.info("Using MockMidjourneyClient")
    else:
        client = MidjourneyClient(
            user_token=discord_token,
            bot_token=bot_token,
            channel_id=channel_id,
            guild_id=guild_id
        )
        logger.info("Using real MidjourneyClient")
    
    # Initialize client
    logger.info("Initializing client...")
    success = await client.initialize()
    
    if success:
        logger.info("✅ Client initialized successfully")
        
        # Verify session ID
        if hasattr(client.user_gateway, 'session_id') and client.user_gateway.session_id:
            logger.info(f"✅ Session ID obtained: {client.user_gateway.session_id}")
        else:
            logger.error("❌ No session ID was set")
            success = False
    else:
        logger.error("❌ Client initialization failed")
    
    # Properly close client
    logger.info("Closing client...")
    await client.close()
    logger.info("Client closed")
    
    return success

async def main():
    """Run all tests"""
    success = await test_client_initialization()
    
    if success:
        logger.info("✅ All tests passed successfully")
        return 0
    else:
        logger.error("❌ Tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 