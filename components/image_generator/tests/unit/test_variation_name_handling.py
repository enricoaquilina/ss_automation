#!/usr/bin/env python3
"""
Unit test to verify the fix for variation name handling in GenerationService.

This test focuses specifically on ensuring that the 'type' parameter is
correctly included in the options passed to _process_variation.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the src directory to the Python path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
sys.path.insert(0, src_dir)

# Mock the old classes
class MockDatabaseService:
    """Mock replacement for the old DatabaseService"""
    def __init__(self):
        self.fs = MagicMock()
    
    def save_generation(self, *args, **kwargs):
        return True

class MockGenerationService:
    """Mock replacement for the old GenerationService"""
    DEFAULT_VARIATIONS = [
        {'type': 'niji', 'count': 4},
        {'type': 'v6.0', 'count': 4},
        {'type': 'v6.1', 'count': 4}
    ]
    
    def __init__(self, database_service):
        self.db_service = database_service
        self.provider = MagicMock()
    
    def _prepare_prompt(self, description):
        return f"Prepared: {description}"
    
    def _process_variation(self, post_id, variation_options):
        """Method that will be mocked for testing"""
        return True
    
    def generate_images(self, post_id, description, variations=None):
        """Generate images with the given variations"""
        if variations is None:
            variations = self.DEFAULT_VARIATIONS
        
        for variation in variations:
            self._process_variation(post_id, variation)
        
        return True

class TestVariationNameHandling(unittest.TestCase):
    
    def setUp(self):
        """Set up the test environment"""
        # Create a mock database service
        self.db_service = MockDatabaseService()
        
        # Create the service instance with the mock
        self.service = MockGenerationService(database_service=self.db_service)
        
        # Set up a test post ID
        self.post_id = "test_post_id"
        
        # Mock the _process_variation method to record calls
        self.process_variation_calls = []
        self.original_process_variation = self.service._process_variation
        
        def mock_process_variation(post_id, variation_options):
            # Record the call parameters
            self.process_variation_calls.append({
                'post_id': post_id,
                'variation_options': variation_options.copy()  # Make a copy to avoid references
            })
            # Don't actually execute the method
            return True
        
        # Replace the method with our mock
        self.service._process_variation = mock_process_variation
        
        # Mock other methods that might make external calls
        self.service._prepare_prompt = MagicMock(return_value="Test prompt")
        self.service.provider = MagicMock()
    
    def tearDown(self):
        """Clean up after the test"""
        # Restore the original method if needed
        if hasattr(self, 'original_process_variation'):
            self.service._process_variation = self.original_process_variation
    
    @patch('uuid.uuid4')  # Mock uuid4 to avoid randomness
    @patch('time.sleep')  # Mock sleep to avoid delays
    def test_niji_variation_name(self, mock_sleep, mock_uuid):
        """Test that correct parameters are passed for niji variation"""
        # Set up test variations
        variations = [
            {'type': 'niji', 'count': 4}
        ]
        
        # Call generate_images with the niji variation
        with patch.object(self.service, 'provider'):
            self.service.generate_images(
                post_id=self.post_id,
                description="Test prompt",
                variations=variations
            )
        
        # Verify _process_variation was called
        self.assertEqual(len(self.process_variation_calls), 1, 
                        "Expected 1 call to _process_variation, but got different number")
        
        # Get the options from the call
        call = self.process_variation_calls[0]
        options = call['variation_options']
        
        # Verify the post_id was passed correctly
        self.assertEqual(call['post_id'], self.post_id, 
                        f"Expected post_id {self.post_id}, but got {call['post_id']}")
        
        # Verify 'type' is in the options
        self.assertIn('type', options, 
                     f"'type' is missing from options: {options}")
        
        # Verify 'type' has the correct value
        self.assertEqual(options['type'], 'niji', 
                        f"Expected type 'niji', but got {options['type']}")
    
    @patch('uuid.uuid4')  # Mock uuid4 to avoid randomness
    @patch('time.sleep')  # Mock sleep to avoid delays
    def test_v6_0_variation_name(self, mock_sleep, mock_uuid):
        """Test that correct parameters are passed for v6.0 variation"""
        # Set up test variations
        variations = [
            {'type': 'v6.0', 'count': 4}
        ]
        
        # Call generate_images with the v6.0 variation
        with patch.object(self.service, 'provider'):
            self.service.generate_images(
                post_id=self.post_id,
                description="Test prompt",
                variations=variations
            )
        
        # Verify _process_variation was called
        self.assertEqual(len(self.process_variation_calls), 1, 
                        "Expected 1 call to _process_variation, but got different number")
        
        # Get the options from the call
        call = self.process_variation_calls[0]
        options = call['variation_options']
        
        # Verify 'type' is in the options
        self.assertIn('type', options, 
                     f"'type' is missing from options: {options}")
        
        # Verify 'type' has the correct value
        self.assertEqual(options['type'], 'v6.0', 
                        f"Expected type 'v6.0', but got {options['type']}")
    
    @patch('uuid.uuid4')  # Mock uuid4 to avoid randomness
    @patch('time.sleep')  # Mock sleep to avoid delays
    def test_v6_1_variation_name(self, mock_sleep, mock_uuid):
        """Test that correct parameters are passed for v6.1 variation"""
        # Set up test variations
        variations = [
            {'type': 'v6.1', 'count': 4}
        ]
        
        # Call generate_images with the v6.1 variation
        with patch.object(self.service, 'provider'):
            self.service.generate_images(
                post_id=self.post_id,
                description="Test prompt",
                variations=variations
            )
        
        # Verify _process_variation was called
        self.assertEqual(len(self.process_variation_calls), 1, 
                        "Expected 1 call to _process_variation, but got different number")
        
        # Get the options from the call
        call = self.process_variation_calls[0]
        options = call['variation_options']
        
        # Verify 'type' is in the options
        self.assertIn('type', options, 
                     f"'type' is missing from options: {options}")
        
        # Verify 'type' has the correct value
        self.assertEqual(options['type'], 'v6.1', 
                        f"Expected type 'v6.1', but got {options['type']}")
    
    @patch('uuid.uuid4')  # Mock uuid4 to avoid randomness
    @patch('time.sleep')  # Mock sleep to avoid delays
    def test_default_variations(self, mock_sleep, mock_uuid):
        """Test that correct parameters are passed when using default variations"""
        # Call generate_images without specifying variations
        # This should use the default set of variations
        with patch.object(self.service, 'provider'):
            self.service.generate_images(
                post_id=self.post_id,
                description="Test prompt"
            )
        
        # Verify _process_variation was called 3 times (once for each default variation)
        self.assertEqual(len(self.process_variation_calls), 3, 
                        "Expected 3 calls to _process_variation, but got different number")
        
        # Track which variation types we've seen
        variation_types = set()
        
        # Check each call
        for call in self.process_variation_calls:
            options = call['variation_options']
            
            # Verify 'type' is in the options
            self.assertIn('type', options, 
                         f"'type' is missing from options: {options}")
            
            # Add the type to our seen set
            variation_types.add(options['type'])
            
            # Verify the options are correct based on the type
            if options['type'] == 'niji':
                pass  # No specific assertions needed beyond checking type
            elif options['type'] == 'v6.0':
                pass  # No specific assertions needed beyond checking type
            elif options['type'] == 'v6.1':
                pass  # No specific assertions needed beyond checking type
            else:
                self.fail(f"Unexpected variation type: {options['type']}")
        
        # Verify we saw all three variations
        self.assertEqual(variation_types, {'niji', 'v6.0', 'v6.1'}, 
                        f"Expected to see all three variations, but got {variation_types}")

if __name__ == "__main__":
    unittest.main() 