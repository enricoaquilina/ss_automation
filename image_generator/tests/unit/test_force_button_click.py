#!/usr/bin/env python3
"""
Test for the force_button_click function session ID handling

Tests that the force_button_click function properly uses the provided session ID
rather than generating a new one each time.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import json
import os
import sys
import requests
import random

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

class TestForceButtonClick(unittest.TestCase):
    """Test the force_button_click function session ID handling"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a logger mock
        self.logger_mock = MagicMock()
        
        # Sample parameters
        self.message_id = 'test_message_id'
        self.custom_id = 'test_custom_id'
        self.channel_id = 'test_channel_id'
        self.token = 'test_token'
        
        # This is the critical parameter - should be passed through, not regenerated
        self.session_id = 'a0123456789abcdef0123456789abcdef'

    @patch('requests.post')
    @patch('random.choice')
    def test_session_id_is_used_directly(self, random_choice_mock, requests_post_mock):
        """Test that the provided session_id is used directly without regenerating"""
        # Import the module to test (importing here to use the mocked modules)
        from scripts.reprocess.enhanced_upscale_handler import force_button_click
        
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 204
        requests_post_mock.return_value = mock_response
        
        # Call the function with our session_id
        result = force_button_click(
            message_id=self.message_id,
            custom_id=self.custom_id,
            channel_id=self.channel_id,
            token=self.token,
            session_id=self.session_id
        )
        
        # Verify the function succeeded
        self.assertTrue(result)
        
        # Assert requests.post was called once
        requests_post_mock.assert_called_once()
        
        # Get the payload that was passed to requests.post
        args, kwargs = requests_post_mock.call_args
        payload = kwargs.get('json', {})
        
        # Assert that the session_id in the payload matches our input session_id exactly
        self.assertEqual(payload.get('session_id'), self.session_id)
        
        # Assert that random.choice was NOT called - meaning no new session_id was generated
        random_choice_mock.assert_not_called()

    @patch('requests.post')
    def test_session_id_is_generated_if_missing(self, requests_post_mock):
        """Test that a session_id is generated if none is provided"""
        # Import the module to test
        from scripts.reprocess.enhanced_upscale_handler import force_button_click
        
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 204
        requests_post_mock.return_value = mock_response
        
        # Call the function without a session_id
        result = force_button_click(
            message_id=self.message_id,
            custom_id=self.custom_id,
            channel_id=self.channel_id,
            token=self.token,
            # No session_id provided
        )
        
        # Verify the function succeeded
        self.assertTrue(result)
        
        # Assert requests.post was called once
        requests_post_mock.assert_called_once()
        
        # Get the payload that was passed to requests.post
        args, kwargs = requests_post_mock.call_args
        payload = kwargs.get('json', {})
        
        # Assert that a session_id was generated and included in the payload
        self.assertIsNotNone(payload.get('session_id'))
        # Verify it follows the expected format (a + 31 hex chars)
        self.assertTrue(payload.get('session_id', '').startswith('a'))
        self.assertEqual(len(payload.get('session_id', '')), 32)

if __name__ == '__main__':
    unittest.main() 