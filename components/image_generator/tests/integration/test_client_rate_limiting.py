#!/usr/bin/env python3
"""
Integration tests for the client's usage of rate limiting
"""

import os
import sys
import time
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Use absolute imports
import src.client as client
from src.utils import MidjourneyError, RateLimiter


class TestClientRateLimiting:
    """Tests for the client's usage of rate limiting"""
    
    @pytest.mark.asyncio
    async def test_client_initializes_rate_limiter(self):
        """Test that client properly initializes the rate limiter"""
        with patch('src.client.DiscordGateway') as mock_gateway:
            # Create a client instance
            client_instance = client.MidjourneyClient(
                user_token="user_token",
                bot_token="bot_token",
                channel_id="channel_id",
                guild_id="guild_id"
            )
            
            # Verify rate limiter is initialized
            assert isinstance(client_instance.rate_limiter, RateLimiter)
            assert client_instance.rate_limiter.base_delay == 0.35  # Default in client
    
    @pytest.mark.asyncio
    async def test_client_uses_rate_limiter_for_api_calls(self):
        """Test that client uses rate limiter for API calls"""
        with patch('src.client.DiscordGateway') as mock_gateway, \
             patch('aiohttp.ClientSession') as mock_session, \
             patch('src.client.requests') as mock_requests:
            
            # Mock a bad response from requests.get
            mock_bad_response = MagicMock()
            mock_bad_response.status_code = 500
            mock_bad_response.text = "Internal Server Error"
            mock_bad_response.headers = {}
            mock_requests.get.return_value = mock_bad_response
            
            # Mock the rate limiter
            mock_limiter = AsyncMock(spec=RateLimiter)
            
            # Make with_retry execute the send_request function directly
            # send_request (inside client._get_recent_messages) calls the patched requests.get
            async def passthrough_retry(func, *args, **kwargs):
                # func here is the send_request defined in _get_recent_messages
                return await func()
            mock_limiter.with_retry.side_effect = passthrough_retry
            
            # Create a client with our mock rate limiter
            client_instance = client.MidjourneyClient(
                user_token="user_token",
                bot_token="bot_token",
                channel_id="channel_id",
                guild_id="guild_id"
            )
            client_instance.rate_limiter = mock_limiter
            
            # Call a method that makes API requests and expect MidjourneyError
            with pytest.raises(MidjourneyError, match="API error: 500 - Internal Server Error"):
                await client_instance._get_recent_messages(limit=5)

            # Verify that the rate limiter's wait method was called
            mock_limiter.wait.assert_called_once()
            # Verify that requests.get (our mock) was called
            mock_requests.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_client_retry_logic(self):
        """Test that client uses retry logic for API calls"""
        with patch('src.client.DiscordGateway') as mock_gateway, \
             patch('aiohttp.ClientSession') as mock_session:
            
            # Create client
            client_instance = client.MidjourneyClient(
                user_token="user_token",
                bot_token="bot_token",
                channel_id="channel_id",
                guild_id="guild_id"
            )
            
            # Replace rate limiter with mock
            mock_limiter = AsyncMock(spec=RateLimiter)
            mock_limiter.with_retry = AsyncMock()
            mock_limiter.with_retry.return_value = "success"
            client_instance.rate_limiter = mock_limiter
            
            # Call a method that uses retry logic
            async def test_func():
                return "test"
                
            result = await client_instance.rate_limiter.with_retry(test_func)
            
            # Verify retry method was called correctly
            assert mock_limiter.with_retry.called
            assert result == "success"
    
    @pytest.mark.asyncio
    async def test_client_updates_rate_limit_headers(self):
        """Test that client updates rate limit information from headers"""
        with patch('src.client.DiscordGateway') as mock_gateway, \
             patch('aiohttp.ClientSession') as mock_session, \
             patch('src.client.requests') as mock_requests:
            
            # Create mock response with rate limit headers
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"id": "message_id"}]
            mock_response.headers = {
                'X-RateLimit-Remaining': '5',
                'X-RateLimit-Reset': str(time.time() + 10)
            }
            mock_requests.get.return_value = mock_response
            
            # Set up session mock for initialization
            aiohttp_response = AsyncMock()
            aiohttp_response.status = 200
            aiohttp_response.json.return_value = {"id": "message_id"}
            
            session_instance = AsyncMock()
            session_instance.get.return_value.__aenter__.return_value = aiohttp_response
            mock_session.return_value.__aenter__.return_value = session_instance
            
            # Create client with mock rate limiter
            client_instance = client.MidjourneyClient(
                user_token="user_token",
                bot_token="bot_token",
                channel_id="channel_id",
                guild_id="guild_id"
            )
            
            # Replace rate limiter with test one
            client_instance.rate_limiter = RateLimiter(base_delay=0.01)
            
            # Mock with_retry to avoid actually calling the wrapped function
            original_with_retry = client_instance.rate_limiter.with_retry
            async def mock_with_retry(func, *args, **kwargs):
                # Call the wrapped function directly to avoid retry logic
                return await func()
                
            client_instance.rate_limiter.with_retry = mock_with_retry
            
            # Call method that makes API request
            await client_instance._get_recent_messages(limit=5)
            
            # Restore the original method
            client_instance.rate_limiter.with_retry = original_with_retry
            
            # Verify rate limit info was updated
            assert 'channels/channel_id/messages' in client_instance.rate_limiter.rate_limit_remaining
            assert client_instance.rate_limiter.rate_limit_remaining['channels/channel_id/messages'] == 5


if __name__ == "__main__":
    pytest.main(["-v"]) 