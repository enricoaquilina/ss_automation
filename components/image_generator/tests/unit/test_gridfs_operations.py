#!/usr/bin/env python3
"""
Tests for GridFS storage operations.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime
from bson import ObjectId

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from src.storage import GridFSStorage, GRIDFS_AVAILABLE
except ImportError:
    # Populate with mock if imports fail
    GRIDFS_AVAILABLE = False
    GridFSStorage = None

# Skip all tests if GridFS is not available
pytestmark = pytest.mark.skipif(not GRIDFS_AVAILABLE, reason="GridFS not available")

# Test data
TEST_MONGODB_URI = "mongodb://localhost:27017"
TEST_DB_NAME = "test_midjourney"
TEST_POST_ID = "60f7b0b9b9b9b9b9b9b9b9b9"
TEST_IMAGE_DATA = b'TEST_IMAGE_DATA'
TEST_PROMPT = "test cosmic dolphin prompt"
TEST_METADATA = {
    "prompt": TEST_PROMPT,
    "message_id": "123456789012345678",
    "image_url": "https://cdn.discordapp.com/attachments/123/456/test.png",
    "timestamp": datetime.now().isoformat()
}
TEST_FILE_ID = ObjectId("60f7b0b9b9b9b9b9b9b9b9b9")

class TestGridFSOperations(unittest.TestCase):
    """Tests for GridFS operations"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock GridFS instance
        self.mock_fs = MagicMock()
        self.mock_fs.put.return_value = TEST_FILE_ID
        self.mock_fs.exists.return_value = True
        
        # Set up mock file
        mock_file = MagicMock()
        mock_file.read.return_value = TEST_IMAGE_DATA
        self.mock_fs.get.return_value = mock_file
        
        # Create mock DB
        self.mock_db = MagicMock()
        self.mock_db.post_images = MagicMock()
        self.mock_db.posts = MagicMock()
        self.mock_db.fs.files = MagicMock()
        
        # Set up mock results
        self.mock_db.post_images.update_one.return_value = MagicMock(modified_count=1)
        self.mock_db.posts.update_one.return_value = MagicMock(modified_count=1)
        self.mock_db.fs.files.update_one.return_value = MagicMock(modified_count=1)
        
        # Create mock MongoClient
        self.mock_client = MagicMock()
        self.mock_client.__getitem__.return_value = self.mock_db
        
        # Create the patch for GridFS
        self.gridfs_patch = patch('gridfs.GridFS', return_value=self.mock_fs)
        self.mongo_client_patch = patch('pymongo.MongoClient', return_value=self.mock_client)
        
        # Start the patches
        self.mock_gridfs = self.gridfs_patch.start()
        self.mock_mongo_client = self.mongo_client_patch.start()
    
    def tearDown(self):
        """Clean up after tests"""
        # Stop the patches
        self.gridfs_patch.stop()
        self.mongo_client_patch.stop()
    
    @pytest.mark.asyncio
    async def test_grid_save(self):
        """Test saving a grid image to GridFS"""
        # Create GridFSStorage instance
        storage = GridFSStorage(
            mongodb_uri=TEST_MONGODB_URI,
            db_name=TEST_DB_NAME,
            post_id=TEST_POST_ID
        )
        
        # Call the save_grid method
        file_id = await storage.save_grid(TEST_IMAGE_DATA, TEST_METADATA)
        
        # Check that GridFS.put was called with the right parameters
        self.mock_fs.put.assert_called_once()
        args, kwargs = self.mock_fs.put.call_args
        self.assertEqual(args[0], TEST_IMAGE_DATA)
        self.assertEqual(kwargs['contentType'], 'image/png')
        self.assertTrue(kwargs['metadata']['is_grid'])
        self.assertEqual(kwargs['metadata']['prompt'], TEST_PROMPT)
        
        # Check that the returned file ID is as expected
        self.assertEqual(file_id, str(TEST_FILE_ID))
        
        # Check that post_images was updated
        self.mock_db.post_images.update_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upscale_save(self):
        """Test saving an upscale image to GridFS"""
        # Create GridFSStorage instance
        storage = GridFSStorage(
            mongodb_uri=TEST_MONGODB_URI,
            db_name=TEST_DB_NAME,
            post_id=TEST_POST_ID
        )
        
        # Prepare upscale metadata
        upscale_metadata = TEST_METADATA.copy()
        upscale_metadata['variant'] = 2
        upscale_metadata['variation'] = "v7.0"
        
        # Call the save_upscale method
        file_id = await storage.save_upscale(TEST_IMAGE_DATA, upscale_metadata)
        
        # Check that GridFS.put was called with the right parameters
        self.mock_fs.put.assert_called_once()
        args, kwargs = self.mock_fs.put.call_args
        self.assertEqual(args[0], TEST_IMAGE_DATA)
        self.assertEqual(kwargs['contentType'], 'image/png')
        self.assertFalse(kwargs['metadata']['is_grid'])
        self.assertTrue(kwargs['metadata']['is_upscale'])
        self.assertEqual(kwargs['metadata']['variant_idx'], 2)
        self.assertEqual(kwargs['metadata']['prompt'], TEST_PROMPT)
        
        # Check that the returned file ID is as expected
        self.assertEqual(file_id, str(TEST_FILE_ID))
        
        # Check that post_images was updated
        self.mock_db.post_images.update_one.assert_called_once()
        
        # Check that posts was updated with upscale information
        self.mock_db.posts.update_one.assert_called_once()
    
    def test_get_image(self):
        """Test retrieving an image from GridFS"""
        # Create GridFSStorage instance
        storage = GridFSStorage(
            mongodb_uri=TEST_MONGODB_URI,
            db_name=TEST_DB_NAME
        )
        
        # Call the get_image method
        image_data = storage.get_image(str(TEST_FILE_ID))
        
        # Check that GridFS.exists and get were called
        self.mock_fs.exists.assert_called_once()
        self.mock_fs.get.assert_called_once()
        
        # Check that the returned data is correct
        self.assertEqual(image_data, TEST_IMAGE_DATA)
    
    def test_save_metadata(self):
        """Test saving metadata for a GridFS file"""
        # Create GridFSStorage instance
        storage = GridFSStorage(
            mongodb_uri=TEST_MONGODB_URI,
            db_name=TEST_DB_NAME
        )
        
        # Call the save_metadata method
        result = storage.save_metadata(TEST_METADATA, str(TEST_FILE_ID))
        
        # Check that fs.files was updated
        self.mock_db.fs.files.update_one.assert_called_once()
        
        # Check that the result is True (success)
            self.assertTrue(result)
    

if __name__ == "__main__":
    unittest.main() 