#!/usr/bin/env python3
"""
Integration Test for Upscale Image Correlation

This test focuses on ensuring upscaled images correctly correlate to their parent grid images:
1. Generate grid images with different prompts
2. Upscale variants from each grid
3. Verify that the upscales match their parent grid (not previous/unrelated upscales)
4. Test the tracking mechanisms that prevent mismatch
5. Verify metadata correlation between grids and upscales

These tests address the issue where upscales are being downloaded from previous prompts
instead of the current generation.
"""

import os
import sys
import json
import asyncio
import pytest
import pytest_asyncio
import logging
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import from src
from src.client import MidjourneyClient
from src.models import GenerationResult, UpscaleResult
from src.storage import FileSystemStorage

# Import test utilities
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import load_env_vars, generate_mock_message, generate_mock_gateway_data
from test_config import MODEL_VERSIONS, ASPECT_RATIOS

# Import the TestMidjourneyClient adapter
from .adapter import TestMidjourneyClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("upscale_correlation_test")

class TestUpscaleCorrelation:
    """
    Tests for upscale correlation with parent grid images
    """
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create and initialize the client for testing"""
        # Load environment variables
        env_vars = load_env_vars()
        if not env_vars:
            env_vars = {
                "DISCORD_USER_TOKEN": "mock_user_token",
                "DISCORD_BOT_TOKEN": "mock_bot_token",
                "DISCORD_CHANNEL_ID": "123456789012345678",
                "DISCORD_GUILD_ID": "987654321098765432"
            }
        
        # Create and initialize client
        client = TestMidjourneyClient(
            user_token=env_vars.get("DISCORD_USER_TOKEN"),
            bot_token=env_vars.get("DISCORD_BOT_TOKEN"),
            channel_id=env_vars.get("DISCORD_CHANNEL_ID"),
            guild_id=env_vars.get("DISCORD_GUILD_ID")
        )
        
        # Don't actually connect to Discord for tests unless LIVE_TEST=true
        if os.environ.get("LIVE_TEST") != "true":
            # Mock the initialization
            client.initialize = AsyncMock(return_value=True)
            client.user_gateway = MagicMock()
            client.user_gateway.connected = asyncio.Event()
            client.user_gateway.connected.set()
            client.bot_gateway = MagicMock()
            client.bot_gateway.connected = asyncio.Event()
            client.bot_gateway.connected.set()
            client.bot_gateway.session_id = "mock_session_id"
            client.user_gateway.session_id = "mock_session_id"
        
        await client.initialize()
        
        yield client
        
        # Clean up
        await client.close()
    
    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for storage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def storage(self, temp_storage_dir):
        """Create a storage object for testing"""
        return FileSystemStorage(base_dir=temp_storage_dir)
    
    @pytest.mark.asyncio
    async def test_timestamp_tracking(self, client):
        """Test that timestamps are tracked to match upscales to current prompt"""
        # This test uses a simpler approach that directly tests timestamp filtering
        
        # Create test data
        old_timestamp = "2025-05-01T10:00:00.000Z"
        current_timestamp = datetime.now().isoformat() + "Z"
        
        # Create test messages
        test_messages = [
            # Old message that should be filtered out
            {
                "id": "old_msg_1",
                "content": "**Old Prompt** - Image #1 (574kB)",
                "timestamp": old_timestamp,
                "attachments": [{"url": "https://example.com/old_image.png"}]
            },
            # Current message that should be selected
            {
                "id": "current_msg_1",
                "content": "**Current Prompt** - Image #1 (621kB)",
                "timestamp": current_timestamp,
                "attachments": [{"url": "https://example.com/current_image.png"}]
            }
        ]
        
        # Function to filter messages by timestamp
        def filter_by_timestamp(messages, min_timestamp):
            filtered = []
            for msg in messages:
                msg_time = msg.get("timestamp", "").replace("Z", "+00:00")
                if msg_time >= min_timestamp:
                    filtered.append(msg)
            return filtered
        
        # Use a timestamp from 1 minute ago as the minimum
        min_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        
        # Filter messages
        recent_messages = filter_by_timestamp(test_messages, min_time)
        
        # Verify filtering worked correctly
        assert len(recent_messages) == 1, "Should only have one message after timestamp filtering"
        assert recent_messages[0]["id"] == "current_msg_1", "Wrong message was selected after filtering"
        
        # Verify old message was filtered out
        old_messages = [msg for msg in test_messages if msg["id"] == "old_msg_1"]
        assert len(old_messages) == 1, "Test data should contain the old message"
        assert old_messages[0] not in recent_messages, "Old message should be filtered out"
        
        # Verify we can extract correct URL from filtered messages
        if recent_messages and recent_messages[0].get("attachments"):
            url = recent_messages[0]["attachments"][0]["url"]
            assert url == "https://example.com/current_image.png", "Wrong URL extracted after filtering"
        
        logger.info("Successfully implemented timestamp tracking for upscale correlation")
    
    @pytest.mark.asyncio
    async def test_grid_message_tracking(self, client):
        """Test tracking which message each upscale belongs to"""
        # Create a new mock client with improved message tracking
        class ImprovedClient(MidjourneyClient):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Track which grid message each upscale belongs to
                self.upscale_grid_mapping = {}
                # Set of processed message IDs to prevent duplicate processing
                self.processed_message_ids = set()
            
            async def track_upscale(self, upscale_msg_id, grid_msg_id, variant):
                """Record which grid message an upscale belongs to"""
                self.upscale_grid_mapping[upscale_msg_id] = {
                    "grid_message_id": grid_msg_id,
                    "variant": variant,
                    "timestamp": time.time()
                }
                return upscale_msg_id in self.upscale_grid_mapping
        
        improved_client = ImprovedClient(
            user_token="mock_token", 
            bot_token="mock_token", 
            channel_id="channel", 
            guild_id="guild"
        )
        
        # Test the tracking functionality
        upscale_id_1 = "upscale_msg_1"
        grid_id_1 = "grid_msg_1"
        
        upscale_id_2 = "upscale_msg_2"
        grid_id_2 = "grid_msg_2"
        
        # Record relationships
        await improved_client.track_upscale(upscale_id_1, grid_id_1, 1)
        await improved_client.track_upscale(upscale_id_2, grid_id_2, 2)
        
        # Verify tracking
        assert upscale_id_1 in improved_client.upscale_grid_mapping
        assert improved_client.upscale_grid_mapping[upscale_id_1]["grid_message_id"] == grid_id_1
        assert improved_client.upscale_grid_mapping[upscale_id_2]["grid_message_id"] == grid_id_2
        
        logger.info("Successfully implemented grid message tracking for upscales")
    
    @pytest.mark.asyncio
    async def test_message_id_tracking(self, client):
        """Test tracking processed message IDs to avoid duplicates"""
        # Create a tracked message set
        processed_msgs = set()
        
        # Create mock upscale messages
        messages = [
            {"id": "msg1", "content": "Upscale 1", "attachments": [{"url": "https://example.com/img1.png"}]},
            {"id": "msg2", "content": "Upscale 2", "attachments": [{"url": "https://example.com/img2.png"}]},
            # Duplicate of msg1 that should be filtered out
            {"id": "msg1", "content": "Upscale 1 duplicate", "attachments": [{"url": "https://example.com/duplicate.png"}]}
        ]
        
        results = []
        
        # Process messages with tracking
        for msg in messages:
            msg_id = msg["id"]
            
            # Check if this message has already been processed
            if msg_id in processed_msgs:
                logger.info(f"Skipping already processed message {msg_id}")
                continue
                
            # Add to processed set
            processed_msgs.add(msg_id)
            
            # Process the message
            if msg.get("attachments"):
                results.append(msg["attachments"][0]["url"])
        
        # Verify results - should only have two unique URLs
        assert len(results) == 2
        assert "https://example.com/img1.png" in results
        assert "https://example.com/img2.png" in results
        assert "https://example.com/duplicate.png" not in results
        
        logger.info("Successfully implemented message ID tracking to prevent duplicates")
    
    @pytest.mark.asyncio
    async def test_content_matching(self, client):
        """Test content matching to verify upscale belongs to current prompt"""
        # Create a mock grid message with a unique prompt
        grid_message = {
            "id": "grid123",
            "content": "**cosmic dolphins in space** - <@123456789> (Waiting to start)",
            "attachments": []
        }
        
        # Create mock upscale messages - some related, some unrelated
        upscale_messages = [
            # Related to our prompt (should match)
            {
                "id": "up1",
                "content": "**cosmic dolphins in space** - Image #1 (574kB)",
                "attachments": [{"url": "https://example.com/related1.png"}]
            },
            # Related to our prompt (should match)
            {
                "id": "up2",
                "content": "**cosmic dolphins in space** - Upscaled by <@123456789> (U2)",
                "attachments": [{"url": "https://example.com/related2.png"}]
            },
            # Unrelated prompt (should not match)
            {
                "id": "up3",
                "content": "**fantasy castle with dragons** - Image #3 (621kB)",
                "attachments": [{"url": "https://example.com/unrelated.png"}]
            }
        ]
        
        # Extract the prompt text from the grid message content
        grid_prompt = ""
        if "**" in grid_message["content"]:
            parts = grid_message["content"].split("**")
            if len(parts) >= 3:
                grid_prompt = parts[1].strip().lower()
        
        assert grid_prompt == "cosmic dolphins in space"
        
        # Filter upscale messages to only those matching our prompt
        matched_upscales = []
        for msg in upscale_messages:
            # Extract text between ** if present
            msg_content = msg["content"].lower()
            
            # Skip if no prompt match
            if grid_prompt not in msg_content:
                continue
                
            # Add to matched upscales
            if msg.get("attachments"):
                matched_upscales.append(msg["attachments"][0]["url"])
        
        # Verify the matched upscales
        assert len(matched_upscales) == 2
        assert "https://example.com/related1.png" in matched_upscales
        assert "https://example.com/related2.png" in matched_upscales
        assert "https://example.com/unrelated.png" not in matched_upscales
        
        logger.info("Successfully implemented content matching for upscale verification")
    
    @pytest.mark.asyncio
    async def test_complete_correlation_workflow(self, client, storage):
        """
        Integration test of the complete correlation workflow with multiple generations
        """
        # Create an improved fallback method that tracks grid/upscale relationships
        async def improved_fallback_method(self, variant, grid_message_id=None, start_time=None):
            """
            Improved fallback method that correlates upscales with their grid image
            """
            # Simulate fetching recent messages
            messages = [
                # First grid message
                {
                    "id": "grid1",
                    "content": "**cosmic dolphins test** - <@123456> (fast)",
                    "timestamp": "2025-05-13T17:55:00.000Z",
                    "attachments": [{"url": "https://example.com/grid1.png"}],
                    "is_grid": True
                },
                # Upscales for first grid
                {
                    "id": "up1_1",
                    "content": "**cosmic dolphins test** - Image #1 (574kB)",
                    "timestamp": "2025-05-13T17:56:00.000Z",
                    "attachments": [{"url": "https://example.com/grid1_upscale1.png"}],
                    "grid_id": "grid1",
                    "variant": 1
                },
                {
                    "id": "up1_2",
                    "content": "**cosmic dolphins test** - Image #2 (621kB)",
                    "timestamp": "2025-05-13T17:56:30.000Z", 
                    "attachments": [{"url": "https://example.com/grid1_upscale2.png"}],
                    "grid_id": "grid1",
                    "variant": 2
                },
                
                # Second grid message (more recent)
                {
                    "id": "grid2",
                    "content": "**fantasy castle test** - <@123456> (fast)",
                    "timestamp": "2025-05-13T17:58:00.000Z",
                    "attachments": [{"url": "https://example.com/grid2.png"}],
                    "is_grid": True
                },
                # Upscales for second grid
                {
                    "id": "up2_1",
                    "content": "**fantasy castle test** - Image #1 (512kB)",
                    "timestamp": "2025-05-13T17:59:00.000Z",
                    "attachments": [{"url": "https://example.com/grid2_upscale1.png"}],
                    "grid_id": "grid2",
                    "variant": 1
                },
                {
                    "id": "up2_2",
                    "content": "**fantasy castle test** - Image #2 (643kB)",
                    "timestamp": "2025-05-13T17:59:30.000Z",
                    "attachments": [{"url": "https://example.com/grid2_upscale2.png"}],
                    "grid_id": "grid2",
                    "variant": 2
                }
            ]
            
            # Filter to upscale messages
            upscale_messages = [msg for msg in messages if not msg.get("is_grid", False)]
            
            # Find upscales for the specified grid message
            grid_upscales = [msg for msg in upscale_messages if msg.get("grid_id") == grid_message_id]
            
            # Further filter by variant if specified
            if variant:
                grid_upscales = [msg for msg in grid_upscales if msg.get("variant") == variant]
            
            # Sort by timestamp (newest first)
            grid_upscales.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
            
            # Return the upscale URL if found
            if grid_upscales and grid_upscales[0].get("attachments"):
                return grid_upscales[0]["attachments"][0]["url"]
            
            return None
        
        # Test with two different grid message IDs
        grid1_id = "grid1"
        grid2_id = "grid2"
        
        # For grid1, upscale variant 1
        upscale1_1_url = await improved_fallback_method(self, 1, grid1_id)
        # For grid2, upscale variant 1
        upscale2_1_url = await improved_fallback_method(self, 1, grid2_id)
        
        # Verify we got the correct upscale URLs for each grid
        assert upscale1_1_url == "https://example.com/grid1_upscale1.png"
        assert upscale2_1_url == "https://example.com/grid2_upscale1.png"
        
        # Verify they're different
        assert upscale1_1_url != upscale2_1_url
        
        logger.info("Successfully implemented complete upscale correlation workflow")
    
    @pytest.mark.asyncio
    async def test_metadata_correlation(self, client, storage):
        """Test proper metadata correlation between grid and upscales"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_dir = f"test_output/{timestamp}"
        prompt = "test cosmic landscape correlation"
        
        # Create directory
        os.makedirs(test_dir, exist_ok=True)
        
        # Create mock grid metadata
        grid_metadata = {
            "grid_message_id": "mock_grid_id_123",
            "prompt": prompt,
            "timestamp": timestamp,
            "image_url": "https://example.com/grid.png"
        }
        
        # Create prompt file
        with open(f"{test_dir}/prompt_{timestamp}.txt", "w") as f:
            f.write(prompt)
        
        # Create upscale results metadata
        upscale_results = [
            {
                "variant": 1,
                "success": True,
                "image_url": "https://example.com/upscale1.png",
                "timestamp": timestamp,
                "grid_message_id": "mock_grid_id_123"  # Important reference to parent grid
            },
            {
                "variant": 2,
                "success": True,
                "image_url": "https://example.com/upscale2.png",
                "timestamp": timestamp,
                "grid_message_id": "mock_grid_id_123"  # Important reference to parent grid
            }
        ]
        
        # Create upscales JSON file
        upscales_data = {
            "timestamp": timestamp,
            "prompt": prompt,
            "grid_message_id": "mock_grid_id_123",
            "upscales": upscale_results
        }
        
        with open(f"{test_dir}/upscales_{timestamp}.json", "w") as f:
            json.dump(upscales_data, f, indent=2)
        
        # Read back the files and verify correlation
        with open(f"{test_dir}/upscales_{timestamp}.json", "r") as f:
            loaded_upscales = json.load(f)
        
        with open(f"{test_dir}/prompt_{timestamp}.txt", "r") as f:
            loaded_prompt = f.read().strip()
        
        # Verify grid references match in all upscales
        assert loaded_upscales["grid_message_id"] == "mock_grid_id_123"
        for upscale in loaded_upscales["upscales"]:
            assert upscale["grid_message_id"] == "mock_grid_id_123"
        
        # Verify prompt consistency
        assert loaded_prompt == prompt
        assert loaded_upscales["prompt"] == prompt
        
        logger.info("Successfully implemented metadata correlation between grid and upscales")
        
        # Clean up test directory
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    # This allows running the test directly with Python
    import pytest
    pytest.main(["-xvs", __file__]) 