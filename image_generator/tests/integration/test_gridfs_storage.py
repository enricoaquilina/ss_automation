#!/usr/bin/env python3
"""
Unit Tests for GridFS Storage

Tests the GridFSStorage class to ensure it correctly stores and retrieves images
in MongoDB GridFS.
"""

import os
import sys
import asyncio
from datetime import datetime
import dotenv
from unittest.mock import Mock, patch, MagicMock
import pytest
from bson import ObjectId

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.storage import GridFSStorage, GRIDFS_AVAILABLE
except ImportError:
    # Populate with mock if imports fail
    GRIDFS_AVAILABLE = False
    GridFSStorage = None

# Skip all tests if GridFS is not available
pytestmark = pytest.mark.skipif(not GRIDFS_AVAILABLE, reason="GridFS not available")


# Mock image data for testing
TEST_IMAGE_DATA = b'MOCK_IMAGE_DATA'
TEST_PROMPT = "test cosmic dolphin prompt"
TEST_METADATA = {
    "prompt": TEST_PROMPT,
    "message_id": "123456789012345678",
    "image_url": "https://cdn.discordapp.com/attachments/123/456/test.png",
    "timestamp": datetime.now().isoformat()
}
TEST_POST_ID = "60f7b0b9b9b9b9b9b9b9b9b9"
TEST_FILE_ID = ObjectId("60f7b0b9b9b9b9b9b9b9b9b9")


class MockGridFSStorage(GridFSStorage):
    """Mock version of GridFSStorage for testing"""
    
    def __init__(self, *args, **kwargs):
        # Skip the actual MongoDB connection
        self.db = MagicMock()
        self.fs = MagicMock()
        self.post_id = kwargs.get('post_id')
        
        # Set up mock methods
        self.fs.put.return_value = TEST_FILE_ID
        self.fs.exists.return_value = True
        
        # Set up mock file
        mock_file = MagicMock()
        mock_file.read.return_value = TEST_IMAGE_DATA
        self.fs.get.return_value = mock_file
        
        # Mock collections
        self.db.post_images = MagicMock()
        self.db.posts = MagicMock()
        self.db.fs.files = MagicMock()
        
        # Set up mock results
        self.db.post_images.update_one.return_value = MagicMock(modified_count=1)
        self.db.posts.update_one.return_value = MagicMock(modified_count=1)
        self.db.fs.files.update_one.return_value = MagicMock(modified_count=1)


@pytest.mark.asyncio
async def test_grid_save():
    """Test saving a grid image to GridFS"""
    storage = MockGridFSStorage(post_id=TEST_POST_ID)
    
    # Call the save_grid method
    file_id = await storage.save_grid(TEST_IMAGE_DATA, TEST_METADATA)
    
    # Check that GridFS.put was called with the right parameters
    storage.fs.put.assert_called_once()
    args, kwargs = storage.fs.put.call_args
    assert args[0] == TEST_IMAGE_DATA
    assert kwargs['contentType'] == 'image/png'
    assert kwargs['metadata']['is_grid'] is True
    assert kwargs['metadata']['prompt'] == TEST_PROMPT
    
    # Check that the returned file ID is as expected
    assert file_id == str(TEST_FILE_ID)
    
    # Check that post_images was updated
    storage.db.post_images.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_upscale_save():
    """Test saving an upscale image to GridFS"""
    storage = MockGridFSStorage(post_id=TEST_POST_ID)
    
    # Prepare upscale metadata
    upscale_metadata = TEST_METADATA.copy()
    upscale_metadata['variant'] = 2
    
    # Call the save_upscale method
    file_id = await storage.save_upscale(TEST_IMAGE_DATA, upscale_metadata)
    
    # Check that GridFS.put was called with the right parameters
    storage.fs.put.assert_called_once()
    args, kwargs = storage.fs.put.call_args
    assert args[0] == TEST_IMAGE_DATA
    assert kwargs['contentType'] == 'image/png'
    assert kwargs['metadata']['is_grid'] is False
    assert kwargs['metadata']['is_upscale'] is True
    assert kwargs['metadata']['variant_idx'] == 2
    assert kwargs['metadata']['prompt'] == TEST_PROMPT
    
    # Check that the returned file ID is as expected
    assert file_id == str(TEST_FILE_ID)
    
    # Check that post_images was updated
    storage.db.post_images.update_one.assert_called_once()
    
    # Check that posts was updated with upscale information
    storage.db.posts.update_one.assert_called_once()


def test_get_image():
    """Test retrieving an image from GridFS"""
    storage = MockGridFSStorage()
    
    # Call the get_image method
    image_data = storage.get_image(str(TEST_FILE_ID))
    
    # Check that GridFS.exists and get were called
    storage.fs.exists.assert_called_once()
    storage.fs.get.assert_called_once()
    
    # Check that the returned data is correct
    assert image_data == TEST_IMAGE_DATA


def test_save_metadata():
    """Test saving metadata for a GridFS file"""
    storage = MockGridFSStorage()
    
    # Call the save_metadata method
    result = storage.save_metadata(TEST_METADATA, str(TEST_FILE_ID))
    
    # Check that fs.files was updated
    storage.db.fs.files.update_one.assert_called_once()
    
    # Check that the result is True (success)
    assert result is True


if __name__ == "__main__":
    # Load .env file for MongoDB connection
    dotenv.load_dotenv()
    
    # Run tests
    pytest.main(["-xvs", __file__]) 