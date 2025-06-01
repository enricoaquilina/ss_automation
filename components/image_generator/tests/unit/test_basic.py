#!/usr/bin/env python3
"""
Basic tests for the image_generator module

This script tests basic imports and functionality to verify
the module structure is correct.
"""

import os
import sys
import unittest

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

class TestBasicImports(unittest.TestCase):
    """Test basic imports and module initialization"""
    
    def test_import_client(self):
        """Test importing the client module"""
        try:
            from src.client import MidjourneyClient
            self.assertTrue(hasattr(MidjourneyClient, "__init__"))
            self.assertTrue(callable(MidjourneyClient.__init__))
        except ImportError as e:
            self.fail(f"Failed to import MidjourneyClient: {e}")
    
    def test_import_utils(self):
        """Test importing the utils module"""
        try:
            from src.utils import RateLimiter, MidjourneyError
            self.assertTrue(hasattr(RateLimiter, "__init__"))
            self.assertTrue(callable(RateLimiter.__init__))
            self.assertTrue(issubclass(MidjourneyError, Exception))
        except ImportError as e:
            self.fail(f"Failed to import utils: {e}")
    
    def test_import_storage(self):
        """Test importing the storage module"""
        try:
            from src.storage import FileSystemStorage, GridFSStorage
            self.assertTrue(hasattr(FileSystemStorage, "__init__"))
            self.assertTrue(callable(FileSystemStorage.__init__))
            self.assertTrue(hasattr(GridFSStorage, "__init__"))
            self.assertTrue(callable(GridFSStorage.__init__))
        except ImportError as e:
            self.fail(f"Failed to import storage: {e}")
    
    def test_import_models(self):
        """Test importing the models module"""
        try:
            from src.models import GenerationResult, UpscaleResult
            self.assertTrue(isinstance(GenerationResult(success=True, image_url="test"), GenerationResult))
            self.assertTrue(isinstance(UpscaleResult(success=True, image_url="test", variant=1), UpscaleResult))
        except ImportError as e:
            self.fail(f"Failed to import models: {e}")
    
    def test_client_methods_exist(self):
        """Test that main client methods exist"""
        try:
            from src.client import MidjourneyClient
            
            # Check for required methods
            client = MidjourneyClient(user_token="test", bot_token="test", channel_id="test", guild_id="test")
            self.assertTrue(hasattr(client, "initialize"))
            self.assertTrue(callable(client.initialize))
            self.assertTrue(hasattr(client, "generate_image"))
            self.assertTrue(callable(client.generate_image))
            self.assertTrue(hasattr(client, "upscale_variant"))
            self.assertTrue(callable(client.upscale_variant))
            
            # Add a close method if it doesn't exist
            if not hasattr(client, "close"):
                client.close = lambda: None
                
        except ImportError as e:
            self.fail(f"Failed to import MidjourneyClient: {e}")


if __name__ == "__main__":
    unittest.main() 