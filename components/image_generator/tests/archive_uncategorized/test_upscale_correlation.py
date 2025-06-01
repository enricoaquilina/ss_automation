#!/usr/bin/env python3
"""
Test upscale correlation between grid images and their upscaled variants.

This test verifies that upscaled images are correctly matched to their parent grid images
and not erroneously matched with upscales from previous generations.

Tests included:
1. Timestamp-based correlation - Upscales are matched to grids with the same timestamp
2. Prompt-based correlation - Upscales contain the same prompt text as their parent grid
3. Message ID correlation - Upscales reference their parent grid message ID
4. Multiple generation separation - Upscales from different generations don't get mixed
"""

import os
import sys
import json
import time
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import logging

# Add the parent directory to sys.path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules we want to test
from src.client import MidjourneyClient

# Configure logger
logger = logging.getLogger("test_upscale_correlation")

# Test fixtures
@pytest.fixture
def mock_client():
    """Create a mock MidjourneyClient for testing"""
    client = MagicMock(spec=MidjourneyClient)
    client._fallback_get_upscale_result = AsyncMock()
    client.upscale_futures = {}
    client.matched_message_ids = set()
    client.last_interaction_time = time.time()
    client.current_generation_prompt = "test prompt for correlation"
    client.current_grid_message_id = "test_grid_message_id"
    client.upscale_grid_mapping = {}
    return client

@pytest.fixture
def mock_grid_message():
    """Mock grid message data"""
    return {
        "id": "test_grid_message_id",
        "content": "**test prompt for correlation** - <@123456> (fast)",
        "timestamp": datetime.now().isoformat(),
        "attachments": [
            {"url": "https://example.com/grid.png"}
        ]
    }

@pytest.fixture
def mock_upscale_messages():
    """Mock upscale message data"""
    now = datetime.now().isoformat()
    return [
        # Valid upscale for the current prompt, recent timestamp
        {
            "id": "upscale_1_id",
            "content": "**test prompt for correlation** - Image #1 (fast)",
            "timestamp": now,
            "attachments": [
                {"url": "https://example.com/upscale1.png"}
            ]
        },
        # Valid upscale but old timestamp (from previous generation)
        {
            "id": "old_upscale_id",
            "content": "**test prompt for correlation** - Image #2 (fast)",
            "timestamp": "2023-01-01T00:00:00",
            "attachments": [
                {"url": "https://example.com/old_upscale.png"}
            ]
        },
        # Invalid upscale (different prompt)
        {
            "id": "different_prompt_id",
            "content": "**completely different prompt** - Image #3 (fast)",
            "timestamp": now,
            "attachments": [
                {"url": "https://example.com/different_prompt.png"}
            ]
        },
        # Not an upscale message
        {
            "id": "not_upscale_id",
            "content": "This is not an upscale message",
            "timestamp": now,
            "attachments": []
        }
    ]

