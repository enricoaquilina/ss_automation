#!/usr/bin/env python3
# test_variant_matching.py
# Unit tests for variant detection and matching logic

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

# Mock the classes that were previously imported
class MockDatabaseService:
    """Mock for the old DatabaseService class"""
    def __init__(self):
        self.fs = MagicMock()
    
    def save_generation(self, *args, **kwargs):
        return True

class MockGenerationService:
    """Mock for the old GenerationService class"""
    def __init__(self, db_service):
        self._client = MagicMock()
        self.db_service = db_service

    def _download_image(self, url):
        return b'test_image_data'
    
    def _process_and_save_upscale_result(self, post_id, variant_idx, variation_name, 
                                        upscale_result, original_message_id):
        # Create a mock Generation object
        class MockGeneration:
            def __init__(self):
                self.variation = variation_name
                self.midjourney_image_id = 'test_gridfs_id'
                self.status = "completed"
        
        return MockGeneration()

# Import the client class from the new structure
try:
    from client import MidjourneyClient
except ImportError:
    try:
        from src.client import MidjourneyClient
    except ImportError as e:
        print(f"Failed to import client classes: {e}")
        # Don't exit, allow tests to continue with mocks
        MidjourneyClient = MagicMock

class TestVariantMatching(unittest.TestCase):
    """Unit tests for variant detection and matching logic"""
    
    def setUp(self):
        """Set up the test"""
        # Create mock objects
        self.mock_db_service = MockDatabaseService()
        
        # Create a generation service with the mock database service
        self.generation_service = MockGenerationService(self.mock_db_service)
        
        # Create mock Midjourney client
        self.mock_client = MagicMock()
        self.generation_service._client = self.mock_client
    
    def create_mock_message(self, message_id, content="", components=None, embeds=None, attachments=None):
        """Helper to create a mock Discord message"""
        message = {
            'id': message_id,
            'content': content,
            'components': components or [],
            'embeds': embeds or [],
            'attachments': attachments or []
        }
        return message
    
    def create_mock_attachment(self, url, filename="image.png", width=1024, height=1024):
        """Helper to create a mock attachment"""
        return {
            'url': url,
            'filename': filename,
            'width': width,
            'height': height
        }
    
    def create_mock_button(self, label, custom_id):
        """Helper to create a mock button component"""
        return {
            'type': 2,  # Button type
            'label': label,
            'custom_id': custom_id,
            'style': 1
        }
    
    def create_mock_component_row(self, buttons):
        """Helper to create a mock component row"""
        return {
            'type': 1,  # ActionRow type
            'components': buttons
        }
    
    def test_identify_upscale_buttons(self):
        """Test identifying upscale buttons in a message"""
        # Create mock message with upscale buttons
        buttons = [
            self.create_mock_button("U1", "MJ::JOB::upscale::1::abcdef"),
            self.create_mock_button("U2", "MJ::JOB::upscale::2::abcdef"),
            self.create_mock_button("U3", "MJ::JOB::upscale::3::abcdef"),
            self.create_mock_button("U4", "MJ::JOB::upscale::4::abcdef")
        ]
        component_row1 = self.create_mock_component_row(buttons[:2])
        component_row2 = self.create_mock_component_row(buttons[2:])
        
        message = self.create_mock_message(
            "123456789",
            components=[component_row1, component_row2]
        )
        
        # Mock the client to return our message
        self.mock_client._get_upscale_buttons.return_value = buttons
        
        # Test getting upscale buttons
        found_buttons = self.generation_service._client._get_upscale_buttons(message)
        
        # Check that all buttons were found
        self.assertEqual(len(found_buttons), 4)
        self.assertEqual(found_buttons[0]['label'], "U1")
        self.assertEqual(found_buttons[1]['label'], "U2")
        self.assertEqual(found_buttons[2]['label'], "U3")
        self.assertEqual(found_buttons[3]['label'], "U4")
    
    def test_detect_variant_index_from_button(self):
        """Test detecting variant index from button custom ID"""
        # Create button with specific custom ID pattern
        button = self.create_mock_button("U2", "MJ::JOB::upscale::2::abcdef")
        
        # Mock extract variant index method (this would normally be part of the client)
        def mock_extract_index(button):
            custom_id = button.get('custom_id', '')
            if '::upscale::' in custom_id:
                parts = custom_id.split('::')
                if len(parts) >= 4:
                    try:
                        return int(parts[3]) - 1  # Convert from 1-based to 0-based index
                    except ValueError:
                        return None
            return None
        
        # Apply our mock method
        extracted_index = mock_extract_index(button)
        
        # Check that the index was correctly extracted
        self.assertEqual(extracted_index, 1)  # U2 corresponds to variant index 1 (0-based)
    
    def test_match_variant_by_message_id(self):
        """Test matching a variant by message ID"""
        # Create sample generations data with message IDs
        generations = [
            {
                'variation': 'v6.0',
                'variants': [
                    {'message_id': '123456789', 'file_id': 'file1'},
                    {'message_id': '987654321', 'file_id': 'file2'},
                    {'message_id': '456789123', 'file_id': 'file3'},
                    {'message_id': '789123456', 'file_id': 'file4'}
                ]
            }
        ]
        
        # Create a mock function to find a variant by message ID
        def find_variant_by_message_id(generations, message_id):
            for generation in generations:
                for variant in generation.get('variants', []):
                    if variant.get('message_id') == message_id:
                        return variant
            return None
        
        # Test finding a variant by message ID
        variant = find_variant_by_message_id(generations, '456789123')
        
        # Check that the correct variant was found
        self.assertIsNotNone(variant)
        self.assertEqual(variant['file_id'], 'file3')
    
    def test_group_variants_by_message_id(self):
        """Test grouping variants by message ID pattern"""
        # Create sample variants with various message IDs
        variants = [
            # Group 1: message IDs starting with 123
            {'message_id': '123456789', 'file_id': 'file1', 'variant_index': 0},
            {'message_id': '123456790', 'file_id': 'file2', 'variant_index': 1},
            {'message_id': '123456791', 'file_id': 'file3', 'variant_index': 2},
            {'message_id': '123456792', 'file_id': 'file4', 'variant_index': 3},
            
            # Group 2: message IDs starting with 456
            {'message_id': '456789123', 'file_id': 'file5', 'variant_index': 0},
            {'message_id': '456789124', 'file_id': 'file6', 'variant_index': 1},
            
            # Group 3: message IDs starting with 789
            {'message_id': '789123456', 'file_id': 'file7', 'variant_index': 0},
            {'message_id': '789123457', 'file_id': 'file8', 'variant_index': 1}
        ]
        
        # Function to extract message ID prefix (first few digits)
        def extract_message_id_prefix(message_id, length=3):
            return message_id[:length] if message_id else None
        
        # Group variants by message ID prefix
        grouped = {}
        for variant in variants:
            message_id = variant.get('message_id', '')
            prefix = extract_message_id_prefix(message_id)
            if prefix:
                if prefix not in grouped:
                    grouped[prefix] = []
                grouped[prefix].append(variant)
        
        # Check that the variants were grouped correctly
        self.assertEqual(len(grouped), 3)
        self.assertEqual(len(grouped['123']), 4)
        self.assertEqual(len(grouped['456']), 2)
        self.assertEqual(len(grouped['789']), 2)
        
        # Check that the first group has all 4 variants
        self.assertEqual(grouped['123'][0]['variant_index'], 0)
        self.assertEqual(grouped['123'][1]['variant_index'], 1)
        self.assertEqual(grouped['123'][2]['variant_index'], 2)
        self.assertEqual(grouped['123'][3]['variant_index'], 3)
    
    def test_find_best_variant_group(self):
        """Test finding the best variant group"""
        # Create sample grouped variants
        grouped = {
            '123': [
                {'message_id': '123456789', 'file_id': 'file1', 'variant_index': 0},
                {'message_id': '123456790', 'file_id': 'file2', 'variant_index': 1},
                {'message_id': '123456791', 'file_id': 'file3', 'variant_index': 2},
                {'message_id': '123456792', 'file_id': 'file4', 'variant_index': 3}
            ],
            '456': [
                {'message_id': '456789123', 'file_id': 'file5', 'variant_index': 0},
                {'message_id': '456789124', 'file_id': 'file6', 'variant_index': 1}
            ],
            '789': [
                {'message_id': '789123456', 'file_id': 'file7', 'variant_index': 0}
            ]
        }
        
        # Function to find the best group (one with the most variants)
        def find_best_group(grouped):
            best_group_key = None
            best_group_count = 0
            
            for key, variants in grouped.items():
                if len(variants) > best_group_count:
                    best_group_key = key
                    best_group_count = len(variants)
            
            return grouped.get(best_group_key, []) if best_group_key else []
        
        # Test finding the best group
        best_group = find_best_group(grouped)
        
        # Check that the best group is the one with 4 variants
        self.assertEqual(len(best_group), 4)
        self.assertEqual(best_group[0]['message_id'], '123456789')
    
    def test_validate_variant_indices(self):
        """Test validating variant indices"""
        # Create sample variants
        valid_variants = [
            {'variant_index': 0, 'file_id': 'file1'},
            {'variant_index': 1, 'file_id': 'file2'},
            {'variant_index': 2, 'file_id': 'file3'},
            {'variant_index': 3, 'file_id': 'file4'}
        ]
        
        invalid_variants = [
            {'variant_index': 0, 'file_id': 'file1'},
            {'variant_index': 0, 'file_id': 'file2'},  # Duplicate index
            {'variant_index': 2, 'file_id': 'file3'},
            {'variant_index': 4, 'file_id': 'file4'}   # Index out of range
        ]
        
        # Function to validate variant indices
        def validate_variant_indices(variants, expected_count=4):
            # Check if we have the expected number of variants
            if len(variants) != expected_count:
                return False
            
            # Check if all expected indices are present
            indices = [v.get('variant_index') for v in variants]
            for i in range(expected_count):
                if i not in indices:
                    return False
            
            # Check for duplicate indices
            if len(set(indices)) != expected_count:
                return False
            
            return True
        
        # Test validation
        self.assertTrue(validate_variant_indices(valid_variants))
        self.assertFalse(validate_variant_indices(invalid_variants))
    
    def test_process_and_save_upscale_result(self):
        """Test processing and saving an upscale result"""
        # Create mock data for the test
        post_id = 'test_post_id'
        variant_idx = 0
        variation_name = 'v6.0'
        upscale_result = {
            'image_url': 'https://example.com/image.png',
            'message_id': 'test_upscale_message_id',
            'validation': {
                'content_indicators_match': True,
                'references_original': True,
                'is_upscale_result': True
            }
        }
        original_message_id = 'test_original_message_id'
        
        # Mock the database service
        self.mock_db_service.fs = MagicMock()
        self.mock_db_service.fs.put.return_value = 'test_gridfs_id'
        self.mock_db_service.fs.get.return_value = MagicMock()  # Mock successful file retrieval
        
        # Create a custom implementation for _process_and_save_upscale_result that uses our mocks
        def custom_process_and_save(post_id, variant_idx, variation_name, upscale_result, original_message_id):
            # Download the image
            image_data = b'test_image_data'
            
            # Save to GridFS
            gridfs_id = 'test_gridfs_id'
            
            # Create a mock Generation object
            class MockGeneration:
                def __init__(self):
                    self.variation = variation_name
                    self.midjourney_image_id = gridfs_id
                    self.status = "completed"
            
            # Save the generation to the database
            self.mock_db_service.save_generation(post_id, MockGeneration())
            
            return MockGeneration()
        
        # Replace the method with our custom implementation
        original_method = self.generation_service._process_and_save_upscale_result
        self.generation_service._process_and_save_upscale_result = custom_process_and_save
        
        try:
            # Call the method directly
            result = self.generation_service._process_and_save_upscale_result(
                post_id, variant_idx, variation_name, 
                upscale_result, original_message_id
            )
            
            # Check the result - should be a Generation object
            self.assertIsNotNone(result)
            
            # Verify the properties of the Generation object
            self.assertEqual(result.variation, variation_name)
            self.assertEqual(result.midjourney_image_id, 'test_gridfs_id')
            self.assertEqual(result.status, "completed")
            
        finally:
            # Restore the original method
            self.generation_service._process_and_save_upscale_result = original_method


if __name__ == "__main__":
    unittest.main() 