#!/usr/bin/env python3
"""
Test script to verify that the generate_image method correctly calls _send_imagine_command.
This tests the full integration between the high-level API and the slash command implementation.

Usage:
    python test_imagine_from_generate_image.py
"""

import os
import sys
import json
import asyncio
import logging
from unittest.mock import patch, AsyncMock, MagicMock

# Add parent directory to sys.path for importing from component package
current_dir = os.path.dirname(os.path.abspath(__file__))
component_dir = os.path.dirname(current_dir)
sys.path.insert(0, component_dir)

# Import client and models
from src.client import MidjourneyClient
from src.models import GenerationResult

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("generate_test")

async def test_generate_image_method():
    """Test that generate_image properly uses _send_imagine_command"""
    
    # Create client with mock credentials
    client = MidjourneyClient(
        user_token="mock_user_token",
        bot_token="mock_bot_token",
        channel_id="123456789012345678",
        guild_id="987654321098765432"
    )
    
    # Mock the necessary components
    client.user_gateway = MagicMock()
    client.user_gateway.session_id = "mock_session_id"
    client.user_gateway.connected = MagicMock()
    client.user_gateway.connected.is_set = MagicMock(return_value=True)
    
    client.bot_gateway = MagicMock()
    client.bot_gateway.connected = MagicMock()
    client.bot_gateway.connected.is_set = MagicMock(return_value=True)
    
    # Define test prompt
    prompt = "cosmic space dolphins, digital art --ar 16:9 --v 6"
    
    # Track if _send_imagine_command was called with the right prompt
    imagine_called = False
    actual_prompt = None
    
    # Mock the _get_recent_messages method
    client._get_recent_messages = AsyncMock(return_value=[{"id": "mock_message_id_123"}])
    
    # Mock the _send_imagine_command method
    async def mock_send_imagine(prompt_value):
        nonlocal imagine_called, actual_prompt
        imagine_called = True
        actual_prompt = prompt_value
        logger.info(f"✅ _send_imagine_command called with prompt: {prompt_value}")
        return {"id": "mock_response_id"}
    
    client._send_imagine_command = mock_send_imagine
    
    # Create a mock for generation_future
    client.generation_future = asyncio.Future()
    
    # Create a mock result for the generation
    mock_result = {
        "message_id": "mock_result_message_id",
        "image_url": "https://example.com/image.png"
    }
    
    # Set up an auto-completion of the future after a short delay
    async def complete_future():
        await asyncio.sleep(0.1)
        if not client.generation_future.done():
            client.generation_future.set_result(mock_result)
    
    # Start the auto-completion task
    completion_task = asyncio.create_task(complete_future())
    
    # Call the generate_image method
    logger.info(f"Calling generate_image with prompt: {prompt}")
    
    # Execute generate_image
    result = await client.generate_image(prompt)
    
    # Wait for the completion task to finish
    await completion_task
    
    # Check the result
    assert imagine_called, "The _send_imagine_command method was not called!"
    assert actual_prompt == prompt, f"Wrong prompt was passed: {actual_prompt}"
    assert result.success, "Generation result should indicate success"
    assert result.grid_message_id == mock_result["message_id"], "Message ID should match mock result"
    assert result.image_url == mock_result["image_url"], "Image URL should match mock result"
    
    logger.info("✅ All tests passed! generate_image correctly calls _send_imagine_command")
    return True

# Run the test
if __name__ == "__main__":
    asyncio.run(test_generate_image_method()) 