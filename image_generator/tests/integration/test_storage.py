#!/usr/bin/env python3
"""
Integration tests for storage backends
"""

import os
import sys
import unittest
import tempfile
import shutil
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

# Import from the src directory
from src.storage import FileSystemStorage, GridFSStorage

# Skip GridFS tests if pymongo is not available
try:
    import pymongo
    from gridfs import GridFS
    from bson import ObjectId
    GRIDFS_AVAILABLE = True
except ImportError:
    GRIDFS_AVAILABLE = False


class TestFileSystemStorage(unittest.TestCase):
    """Integration tests for FileSystemStorage"""
    
    def setUp(self):
        """Set up the test environment"""
        # Create a temporary directory for test storage
        self.test_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(base_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up after the test"""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_save_grid(self):
        """Test saving a grid image to the filesystem"""
        # Create test data
        test_data = b"Test image data"
        test_metadata = {
            "prompt": "test prompt",
            "message_id": "test_message_id",
            "image_url": "https://example.com/image.png"
        }
        
        # Save grid image
        loop = asyncio.get_event_loop()
        grid_path = loop.run_until_complete(
            self.storage.save_grid(test_data, test_metadata)
        )
        
        # Check that the file was created
        self.assertTrue(os.path.exists(grid_path))
        
        # Check that the metadata file was created
        metadata_path = f"{grid_path}.meta.json"
        self.assertTrue(os.path.exists(metadata_path))
        
        # Check the file contents
        with open(grid_path, "rb") as f:
            saved_data = f.read()
        self.assertEqual(saved_data, test_data)
    
    def test_save_upscale(self):
        """Test saving an upscale image to the filesystem"""
        # Create test data
        test_data = b"Test upscale data"
        test_metadata = {
            "prompt": "test prompt",
            "variant": 2,
            "variation": "v6.0",
            "grid_message_id": "test_grid_message_id",
            "image_url": "https://example.com/upscale.png"
        }
        
        # Save upscale image
        loop = asyncio.get_event_loop()
        upscale_path = loop.run_until_complete(
            self.storage.save_upscale(test_data, test_metadata)
        )
        
        # Check that the file was created
        self.assertTrue(os.path.exists(upscale_path))
        
        # Check that the metadata file was created
        metadata_path = f"{upscale_path}.meta.json"
        self.assertTrue(os.path.exists(metadata_path))
        
        # Check the file contents
        with open(upscale_path, "rb") as f:
            saved_data = f.read()
        self.assertEqual(saved_data, test_data)


@unittest.skipIf(not GRIDFS_AVAILABLE, "GridFS not available")
class TestGridFSStorageMock(unittest.TestCase):
    """Integration tests for GridFSStorage with mocks"""
    
    def setUp(self):
        """Set up the test environment with mocks"""
        # Create mock objects and IDs
        self.mock_file_id = ObjectId("507f1f77bcf86cd799439012")
        self.mock_post_id = "507f1f77bcf86cd799439011"  # Valid ObjectId string
        
        # Set up MongoDB client mock
        self.patcher_mongo_client = patch('pymongo.MongoClient')
        self.mock_mongo_client = self.patcher_mongo_client.start()
        
        # Configure nested mocks for database operations
        self.mock_db = MagicMock()
        self.mock_fs = MagicMock()
        self.mock_files_collection = MagicMock()
        self.mock_post_images = MagicMock()
        self.mock_posts = MagicMock()
        
        # Set up the mock chain
        self.mock_mongo_client.return_value = self.mock_mongo_client
        self.mock_mongo_client.__getitem__.return_value = self.mock_db
        self.mock_db.fs = self.mock_fs
        self.mock_db.fs.files = self.mock_files_collection
        self.mock_db.post_images = self.mock_post_images
        self.mock_db.posts = self.mock_posts
        
        # Configure mock return values
        self.mock_fs.put.return_value = self.mock_file_id
        self.mock_fs.exists.return_value = True
        self.mock_fs.get.return_value.read.return_value = b"Test data from GridFS"
        
        # For update operations
        update_result = MagicMock()
        update_result.modified_count = 1
        update_result.upserted_id = None
        self.mock_post_images.update_one.return_value = update_result
        self.mock_posts.update_one.return_value = update_result
        self.mock_files_collection.update_one.return_value = update_result
        
        # Create the storage instance (it will use our mocked MongoClient)
        self.storage = GridFSStorage(
            mongodb_uri="mongodb://mock_server:27017",
            db_name="mock_db",
            post_id=self.mock_post_id
        )
        
        # Replace the object's attributes with our mocks
        self.storage.db = self.mock_db
        self.storage.fs = self.mock_fs
        self.storage.client = self.mock_mongo_client
    
    def tearDown(self):
        """Clean up the patches"""
        self.patcher_mongo_client.stop()
    
    def test_save_grid(self):
        """Test saving a grid image to GridFS"""
        # Create test data
        test_data = b"Test image data"
        test_metadata = {
            "prompt": "test prompt",
            "message_id": "test_message_id",
            "image_url": "https://example.com/image.png"
        }
        
        # Save grid image
        loop = asyncio.get_event_loop()
        file_id = loop.run_until_complete(
            self.storage.save_grid(test_data, test_metadata)
        )
        
        # Check that GridFS.put was called with the right data
        self.mock_fs.put.assert_called_once()
        args, kwargs = self.mock_fs.put.call_args
        self.assertEqual(args[0], test_data)
        self.assertEqual(kwargs['contentType'], 'image/png')
        self.assertEqual(kwargs['metadata']['prompt'], 'test prompt')
        self.assertEqual(kwargs['metadata']['is_grid'], True)
        
        # Check that post_images.update_one was called
        self.mock_post_images.update_one.assert_called_once()
        args, kwargs = self.mock_post_images.update_one.call_args
        self.assertEqual(args[0], {"post_id": ObjectId(self.mock_post_id)})
        self.assertIn("$push", args[1])
        self.assertIn("generations", args[1]["$push"])
        
        # Check that the file ID was returned
        self.assertEqual(file_id, str(self.mock_file_id))
    
    def test_save_upscale(self):
        """Test saving an upscale image to GridFS"""
        # Create test data
        test_data = b"Test upscale data"
        test_metadata = {
            "prompt": "test prompt",
            "variant": 2,
            "grid_message_id": "test_grid_message_id",
            "image_url": "https://example.com/upscale.png"
        }
        
        # Save upscale image
        loop = asyncio.get_event_loop()
        file_id = loop.run_until_complete(
            self.storage.save_upscale(test_data, test_metadata)
        )
        
        # Check that GridFS.put was called with the right data
        self.mock_fs.put.assert_called_once()
        args, kwargs = self.mock_fs.put.call_args
        self.assertEqual(args[0], test_data)
        self.assertEqual(kwargs['contentType'], 'image/png')
        self.assertEqual(kwargs['metadata']['prompt'], 'test prompt')
        self.assertEqual(kwargs['metadata']['is_grid'], False)
        self.assertEqual(kwargs['metadata']['is_upscale'], True)
        self.assertEqual(kwargs['metadata']['variant_idx'], 2)
        
        # Check that post_images.update_one was called
        self.mock_post_images.update_one.assert_called_once()
        
        # Check that posts.update_one was called
        self.mock_posts.update_one.assert_called_once()
        args, kwargs = self.mock_posts.update_one.call_args
        self.assertEqual(args[0], {"_id": ObjectId(self.mock_post_id)})
        self.assertIn("$push", args[1])
        self.assertIn("upscales", args[1]["$push"])
        
        # Check that the file ID was returned
        self.assertEqual(file_id, str(self.mock_file_id))
    
    def test_get_image(self):
        """Test retrieving an image from GridFS"""
        # Get the image
        image_data = self.storage.get_image(str(self.mock_file_id))
        
        # Check that fs.get was called
        self.mock_fs.get.assert_called_once_with(self.mock_file_id)
        
        # Check that we got the expected data
        self.assertEqual(image_data, b"Test data from GridFS")
    
    def test_save_metadata(self):
        """Test saving metadata for an image"""
        # Create test metadata
        test_metadata = {
            "prompt": "test prompt",
            "message_id": "test_message_id",
            "image_url": "https://example.com/image.png"
        }
        
        # Save metadata
        result = self.storage.save_metadata(test_metadata, str(self.mock_file_id))
        
        # Check that fs.files.update_one was called
        self.mock_files_collection.update_one.assert_called_once()
        args, kwargs = self.mock_files_collection.update_one.call_args
        self.assertEqual(args[0], {"_id": self.mock_file_id})
        self.assertIn("$set", args[1])
        self.assertEqual(args[1]["$set"]["metadata"], test_metadata)
        
        # Check that the operation was successful
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main() 