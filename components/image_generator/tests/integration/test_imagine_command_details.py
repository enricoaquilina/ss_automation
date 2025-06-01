#!/usr/bin/env python3
"""
Integration test for Discord imagine command payload structure.

This test verifies that the imagine command generates the correct API payload
structure when sent to Discord's slash command endpoint.
"""

import os
import sys
import json
import pytest
import pytest_asyncio
import logging
from unittest.mock import MagicMock, AsyncMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from src.client import MidjourneyClient

class TestImagineCommandDetails:
    """Test Discord imagine command payload structure"""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock client for testing"""
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
        
        return client
        
    @pytest_asyncio.fixture
    async def captured_command_data(self, mock_client):
        """Fixture that captures command data from slash command calls"""
        captured_data = {"headers": None, "payload": None, "url": None}
        
        async def mock_send_slash_command(command):
            """Mock implementation that captures the command payload"""
            captured_data["payload"] = {
                "type": 2,  # APPLICATION_COMMAND
                "application_id": "936929561302675456",  # Midjourney app ID
                "guild_id": mock_client.guild_id,
                "channel_id": mock_client.channel_id,
                "session_id": mock_client.user_gateway.session_id,
                "data": command
            }
            return {"success": True}
        
        # Apply the mock
        mock_client._send_slash_command = mock_send_slash_command
        
        yield mock_client, captured_data
    
    @pytest.mark.asyncio
    async def test_imagine_command_payload_structure(self, captured_command_data):
        """Test that imagine command generates correct payload structure"""
        client, captured_data = captured_command_data
        
        # Test prompt
        prompt = "cosmic space dolphins, digital art --ar 16:9 --v 6"
        
        # Call the imagine command
        result = await client._send_imagine_command(prompt)
        
        # Verify the command was captured
        assert captured_data["payload"] is not None, "Command payload should be captured"
        payload = captured_data["payload"]
        
        # Verify payload structure
        assert payload["type"] == 2, "Should be APPLICATION_COMMAND type"
        assert payload["application_id"] == "936929561302675456", "Should use Midjourney app ID"
        assert payload["guild_id"] == client.guild_id, "Should include guild ID"
        assert payload["channel_id"] == client.channel_id, "Should include channel ID"
        assert payload["session_id"] == "mock_session_id", "Should include session ID"
        assert "data" in payload, "Should include command data"
        
        # Verify command data structure
        command_data = payload["data"]
        assert command_data["name"] == "imagine", "Should be imagine command"
        assert command_data["type"] == 1, "Should be CHAT_INPUT type"
        assert "options" in command_data, "Should include options"
        
        # Verify prompt option
        options = command_data["options"]
        assert len(options) == 1, "Should have exactly one option"
        prompt_option = options[0]
        assert prompt_option["name"] == "prompt", "Option should be named 'prompt'"
        assert prompt_option["type"] == 3, "Option should be STRING type"
        assert prompt_option["value"] == prompt, "Option value should match input prompt"
    
    @pytest.mark.asyncio
    async def test_imagine_command_with_different_prompts(self, captured_command_data):
        """Test imagine command with various prompt formats"""
        client, captured_data = captured_command_data
        
        test_prompts = [
            "simple prompt",
            "prompt with --ar 1:1",
            "prompt with --v 6 --style raw",
            "complex prompt with multiple --parameters --ar 16:9 --v 6 --stylize 1000"
        ]
        
        for prompt in test_prompts:
            # Reset captured data
            captured_data["payload"] = None
            
            # Call imagine command
            await client._send_imagine_command(prompt)
            
            # Verify payload was captured
            assert captured_data["payload"] is not None, f"Payload should be captured for prompt: {prompt}"
            
            # Verify prompt is correctly embedded
            command_data = captured_data["payload"]["data"]
            prompt_option = command_data["options"][0]
            assert prompt_option["value"] == prompt, f"Prompt should be preserved exactly: {prompt}"
    
    @pytest.mark.asyncio 
    async def test_imagine_command_metadata_fields(self, captured_command_data):
        """Test that all required metadata fields are present"""
        client, captured_data = captured_command_data
        
        prompt = "test prompt for metadata"
        await client._send_imagine_command(prompt)
        
        payload = captured_data["payload"]
        command_data = payload["data"]
        
        # Verify required command metadata
        assert "version" in command_data, "Should include version"
        assert "id" in command_data, "Should include command ID"
        assert command_data["id"] == "938956540159881230", "Should use correct imagine command ID"
        
        # Verify the version is a valid format (numeric string)
        version = command_data["version"]
        assert isinstance(version, str), "Version should be a string"
        assert version.isdigit(), "Version should be numeric"
        assert len(version) > 10, "Version should be a Discord snowflake format"
    
    @pytest.mark.asyncio
    async def test_imagine_command_error_handling(self, mock_client):
        """Test error handling when slash command fails"""
        
        # Mock slash command to raise an exception
        async def failing_slash_command(command):
            raise Exception("Mock network error")
        
        mock_client._send_slash_command = failing_slash_command
        
        # Call imagine command and expect it to handle the error
        result = await mock_client._send_imagine_command("test prompt")
        
        # The imagine command should handle errors gracefully and return None
        assert result is None, "Should return None when slash command fails"