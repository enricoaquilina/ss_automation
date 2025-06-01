#!/usr/bin/env python3
"""
Test script for upscale processing functionality

This script tests the upscale processing logic in the generation service,
verifying that upscale results are properly handled regardless of key format.
"""

import os
import sys
import unittest
import logging
import pytest
import asyncio
from unittest.mock import MagicMock, patch
import datetime
from bson import ObjectId

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Import from the proper path - try both absolute and relative imports
try:
    from src.image_generator.services.generation_service import GenerationService
except ImportError as e:
    print(f"ERROR: Could not import GenerationService. Check PYTHONPATH. Error: {e}")
    # Also print sys.path to help debug
    print(f"Current sys.path: {sys.path}")
    # And current PYTHONPATH env var
    print(f"Current PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    sys.exit(1)

# Create a custom AsyncMock that returns a value when awaited
class AsyncReturnValueMock:
    """A mock that returns a value when awaited"""
    def __init__(self, return_value):
        self.return_value = return_value
        
    def __await__(self):
        async def _async_return():
            return self.return_value
        return _async_return().__await__()

@pytest.fixture
def mock_generation_service():
    """Create a mock generation service for testing"""
    # Create a mock for the database
    mock_db = MagicMock()
    
    # Create a mock for the client
    mock_client = MagicMock()
    
    # Create a mock for the storage
    mock_storage = MagicMock()
    
    # Create the service with the mocks
    service = GenerationService(db=mock_db, client=mock_client, storage=mock_storage)
    
    # Make _process_and_save_upscale_result return an awaitable mock
    service._process_and_save_upscale_result = MagicMock(
        return_value=AsyncReturnValueMock({'id': ObjectId()})
    )
    
    return service

@pytest.fixture
def sample_upscale_result_format1():
    """Sample upscale result with id and url keys"""
    return {
        "id": "upscaled_message_id_123",
        "url": "https://example.com/upscaled_image_1.jpg",
        "button_idx": 1,
        "original_message_id": "original_msg"
    }

@pytest.fixture
def sample_upscale_result_format2():
    """Sample upscale result with message_id and image_url keys"""
    return {
        "message_id": "upscaled_message_id_456",
        "image_url": "https://example.com/upscaled_image_2.jpg",
        "button_idx": 2,
        "original_message_id": "original_msg"
    }

@pytest.fixture
def sample_upscale_result_both_formats():
    """Sample upscale result with both key formats"""
    return {
        "id": "upscaled_message_id_789",
        "url": "https://example.com/upscaled_image_3a.jpg",
        "message_id": "upscaled_message_id_789",
        "image_url": "https://example.com/upscaled_image_3b.jpg",
        "button_idx": 3,
        "original_message_id": "original_msg"
    }

class TestUpscaleProcessing:
    """Test case for upscale processing functionality"""
    
    @pytest.mark.asyncio
    async def test_upscale_processing_with_message_id_and_image_url_keys(self, mock_generation_service, sample_upscale_result_format2):
        """Test upscale processing with message_id and image_url keys"""
        service = mock_generation_service
        
        # Add validation data to the sample result
        sample_upscale_result_format2['validation'] = {
            'content_indicators_match': True,
            'references_original': True,
            'is_upscale_result': True
        }
        
        # Mock the _wait_for_upscale_result to return an awaitable mock with our sample result
        service._wait_for_upscale_result = MagicMock(
            return_value=AsyncReturnValueMock(sample_upscale_result_format2)
        )
        
        # Call the method we're testing - properly await the coroutine
        result = await service._process_upscale(
            message_id="original_msg",
            upscale_idx=1,
            post_id="66b88b70b2979f6117b347f2",
            variation_name="v6.0"
        )
        
        # Assert that the process was successful
        assert result is True
        
        # Verify the mock was called with the right parameters
        service._wait_for_upscale_result.assert_called_once_with(
            "original_msg", 1, timeout=60
        )
        
    @pytest.mark.asyncio
    async def test_upscale_processing_with_id_and_url_keys(self, mock_generation_service, sample_upscale_result_format1):
        """Test upscale processing with id and url keys"""
        service = mock_generation_service
        
        # Create a test result with ONLY id and url keys (no message_id or image_url)
        old_format_result = {
            "id": "upscaled_message_id_123",
            "url": "https://example.com/upscaled_image_1.jpg",
            "button_idx": 1,
            "original_message_id": "original_msg",
            "validation": {
                'content_indicators_match': True,
                'references_original': True,
                'is_upscale_result': True
            }
        }
        
        # Mock the _wait_for_upscale_result to return an awaitable mock with our test result
        service._wait_for_upscale_result = MagicMock(
            return_value=AsyncReturnValueMock(old_format_result)
        )
        # We also need to patch _get_image_ref_for_post to return a valid post image
        service._get_image_ref_for_post = MagicMock(return_value={"_id": ObjectId()})
            
        # Call the method we're testing - properly await the coroutine
        result = await service._process_upscale(
                message_id="original_msg",
                upscale_idx=1,
                post_id="66b88b70b2979f6117b347f2",
                variation_name="v6.0"
            )
            
        # Assert that the process was successful
        assert result is True
        
        # Verify the mocks were called with the right parameters
        service._wait_for_upscale_result.assert_called_once_with(
            "original_msg", 1, timeout=60
        )
            
    @pytest.mark.asyncio
    async def test_upscale_processing_with_both_key_formats(self, mock_generation_service, sample_upscale_result_both_formats):
        """Test upscale processing with both key formats"""
        service = mock_generation_service
        
        # Add validation data to the sample result
        sample_upscale_result_both_formats['validation'] = {
            'content_indicators_match': True,
            'references_original': True,
            'is_upscale_result': True
        }
        
        # Mock the _wait_for_upscale_result to return an awaitable mock with our sample result
        service._wait_for_upscale_result = MagicMock(
            return_value=AsyncReturnValueMock(sample_upscale_result_both_formats)
        )
        
        # Call the method we're testing - properly await the coroutine
        result = await service._process_upscale(
            message_id="original_msg",
            upscale_idx=1,
            post_id="66b88b70b2979f6117b347f2",
            variation_name="v6.0"
        )
        
        # Assert that the process was successful
        assert result is True
        
        # Verify the mock was called with the right parameters
        service._wait_for_upscale_result.assert_called_once_with(
            "original_msg", 1, timeout=60
        )
        
    @pytest.mark.asyncio
    async def test_upscale_processing_with_missing_keys(self, mock_generation_service):
        """Test upscale processing with missing keys"""
        service = mock_generation_service
        
        # Mock the _wait_for_upscale_result to return a result with missing keys
        mock_upscale_result = {
            'content': 'Test content',
            'button_idx': 1,
            'original_message_id': "original_msg"
        }
        service._wait_for_upscale_result = MagicMock(
            return_value=AsyncReturnValueMock(mock_upscale_result)
        )
        
        # Call the method we're testing - properly await the coroutine
        result = await service._process_upscale(
            message_id="original_msg",
            upscale_idx=1,
            post_id="66b88b70b2979f6117b347f2",
            variation_name="v6.0"
        )
        
        # Assert that the process failed due to missing keys
        assert result is False

if __name__ == '__main__':
    unittest.main() 