#!/usr/bin/env python3
"""
Integration tests for Midjourney client.

These tests verify the integration between our code and the Midjourney API.
Note that these tests require valid Discord credentials and will make actual API calls.
"""

import os
import sys
import asyncio
import logging
import pytest
import pytest_asyncio
import dotenv
from time import sleep

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from src import MidjourneyClient
    from src.utils import ModerationError
except ImportError:
    print("Failed to import MidjourneyClient. Check your import paths.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load environment variables
dotenv.load_dotenv()

# Get required environment variables
USER_TOKEN = os.environ.get("DISCORD_USER_TOKEN") or os.environ.get("DISCORD_TOKEN")
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN") or USER_TOKEN
CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")

# Skip tests if environment variables are not set
pytestmark = pytest.mark.skipif(
    not all([USER_TOKEN, CHANNEL_ID, GUILD_ID]),
    reason="Missing required environment variables for integration tests"
)

@pytest_asyncio.fixture
async def client():
    """Create and initialize MidjourneyClient for tests"""
    client = MidjourneyClient(
        user_token=USER_TOKEN,
        bot_token=BOT_TOKEN,
        channel_id=CHANNEL_ID,
        guild_id=GUILD_ID
    )
    await client.initialize()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_initialization(client):
    """Test that the client initializes successfully"""
    # This test relies on the client fixture which calls initialize()
    assert client is not None
    
@pytest.mark.asyncio
async def test_generate_image_with_v7(client):
    """Test generating an image with v7.0 model"""
    # Generate a test prompt for v7.0 that is less likely to be filtered
    prompt = "test --v 7.0"
    
    # Generate image
    result = await client.generate_image(prompt)
    
    # Check result - skip test if moderation occurred instead of failing
    if not result.success and "moderation" in result.error.lower():
        pytest.skip(f"Test skipped due to moderation: {result.error}")
    
    # Continue with normal assertions if not moderated
    assert result.success, f"Image generation failed: {result.error}"
    assert result.grid_message_id is not None
    assert result.image_url is not None and result.image_url.startswith("https://")

@pytest.mark.asyncio
async def test_generate_image_with_niji(client):
    """Test generating an image with niji model"""
    # Generate a test prompt for niji that is less likely to be filtered
    prompt = "test --niji 6"
    
    # Generate image
    result = await client.generate_image(prompt)
    
    # Check result - skip test if moderation occurred instead of failing
    if not result.success and "moderation" in result.error.lower():
        pytest.skip(f"Test skipped due to moderation: {result.error}")
    
    # Continue with normal assertions if not moderated
    assert result.success, f"Image generation failed: {result.error}"
    assert result.grid_message_id is not None
    assert result.image_url is not None and result.image_url.startswith("https://")

@pytest.mark.asyncio
async def test_upscale_variants(client):
    """Test upscaling variants from a grid"""
    # First generate an image with a simple, safe prompt
    prompt = "test --v 6.0"
    generation = await client.generate_image(prompt)
    
    # Skip test if moderation occurred instead of failing
    if not generation.success and "moderation" in generation.error.lower():
        pytest.skip(f"Test skipped due to moderation: {generation.error}")
    
    # Check that generation was successful
    assert generation.success, f"Image generation failed: {generation.error}"
    
    # Upscale all variants
    upscales = await client.upscale_all_variants(generation.grid_message_id)
    
    # Check that at least one upscale was successful
    assert any(result.success for result in upscales), "No upscales were successful"
    
    # Check details of successful upscales
    for result in upscales:
        if result.success:
            assert 1 <= result.variant <= 4, f"Unexpected variant number: {result.variant}"
            assert result.image_url is not None and result.image_url.startswith("https://")
        else:
            print(f"Upscale variant {result.variant} failed: {result.error}")

@pytest.mark.asyncio
async def test_content_moderation_handling(client):
    """
    Test handling of content moderation
    
    This test checks that the client properly handles moderation cases by:
    1. Attempting to generate an image with potentially moderated content
    2. Verifying that either a successful result is returned (if the prompt passes moderation)
       or a proper error is raised/returned (if the prompt is moderated)
    """
    # Use a prompt that might trigger content moderation, but is on the border
    # This is deliberate - it should either pass moderation or fail with a specific error
    prompt = "beautiful woman in a swimming pool"
    
    try:
        result = await client.generate_image(prompt)
        
        # If generation was successful, verify the result
        if result.success:
            # Success case - the prompt passed moderation
            assert result.grid_message_id is not None
            assert result.image_url is not None and result.image_url.startswith("https://")
            logging.info("Moderation test: Prompt passed moderation checks")
        else:
            # Generation failed but not with an exception - check for moderation message
            assert "moderation" in result.error.lower() or "content filter" in result.error.lower(), \
                f"Expected moderation error but got: {result.error}"
            logging.info(f"Moderation test: Prompt was moderated with error: {result.error}")
            
    except ModerationError as e:
        # Expected exception if content is moderated - this is a successful test case
        logging.info(f"Moderation test: Caught expected ModerationError: {e}")
        assert True
    except Exception as e:
        # Any other exception is unexpected and should fail the test
        logging.error(f"Moderation test: Unexpected error: {e}")
        assert False, f"Unexpected error during moderation test: {e}"

if __name__ == '__main__':
    pytest.main(["-xvs", __file__]) 