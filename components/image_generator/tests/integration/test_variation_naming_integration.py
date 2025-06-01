#!/usr/bin/env python3
"""
Integration tests for variation naming behavior.

These tests verify that different variations (v6.0, v6.1, niji) are correctly
handled and named throughout the entire image generation process.
"""

import os
import sys
import logging
import time
import json
import shutil
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv
import gridfs
import unittest

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Add project root to sys.path
sys.path.append('/mongodb/silicon_sentiments')

class VariationNamingIntegrationTest(unittest.TestCase):
    """Integration test for validating variation naming behavior"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests"""
        # Load environment variables
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
            '.env'
        )
        load_dotenv(env_path)
        
        # Connect to MongoDB
        uri = os.environ.get('MONGODB_URI')
        cls.client = MongoClient(uri)
        cls.db = cls.client['instagram_db']
        cls.fs = gridfs.GridFS(cls.db)
        
        # Define test post ID - use an existing post
        cls.post_id = '66b88b70b2979f6117b347f2'
        
        # Get image reference for the post
        post = cls.db.posts.find_one({'_id': ObjectId(cls.post_id)})
        if not post or 'image_ref' not in post:
            raise ValueError(f"Test post {cls.post_id} not found or has no image_ref")
        
        cls.image_ref = post['image_ref']
        
        # Output directory for downloaded files
        cls.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'data',
            'test_output',
            f"test_variations_{int(time.time())}"
        )
        os.makedirs(cls.output_dir, exist_ok=True)
        
        # Path to clean_and_reprocess.py script
        cls.script_path = "/home/enrico/clean_and_reprocess.py"
        
        # Make sure the script exists
        if not os.path.exists(cls.script_path):
            raise FileNotFoundError(f"Required script not found: {cls.script_path}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests are done"""
        # Clean up output directory
        if os.path.exists(cls.output_dir):
            shutil.rmtree(cls.output_dir)
        
        # Close MongoDB connection
        cls.client.close()
    
    def setUp(self):
        """Set up before each test"""
        # Clean existing data for the test post
        self.clean_post_data()
        
        # Create variation-specific directories
        for variation in ['v6.0', 'v6.1', 'niji']:
            var_dir = os.path.join(self.output_dir, variation)
            os.makedirs(var_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up after each test"""
        # Optionally clean up data after each test
        # self.clean_post_data()
        pass
    
    def clean_post_data(self) -> None:
        """Clean existing data for the test post"""
        logging.info(f"Cleaning existing data for post: {self.post_id}")
        
        # Delete GridFS files
        file_count = 0
        for file in self.db.fs.files.find({'metadata.post_id': self.post_id}):
            self.fs.delete(file['_id'])
            file_count += 1
        
        # Also check for files with post_id as ObjectId
        for file in self.db.fs.files.find({'metadata.post_id': ObjectId(self.post_id)}):
            self.fs.delete(file['_id'])
            file_count += 1
        
        logging.info(f"Deleted {file_count} files from GridFS")
        
        # Clean post_images document
        result = self.db.post_images.update_one(
            {'_id': self.image_ref},
            {
                '$set': {
                    'generations': [],
                    'updated_at': time.time()
                }
            }
        )
        
        logging.info(f"Cleaned generations in post_images document")
    
    def run_generation_for_variation(self, variation: str) -> bool:
        """Run image generation for a specific variation"""
        logging.info(f"Running generation for variation: {variation}")
        
        # Run the clean_and_reprocess.py script
        command = [
            "python3",
            self.script_path,
            self.post_id,
            f"--variation={variation}",
            "--clean=no",  # We already cleaned in setUp
            "--debug"
        ]
        
        try:
            # Execute the command as a subprocess
            result = subprocess.run(
                command,
                cwd="/mongodb/silicon_sentiments",
                capture_output=True,
                text=True,
                check=True,
                env=os.environ
            )
            
            # Log relevant output
            for line in result.stdout.splitlines():
                if any(keyword in line for keyword in [
                    "variation", "Saved", "GridFS", "Verifying", "Downloading"
                ]):
                    logging.info(f"GENERATION: {line.strip()}")
            
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running generation: {str(e)}")
            if e.stdout:
                logging.error(f"Stdout: {e.stdout}")
            if e.stderr:
                logging.error(f"Stderr: {e.stderr}")
            return False
    
    def check_gridfs_files(self, variation: str) -> Tuple[List[Dict], bool]:
        """Check GridFS files for the specified variation"""
        logging.info(f"Checking GridFS files for variation: {variation}")
        
        # Find files for this post with this variation
        files = list(self.db.fs.files.find({
            'metadata.post_id': self.post_id,
            'metadata.variation': variation
        }))
        
        # Also check with ObjectId
        obj_files = list(self.db.fs.files.find({
            'metadata.post_id': ObjectId(self.post_id),
            'metadata.variation': variation
        }))
        
        files.extend(obj_files)
        logging.info(f"Found {len(files)} files for variation {variation}")
        
        # Check if we have 4 variants (0-3)
        variants_found = set()
        for file in files:
            metadata = file.get('metadata', {})
            variant_idx = metadata.get('variant_idx')
            if variant_idx in [0, 1, 2, 3]:
                variants_found.add(variant_idx)
        
        all_variants_found = len(variants_found) == 4
        logging.info(f"Found variants: {sorted(variants_found)}, all variants found: {all_variants_found}")
        
        # Check filenames
        for file in files:
            filename = file.get('filename', '')
            if not filename.startswith(f"{variation}_variant_"):
                logging.error(f"Incorrect filename format: {filename}")
                return files, False
        
        return files, all_variants_found
    
    def check_post_images_document(self, variation: str) -> Tuple[List[Dict], bool]:
        """Check post_images document for the specified variation"""
        logging.info(f"Checking post_images document for variation: {variation}")
        
        # Get post_images document
        post_image = self.db.post_images.find_one({'_id': self.image_ref})
        if not post_image:
            logging.error(f"Post image document not found: {self.image_ref}")
            return [], False
        
        # Get generations with the specified variation
        generations = post_image.get('generations', [])
        variation_generations = [gen for gen in generations if gen.get('variation') == variation]
        
        logging.info(f"Found {len(variation_generations)} generations for variation {variation}")
        
        # Check if we have at least 4 generations (one for each variant)
        return variation_generations, len(variation_generations) >= 4
    
    def download_and_check_files(self, variation: str, gridfs_files: List[Dict]) -> bool:
        """Download files from GridFS and check their content"""
        logging.info(f"Downloading and checking files for variation: {variation}")
        
        output_var_dir = os.path.join(self.output_dir, variation)
        os.makedirs(output_var_dir, exist_ok=True)
        
        # Download each file
        success = True
        for file in gridfs_files:
            try:
                # Get file data from GridFS
                grid_file = self.fs.get(file['_id'])
                file_data = grid_file.read()
                
                # Create filename with consistent format
                metadata = file.get('metadata', {})
                variant_idx = metadata.get('variant_idx', 0)
                file_path = os.path.join(output_var_dir, f"{variation}_variant_{variant_idx}_{file['_id']}.jpg")
                
                # Save file
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                
                # Check file size
                file_size = os.path.getsize(file_path)
                if file_size < 100000:  # Basic sanity check, images should be larger than 100KB
                    logging.error(f"File too small: {file_path}, size: {file_size}")
                    success = False
                else:
                    logging.info(f"Downloaded file to {file_path}, size: {file_size}")
            except Exception as e:
                logging.error(f"Error downloading file {file['_id']}: {str(e)}")
                success = False
        
        return success
    
    @unittest.skip("Skip this test by default as it requires actual image generation which is slow and resource-intensive")
    def test_niji_variation(self):
        """Test niji variation naming"""
        variation = "niji"
        
        # Run generation
        success = self.run_generation_for_variation(variation)
        self.assertTrue(success, "Failed to run generation for niji variation")
        
        # Check GridFS files
        gridfs_files, all_variants = self.check_gridfs_files(variation)
        self.assertTrue(all_variants, "Not all variants found in GridFS for niji variation")
        self.assertTrue(len(gridfs_files) >= 4, "Not enough GridFS files found for niji variation")
        
        # Check post_images document
        generations, has_all_gens = self.check_post_images_document(variation)
        self.assertTrue(has_all_gens, "Not all generations found in post_images for niji variation")
        
        # Download and check files
        download_success = self.download_and_check_files(variation, gridfs_files)
        self.assertTrue(download_success, "Failed to download and verify niji files")
        
        # Verify filenames in GridFS
        for file in gridfs_files:
            filename = file.get('filename', '')
            self.assertTrue(filename.startswith(f"{variation}_variant_"), 
                           f"Incorrect filename format: {filename}")
            
            # Verify metadata
            metadata = file.get('metadata', {})
            self.assertEqual(metadata.get('variation'), variation, 
                            f"Incorrect variation in metadata: {metadata.get('variation')}")
    
    @unittest.skip("Skip this test by default as it requires actual image generation which is slow and resource-intensive")
    def test_v6_0_variation(self):
        """Test v6.0 variation naming"""
        variation = "v6.0"
        
        # Run generation
        success = self.run_generation_for_variation(variation)
        self.assertTrue(success, "Failed to run generation for v6.0 variation")
        
        # Check GridFS files
        gridfs_files, all_variants = self.check_gridfs_files(variation)
        self.assertTrue(all_variants, "Not all variants found in GridFS for v6.0 variation")
        self.assertTrue(len(gridfs_files) >= 4, "Not enough GridFS files found for v6.0 variation")
        
        # Check post_images document
        generations, has_all_gens = self.check_post_images_document(variation)
        self.assertTrue(has_all_gens, "Not all generations found in post_images for v6.0 variation")
        
        # Download and check files
        download_success = self.download_and_check_files(variation, gridfs_files)
        self.assertTrue(download_success, "Failed to download and verify v6.0 files")
        
        # Verify filenames in GridFS
        for file in gridfs_files:
            filename = file.get('filename', '')
            self.assertTrue(filename.startswith(f"{variation}_variant_"), 
                           f"Incorrect filename format: {filename}")
            
            # Verify metadata
            metadata = file.get('metadata', {})
            self.assertEqual(metadata.get('variation'), variation, 
                            f"Incorrect variation in metadata: {metadata.get('variation')}")
    
    @unittest.skip("Skip this test by default as it requires actual image generation which is slow and resource-intensive")
    def test_v6_1_variation(self):
        """Test v6.1 variation naming"""
        variation = "v6.1"
        
        # Run generation
        success = self.run_generation_for_variation(variation)
        self.assertTrue(success, "Failed to run generation for v6.1 variation")
        
        # Check GridFS files
        gridfs_files, all_variants = self.check_gridfs_files(variation)
        self.assertTrue(all_variants, "Not all variants found in GridFS for v6.1 variation")
        self.assertTrue(len(gridfs_files) >= 4, "Not enough GridFS files found for v6.1 variation")
        
        # Check post_images document
        generations, has_all_gens = self.check_post_images_document(variation)
        self.assertTrue(has_all_gens, "Not all generations found in post_images for v6.1 variation")
        
        # Download and check files
        download_success = self.download_and_check_files(variation, gridfs_files)
        self.assertTrue(download_success, "Failed to download and verify v6.1 files")
        
        # Verify filenames in GridFS
        for file in gridfs_files:
            filename = file.get('filename', '')
            self.assertTrue(filename.startswith(f"{variation}_variant_"), 
                           f"Incorrect filename format: {filename}")
            
            # Verify metadata
            metadata = file.get('metadata', {})
            self.assertEqual(metadata.get('variation'), variation, 
                            f"Incorrect variation in metadata: {metadata.get('variation')}")
    
    def test_verify_existing_files(self):
        """Test to verify existing files in GridFS have correct variation naming"""
        # Check for existing files with 'niji' variation
        niji_files = list(self.db.fs.files.find({'metadata.variation': 'niji'}))
        
        if niji_files:
            logging.info(f"Found {len(niji_files)} existing niji files in GridFS")
            
            # Verify filenames
            for file in niji_files:
                filename = file.get('filename', '')
                # Allow "midjourney_" prefix if it contains "_variant_" and metadata confirms niji
                is_valid_niji_filename = (filename.startswith("niji_variant_") or \
                                         (filename.startswith("midjourney_") and "_variant_" in filename))
                self.assertTrue(is_valid_niji_filename,
                              f"Incorrect filename format for niji file: {filename}")
                
                # Verify metadata
                metadata = file.get('metadata', {})
                self.assertEqual(metadata.get('variation'), 'niji', 
                               f"Incorrect variation in metadata: {metadata.get('variation')}")
        else:
            logging.warning("No existing niji files found in GridFS to verify")

if __name__ == "__main__":
    unittest.main() 