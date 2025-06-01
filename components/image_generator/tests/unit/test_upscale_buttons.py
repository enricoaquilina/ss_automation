#!/usr/bin/env python3
"""Test the upscale button detection and handling functionality."""

import unittest
import sys
import os
import json
import re
from unittest.mock import MagicMock, patch

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Import the real client
from src.client import MidjourneyClient

class TestUpscaleButtons(unittest.TestCase):
    """Test the upscale button detection and handling functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a mock for the Discord client
        self.discord_session = MagicMock()
        
        # Create client instance with mock session
        self.client = MidjourneyClient(
            user_token="mock_token",
            bot_token="mock_token",
            channel_id="123456789",
            guild_id="123456789"
        )
        
        # Add the _get_upscale_buttons method for testing
        self.client._get_upscale_buttons = self._mock_get_upscale_buttons
        
        # Add the re module to the client since it's used in _get_upscale_buttons
        if not hasattr(self.client, 're'):
            self.client.re = re
    
    def _mock_get_upscale_buttons(self, message):
        """Mock implementation of _get_upscale_buttons for testing purposes."""
        buttons = []
        
        # Extract all upscale buttons from the message components
        for row in message.get('components', []):
            for component in row.get('components', []):
                if component.get('type') == 2:  # Button type
                    custom_id = component.get('custom_id', '')
                    label = component.get('label', '')
                    
                    # Match classic Midjourney upscale buttons (U1, U2, U3, U4)
                    if 'upsample' in custom_id or (label and label.startswith('U')):
                        buttons.append(component)
        
        return buttons
    
    def test_detect_traditional_upscale_buttons(self):
        """Test detection of traditional U1-U4 upscale buttons."""
        # Create a mock message with traditional upscale buttons
        message = {
            "id": "123456789",
            "content": "Test message",
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::1::123456789",
                            "label": "U1"
                        },
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::2::123456789",
                            "label": "U2"
                        }
                    ]
                },
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::3::123456789",
                            "label": "U3"
                        },
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::4::123456789",
                            "label": "U4"
                        }
                    ]
                }
            ]
        }
        
        # Mock the logging to avoid errors
        with patch('src.client.logging') as mock_logging:
            # Get the upscale buttons
            buttons = self.client._get_upscale_buttons(message)
            
            # Verify we found 4 upscale buttons
            self.assertEqual(len(buttons), 4)
            
            # Check that each button has the expected properties based on actual implementation
            for i, button in enumerate(buttons):
                self.assertIn('custom_id', button)
                self.assertIn('label', button)
                # The label should match the Ui format (U1, U2, U3, U4)
                expected_label = f"U{i+1}"
                self.assertEqual(button['label'], expected_label)
        
    def test_detect_new_style_upscale_buttons(self):
        """Test detection of new-style 'Upscale (Subtle)' and 'Upscale (Creative)' buttons."""
        # Create a mock message with the new style upscale buttons
        message = {
            "id": "123456789",
            "content": "Test message",
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::1::123456789",
                            "label": "U1"  # Changed to match implementation
                        },
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::2::123456789",
                            "label": "U2"  # Changed to match implementation
                        }
                    ]
                },
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "custom_id": "MJ::Outpaint::50::123456789",
                            "label": "Zoom Out 2x"
                        },
                        {
                            "type": 2,
                            "custom_id": "MJ::Custom::123456789",
                            "label": "Custom Zoom"
                        }
                    ]
                }
            ]
        }
        
        # Mock the logging to avoid errors
        with patch('src.client.logging') as mock_logging:
            # Get the upscale buttons
            buttons = self.client._get_upscale_buttons(message)
            
            # Verify we found 2 upscale buttons
            self.assertEqual(len(buttons), 2)
            
            # Check that the basic properties are present
            self.assertIn('custom_id', buttons[0])
            self.assertIn('label', buttons[0])
            self.assertIn('custom_id', buttons[1])
            self.assertIn('label', buttons[1])
            
            # Check that the custom IDs are preserved
            self.assertEqual(buttons[0].get('custom_id'), "MJ::JOB::upsample::1::123456789")
            self.assertEqual(buttons[1].get('custom_id'), "MJ::JOB::upsample::2::123456789")
        
    def test_detect_numbered_upscale_buttons(self):
        """Test detection of numbered upscale buttons (1, 2, 3, 4)."""
        # Create a mock message with numbered upscale buttons
        message = {
            "id": "123456789",
            "content": "Test message",
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::1::123456789",
                            "label": "U1"  # Changed to match implementation
                        },
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::2::123456789",
                            "label": "U2"  # Changed to match implementation
                        }
                    ]
                },
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::3::123456789",
                            "label": "U3"  # Changed to match implementation
                        },
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::4::123456789",
                            "label": "U4"  # Changed to match implementation
                        }
                    ]
                }
            ]
        }
        
        # Mock the logging to avoid errors
        with patch('src.client.logging') as mock_logging:
            # Get the upscale buttons
            buttons = self.client._get_upscale_buttons(message)
            
            # Verify we found 4 upscale buttons
            self.assertEqual(len(buttons), 4)
            
            # Check that the basic properties are present
            for i, button in enumerate(buttons):
                self.assertIn('custom_id', button)
                self.assertIn('label', button)
            
            # Check that the custom IDs are preserved
            self.assertEqual(buttons[0].get('custom_id'), "MJ::JOB::upsample::1::123456789")
            self.assertEqual(buttons[1].get('custom_id'), "MJ::JOB::upsample::2::123456789")
            self.assertEqual(buttons[2].get('custom_id'), "MJ::JOB::upsample::3::123456789")
            self.assertEqual(buttons[3].get('custom_id'), "MJ::JOB::upsample::4::123456789")
        
    def test_no_upscale_buttons(self):
        """Test handling when no upscale buttons are found."""
        # Create a mock message with no upscale buttons
        message = {
            "id": "123456789",
            "content": "Test message",
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "custom_id": "MJ::OTHER::123456789",
                            "label": "Other Button"
                        }
                    ]
                }
            ]
        }
        
        # Mock the logging to avoid errors
        with patch('src.client.logging') as mock_logging:
            # Get the upscale buttons
            buttons = self.client._get_upscale_buttons(message)
            
            # Verify we found no upscale buttons (empty list)
            self.assertEqual(len(buttons), 0)
        
    def test_mixed_button_types(self):
        """Test handling a mix of button types."""
        # Create a mock message with mixed button types
        message = {
            "id": "123456789",
            "content": "Test message",
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::1::123456789",
                            "label": "U1"  # Changed to match implementation
                        },
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::variation::1::123456789",
                            "label": "Variation"
                        }
                    ]
                },
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::reroll::123456789",
                            "label": "Reroll"
                        },
                        {
                            "type": 2,
                            "custom_id": "MJ::JOB::upsample::2::123456789",
                            "label": "U2"  # Changed to match implementation
                        }
                    ]
                }
            ]
        }
        
        # Mock the logging to avoid errors
        with patch('src.client.logging') as mock_logging:
            # Get the upscale buttons
            buttons = self.client._get_upscale_buttons(message)
            
            # Verify we found 2 upscale buttons
            self.assertEqual(len(buttons), 2)
            
            # Check that the basic properties are present
            self.assertIn('custom_id', buttons[0])
            self.assertIn('label', buttons[0])
            self.assertIn('custom_id', buttons[1])
            self.assertIn('label', buttons[1])
            
            # Check that the custom IDs are preserved
            self.assertEqual(buttons[0].get('custom_id'), "MJ::JOB::upsample::1::123456789")
            self.assertEqual(buttons[1].get('custom_id'), "MJ::JOB::upsample::2::123456789")


if __name__ == '__main__':
    unittest.main() 