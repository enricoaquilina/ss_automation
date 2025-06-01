#!/usr/bin/env python3
"""
Integration tests for Discord slash commands

This script tests the functionality for sending and processing 
Discord slash commands with the Midjourney client.
"""

import os
import sys
import json
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

# Import from the src directory
from src.client import MidjourneyClient
from src.utils import RateLimiter

# Import the client helper
from .client_helper import add_test_methods_to_client

@pytest.fixture
def mock_client():
    """Create a mocked client for testing"""
    # Create a mocked client
    client = MidjourneyClient(
        user_token="mock_token",
        bot_token="mock_token",
        channel_id="123456789",
        guild_id="123456789"
    )
    
    # Add test methods to the client
    client = add_test_methods_to_client(client)
    
    # Mock the Discord user gateway
    client.user_gateway = MagicMock(spec=['session_id', 'connected', 'close'])
    client.user_gateway.session_id = "mock_test_session_id"
    
    # Mock for user_gateway.connected.is_set()
    mock_connected_event = MagicMock()
    mock_connected_event.is_set = MagicMock(return_value=True)
    client.user_gateway.connected = mock_connected_event
    
    client.user_gateway.close = AsyncMock()
    
    # Mock rate limiter
    client.rate_limiter = RateLimiter()
    # Override the rate limiter's wait method to avoid waiting in tests
    client.rate_limiter.wait = AsyncMock()
    
    # Add a close method to the client itself if it doesn't exist yet (for tests only)
    if not hasattr(client, 'close'):
        client.close = AsyncMock()
        
    return client

@pytest_asyncio.fixture
async def mock_rate_limiter(mock_client):
    """Mock the rate limiter's with_retry method"""
    original_with_retry = mock_client.rate_limiter.with_retry
    
    async def mock_with_retry(func, *args, max_retries=3, retry_status_codes=None, **kwargs):
        """Mock implementation of with_retry that just calls the function once without retries"""
        # Call the function directly without retry logic, but don't pass retry-specific kwargs
        return await func(*args, **kwargs)
    
    mock_client.rate_limiter.with_retry = AsyncMock(side_effect=mock_with_retry)
    
    yield mock_client
    
    # Restore original method if needed
    mock_client.rate_limiter.with_retry = original_with_retry

@pytest.mark.asyncio
async def test_imagine_command_format(mock_rate_limiter, monkeypatch):
    """Test the format of the /imagine command payload"""
    client = mock_rate_limiter
    
    # Mock the requests.post method
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'id': 'response_id', 'type': 4}
    mock_response.text = json.dumps({'id': 'response_id', 'type': 4})
    mock_response.headers = {'Content-Type': 'application/json', 'X-RateLimit-Remaining': '10'}
    
    # Configure the mock to return the response
    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr('src.client.requests.post', mock_post)
    
    # Run the command
    prompt = "a beautiful sunset over mountains"
    await client._send_imagine_command(prompt)
    
    # Check that the post method was called with the right arguments
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    
    # The URL should be the first argument
    assert args[0] == 'https://discord.com/api/v10/interactions'
    
    # Parse the JSON payload
    payload = kwargs['json']
    
    # Verify the payload structure
    assert payload['type'] == 2  # APPLICATION_COMMAND
    assert payload['application_id'] == '936929561302675456'  # Midjourney app ID
    assert payload['guild_id'] == '123456789'
    assert payload['channel_id'] == '123456789'
    
    # Verify the command data
    command_data = payload['data']
    assert command_data['name'] == 'imagine'
    assert command_data['id'] == '938956540159881230'
    
    # Verify the prompt is in the options
    assert len(command_data['options']) == 1
    assert command_data['options'][0]['name'] == 'prompt'
    assert command_data['options'][0]['value'] == prompt

@pytest.mark.asyncio
async def test_slash_command_with_options(mock_rate_limiter, monkeypatch):
    """Test a slash command with multiple options"""
    client = mock_rate_limiter
    
    # Mock the requests.post method
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'id': 'response_id', 'type': 4}
    mock_response.text = json.dumps({'id': 'response_id', 'type': 4})
    mock_response.headers = {'Content-Type': 'application/json', 'X-RateLimit-Remaining': '10'}
    
    # Configure the mock to return the response
    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr('src.client.requests.post', mock_post)
    
    # Create a test command with options
    command = {
        'name': 'settings',
        'id': '972289487818334209',
        'options': [
            {'name': 'remix', 'value': True},
            {'name': 'style', 'value': 'raw'}
        ]
    }
    
    # Run the command
    await client._send_slash_command(command)
    
    # Check that the post method was called with the right arguments
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    
    # The URL should be the first argument
    assert args[0] == 'https://discord.com/api/v10/interactions'
    
    # Parse the JSON payload
    payload = kwargs['json']
    
    # Verify the payload structure
    assert payload['type'] == 2  # APPLICATION_COMMAND
    assert payload['application_id'] == '936929561302675456'  # Midjourney app ID
    
    # Verify the command data
    command_data = payload['data']
    assert command_data['name'] == 'settings'
    assert command_data['id'] == '972289487818334209'
    
    # Verify options
    assert len(command_data['options']) == 2
    assert command_data['options'][0]['name'] == 'remix'
    assert command_data['options'][0]['value'] == True
    assert command_data['options'][1]['name'] == 'style'
    assert command_data['options'][1]['value'] == 'raw'

@pytest.mark.asyncio
async def test_handling_slash_command_response(mock_rate_limiter, monkeypatch):
    """Test handling of slash command responses"""
    client = mock_rate_limiter
    
    # Mock the requests.post method
    mock_response = MagicMock()
    mock_response.status_code = 204  # Discord usually returns 204 for successful interactions
    mock_response.json.return_value = {}
    mock_response.text = ""
    mock_response.headers = {'X-RateLimit-Remaining': '10'}
    
    # Configure the mock to return the response
    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr('src.client.requests.post', mock_post)
    
    # Run the command
    prompt = "a beautiful sunset over mountains"
    response = await client._send_imagine_command(prompt)
    
    # Verify response handling
    mock_post.assert_called_once()
    assert response is not None
    assert response.get('status') == 204
    assert response.get('text_response') == 'No Content'

@pytest.mark.asyncio
async def test_error_handling_in_slash_command(mock_rate_limiter, monkeypatch):
    """Test error handling in slash commands"""
    client = mock_rate_limiter
    
    # Mock the requests.post method to raise an error
    mock_post = MagicMock(side_effect=Exception("Network error"))
    monkeypatch.setattr('src.client.requests.post', mock_post)
    
    # Run the command and expect it to handle the error gracefully
    prompt = "a beautiful sunset over mountains"
    
    # The _send_imagine_command method should handle the error and return None
    response = await client._send_imagine_command(prompt)
    
    # Verify error response
    assert response is None 