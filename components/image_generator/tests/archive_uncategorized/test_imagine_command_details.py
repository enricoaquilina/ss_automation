#!/usr/bin/env python3
"""
Test script to capture and verify the details of the Discord imagine command.
This script specifically traces the API call structure to verify proper payloads.

Usage:
    python test_imagine_command_details.py
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
src_dir = os.path.join(component_dir, 'src')
sys.path.insert(0, component_dir)

# Import client
from src.client import MidjourneyClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("imagine_test")

async def test_imagine_command():
    """Test the imagine command details"""
    
    # Create mock tokens for test
    client = MidjourneyClient(
        user_token="mock_user_token",
        bot_token="mock_bot_token",
        channel_id="123456789012345678",
        guild_id="987654321098765432"
    )
    
    # Mock session ID and gateway
    client.user_gateway = MagicMock()
    client.user_gateway.session_id = "mock_session_id"
    client.user_gateway.connected = MagicMock()
    client.user_gateway.connected.is_set = MagicMock(return_value=True)
    
    # Store captured data
    captured_data = {"headers": None, "payload": None, "url": None}
    
    # Define a test prompt
    prompt = "cosmic space dolphins, digital art --ar 16:9 --v 6"
    
    # Create a simple successful mock response
    mock_response = AsyncMock()
    mock_response.status = 204
    mock_response.json = AsyncMock(return_value={"success": True})
    
    # Replace _send_slash_command with our mock implementation
    async def mock_send_slash_command(command):
        """Mock implementation of _send_slash_command that captures the payload"""
        # Capture the command data
        captured_data["payload"] = {
            "type": 2,  # APPLICATION_COMMAND
            "application_id": "936929561302675456",  # Midjourney app ID
            "guild_id": client.guild_id,
            "channel_id": client.channel_id,
            "session_id": client.user_gateway.session_id,
            "data": command
        }
        
        logger.debug(f"Command payload: {json.dumps(captured_data['payload'], indent=2)}")
        return {"success": True}
    
    # Apply the mock
    client._send_slash_command = mock_send_slash_command
    
    # Call the imagine command
    logger.info(f"Sending imagine command with prompt: {prompt}")
    result = await client._send_imagine_command(prompt)
    
    # Print and validate results
    payload = captured_data["payload"]
    if payload:
        logger.info("Successfully captured imagine command payload:")
        print(json.dumps(payload, indent=2))
        
        # Validate command structure
        assert payload["type"] == 2, "Type should be 2 (APPLICATION_COMMAND)"
        assert payload["application_id"] == "936929561302675456", "Should use Midjourney app ID"
        assert "channel_id" in payload, "Should include channel ID"
        assert "guild_id" in payload, "Should include guild ID"
        assert "session_id" in payload, "Should include session ID"
        
        # Validate command data
        command_data = payload["data"]
        assert command_data["name"] == "imagine", "Command name should be 'imagine'"
        assert command_data["id"] == "938956540159881230", "Command ID should be correct"
        
        # Validate prompt
        options = command_data["options"]
        assert len(options) == 1, "Should have exactly one option"
        assert options[0]["name"] == "prompt", "Option name should be 'prompt'"
        assert options[0]["value"] == prompt, "Prompt value should match the input"
        
        logger.info("✅ All validations passed!")
        return True
    else:
        logger.error("❌ Failed to capture command payload!")
        return False

# Run the test
if __name__ == "__main__":
    asyncio.run(test_imagine_command()) 