class TestUpscaleCorrelation:
    """Test cases for upscale correlation with grid images"""
    
    @pytest.mark.asyncio
    async def test_timestamp_correlation(self, mock_client, mock_upscale_messages):
        """Test that upscales are correlated with grids using timestamps"""
        # Set up the client and patches
        current_time = time.time()
        mock_client.last_interaction_time = current_time
        
        # Set up the mocked _get_recent_messages to return our test messages
        mock_client._get_recent_messages = AsyncMock(return_value=mock_upscale_messages)
        
        # Set up a mocked _get_message_details to return our grid message
        mock_client._get_message_details = AsyncMock(return_value=None)
        
        # Use a time from an hour ago to simulate an old upscale
        old_time = current_time - 3600
        
        # Test with current time - should find the upscale
        result = await MidjourneyClient._fallback_get_upscale_result(mock_client, 1, current_time)
        assert result == "https://example.com/upscale1.png"
        
        # Reset matched message IDs
        mock_client.matched_message_ids = set()
        
        # Test with old time - should NOT find the upscale
        result = await MidjourneyClient._fallback_get_upscale_result(mock_client, 1, old_time)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_prompt_correlation(self, mock_client, mock_grid_message, mock_upscale_messages):
        """Test that upscales are correlated with grids based on prompt content"""
        # Set up the client and patches
        mock_client._get_recent_messages = AsyncMock(return_value=mock_upscale_messages)
        mock_client._get_message_details = AsyncMock(return_value=mock_grid_message)
        
        # Test with correct prompt - should find the upscale
        mock_client.current_generation_prompt = "test prompt for correlation"
        result = await MidjourneyClient._fallback_get_upscale_result(mock_client, 1)
        assert result == "https://example.com/upscale1.png"
        
        # Reset matched message IDs
        mock_client.matched_message_ids = set()
        
        # Test with different prompt - should NOT find the upscale
        mock_client.current_generation_prompt = "different prompt"
        result = await MidjourneyClient._fallback_get_upscale_result(mock_client, 3)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_grid_message_id_correlation(self, mock_client, mock_grid_message, mock_upscale_messages):
        """Test that upscales store references to their parent grid message ID"""
        # Set up the client and patches
        mock_client._get_recent_messages = AsyncMock(return_value=mock_upscale_messages)
        mock_client._get_message_details = AsyncMock(return_value=mock_grid_message)
        mock_client.current_grid_message_id = "test_grid_message_id"
        
        # Perform upscale detection
        result = await MidjourneyClient._fallback_get_upscale_result(mock_client, 1)
        assert result == "https://example.com/upscale1.png"
        
        # Verify that the upscale's grid message ID was stored in upscale_grid_mapping
        assert "upscale_1_id" in mock_client.upscale_grid_mapping
        assert mock_client.upscale_grid_mapping["upscale_1_id"]["grid_message_id"] == "test_grid_message_id"
        assert mock_client.upscale_grid_mapping["upscale_1_id"]["variant"] == 1
    
    @pytest.mark.asyncio
    async def test_message_id_tracking(self, mock_client, mock_upscale_messages):
        """Test that processed message IDs are tracked to avoid duplicates"""
        # Set up the client and patches
        mock_client._get_recent_messages = AsyncMock(return_value=mock_upscale_messages)
        
        # First call should process and track message IDs
        result1 = await MidjourneyClient._fallback_get_upscale_result(mock_client, 1)
        assert result1 == "https://example.com/upscale1.png"
        assert "upscale_1_id" in mock_client.matched_message_ids
        
        # Second call with same variant should not find anything as IDs are tracked
        result2 = await MidjourneyClient._fallback_get_upscale_result(mock_client, 1)
        assert result2 is None
    
    @pytest.mark.asyncio
    async def test_consolidated_metadata(self, mock_client, monkeypatch):
        """Test that consolidated metadata correctly links grid and upscales"""
        # This test requires filesystem operations, so we'll mock them
        mock_open = MagicMock()
        mock_dump = MagicMock()
        
        # Patch open and json.dump
        monkeypatch.setattr("builtins.open", mock_open)
        monkeypatch.setattr("json.dump", mock_dump)
        
        # Mock FileSystemStorage functions
        from src.storage import FileSystemStorage
        storage = FileSystemStorage(base_dir="test_output")
        
        # Mock the save_grid method to test consolidated metadata creation
        grid_metadata = {
            "prompt": "test prompt for correlation",
            "grid_message_id": "test_grid_message_id",
            "image_url": "https://example.com/grid.png"
        }
        
        # Run save_grid to create the base consolidated file
        await storage.save_grid(b"fake_image_data", grid_metadata)
        
        # Run save_upscale to update the consolidated file
        upscale_metadata = {
            "prompt": "test prompt for correlation",
            "grid_message_id": "test_grid_message_id",
            "variant": 1,
            "image_url": "https://example.com/upscale1.png"
        }
        
        await storage.save_upscale(b"fake_upscale_data", upscale_metadata)
        
        # Verify that json.dump was called to create/update consolidated files
        assert mock_dump.call_count >= 2

if __name__ == "__main__":
    # Run the tests
    pytest.main(["-xvs", "test_upscale_correlation.py"]) 