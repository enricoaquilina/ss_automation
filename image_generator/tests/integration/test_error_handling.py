#!/usr/bin/env python3
"""
Integration Tests for Error Handling

Tests the error handling for various types of errors in the Midjourney client.
"""

import os
import sys
import json
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

# Import from the src directory
from src.client import MidjourneyClient
from src.utils import (
    MidjourneyError, PreModerationError, PostModerationError, EphemeralModerationError,
    InvalidRequestError, QueueFullError, JobQueuedError, RateLimiter
)
from src.models import GenerationResult

# Import the client helper
from .client_helper import add_test_methods_to_client

class TestErrorHandling(unittest.TestCase):
    """Integration tests for error handling in the Midjourney client"""
    
    def setUp(self):
        """Set up the test environment with a mocked client"""
        # Create a client with mock tokens
        self.client = MidjourneyClient(
            user_token="mock_token",
            bot_token="mock_token",
            channel_id="123456789",
            guild_id="123456789"
        )
        
        # Add test methods to the client
        self.client = add_test_methods_to_client(self.client)
        
        # Mock the Discord session
        self.client.user_gateway = MagicMock()
        self.client.user_gateway.connected = AsyncMock()
        self.client.user_gateway.connected.__bool__ = lambda self: True
        
        # Mock rate limiter
        self.client.rate_limiter = RateLimiter()
        
        # Add a close method if it doesn't exist yet
        if not hasattr(self.client, 'close'):
            self.client.close = AsyncMock()

    def tearDown(self):
        """Clean up after tests"""
        # Ensure we close the client
        if hasattr(self.client, 'close'):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.client.close())
    
    def test_pre_moderation_error(self):
        """Test handling of pre-moderation errors"""
        # Error message example
        error_content = "Your submission was blocked by the moderation system for the prompt: 'inappropriate content'. 'adult' in this case."
        
        # Create a mock response
        mock_response = {
            'id': 'response_id',
            'channel_id': '123456789',
            'content': error_content,
            'embeds': [],
            'components': [],
            'attachments': []
        }
        
        # Mock the interaction response
        with patch.object(self.client, '_send_imagine_command', new_callable=AsyncMock) as mock_send:
            # Configure the mock to return None (early failure)
            mock_send.return_value = None
            
            # Configure the generation future to be empty for 30 seconds
            # This is a sign of pre-moderation
            with patch.object(self.client, '_get_imagine_error', return_value="Pre-moderation error"):
                
                # Run the test
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(self.client.generate_image("adult content prompt"))
                
                # Verify error handling
                self.assertIsInstance(result, GenerationResult)
                self.assertFalse(result.success)
                self.assertIsNotNone(result.error)
                self.assertIn("moderation", result.error.lower())
    
    def test_queue_full_error(self):
        """Test handling of queue full errors"""
        # Error message example
        error_content = "Your request couldn't be processed. The Midjourney bot is currently at maximum capacity. (Queue full error)"
        
        # Mock the interaction response
        with patch.object(self.client, '_send_imagine_command', new_callable=AsyncMock) as mock_send:
            # Configure the mock to return the error
            mock_send.return_value = {
                'id': 'response_id',
                'channel_id': '123456789',
                'content': error_content,
                'embeds': [],
                'components': [],
                'attachments': []
            }
            
            # Configure the _get_imagine_error method to detect the error
            with patch.object(self.client, '_get_imagine_error', return_value="Queue is full, try again later"):
                
                # Run the test
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(self.client.generate_image("test prompt"))
                
                # Verify error handling
                self.assertIsInstance(result, GenerationResult)
                self.assertFalse(result.success)
                self.assertIsNotNone(result.error)
                self.assertIn("Queue", result.error)
    
    def test_invalid_parameter_error(self):
        """Test handling of invalid parameter errors"""
        # Error message example
        error_content = "Invalid parameter. Please check your input and try again."
        
        # Mock the interaction response
        with patch.object(self.client, '_send_imagine_command', new_callable=AsyncMock) as mock_send:
            # Configure the mock to return the error
            mock_send.return_value = {
                'id': 'response_id',
                'channel_id': '123456789',
                'content': error_content,
                'embeds': [],
                'components': [],
                'attachments': []
            }
            
            # Configure the _get_imagine_error method to detect the error
            with patch.object(self.client, '_get_imagine_error', return_value=error_content):
                
                # Run the test
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(self.client.generate_image("test prompt"))
                
                # Verify error handling
                self.assertIsInstance(result, GenerationResult)
                self.assertFalse(result.success)
                self.assertIsNotNone(result.error)
                self.assertIn("Invalid parameter", result.error)
    
    def test_unknown_error(self):
        """Test handling of unknown errors"""
        # Error message example
        error_content = "An unknown error occurred."
        
        # Mock the interaction response
        with patch.object(self.client, '_send_imagine_command', new_callable=AsyncMock) as mock_send:
            # Configure the mock to raise an exception
            mock_send.side_effect = Exception("Unexpected error")
            
            # Run the test
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.client.generate_image("test prompt"))
            
            # Verify error handling
            self.assertIsInstance(result, GenerationResult)
            self.assertFalse(result.success)
            self.assertIsNotNone(result.error)
            self.assertIn("error", result.error.lower())


if __name__ == "__main__":
    unittest.main() 