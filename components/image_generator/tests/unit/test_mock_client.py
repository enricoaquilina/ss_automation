#!/usr/bin/env python3
"""
Mock Client Tests

Tests the basic functionality using mock implementations
"""

import os
import sys
import uuid
import pytest
import logging
from unittest import mock
from pathlib import Path
import asyncio

# Add necessary paths
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Shared model classes for testing
class GenerationResult:
    def __init__(self, success=True, grid_message_id=None, image_url=None, error=None):
        self.success = success
        self.grid_message_id = grid_message_id
        self.image_url = image_url
        self.error = error

class UpscaleResult:
    def __init__(self, success=True, variant=0, image_url=None, error=None):
        self.success = success
        self.variant = variant
        self.image_url = image_url
        self.error = error

class MockMidjourneyClient:
    """Mock client for testing"""
    def __init__(self, user_token, bot_token, channel_id, guild_id):
        self.user_token = user_token
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.user_gateway = mock.MagicMock()
        self.user_gateway.session_id = f"mock_session_{uuid.uuid4().hex[:8]}"
        self.bot_gateway = mock.MagicMock()
        
    async def initialize(self):
        """Mock initialization"""
        return True
        
    async def generate_image(self, prompt):
        """Mock image generation"""
        # Generate mock data
        grid_id = f"mock_grid_{uuid.uuid4().hex[:8]}"
        image_url = "https://example.com/mock/grid.png"
        
        return GenerationResult(
            success=True,
            grid_message_id=grid_id,
            image_url=image_url
        )
        
    async def _get_message_details(self, message_id):
        """Mock get message details"""
        return {
            "id": message_id,
            "attachments": [{"url": "https://example.com/mock/grid.png"}],
            "components": [{"components": [{"label": "U1"}, {"label": "U2"}, {"label": "U3"}, {"label": "U4"}]}]
        }
        
    async def upscale_all_variants(self, grid_message_id):
        """Mock upscaling all variants"""
        results = []
        for variant in range(1, 5):
            results.append(UpscaleResult(
                success=True,
                variant=variant,
                image_url=f"https://example.com/mock/upscale_{variant}.png"
            ))
        return results
        
    async def close(self):
        """Mock close client"""
        return True


class TestMockClient:
    """Tests for the mock client implementation"""
    
    @pytest.mark.asyncio
    async def test_mock_client_generate(self):
        """Test image generation with mock client"""
        client = MockMidjourneyClient(
            user_token="mock_token",
            bot_token="mock_bot_token",
            channel_id="12345",
            guild_id="67890"
        )
        
        await client.initialize()
        
        # Generate an image
        result = await client.generate_image("Test prompt with landscape")
        
        assert result.success is True
        assert result.grid_message_id is not None
        assert result.image_url is not None
        
        await client.close()

    @pytest.mark.asyncio
    async def test_mock_client_upscale(self):
        """Test upscaling with mock client"""
        client = MockMidjourneyClient(
            user_token="mock_token",
            bot_token="mock_bot_token",
            channel_id="12345",
            guild_id="67890"
        )
        
        await client.initialize()
        
        # Test upscale
        grid_id = f"mock_grid_{uuid.uuid4().hex[:8]}"
        results = await client.upscale_all_variants(grid_id)
        
        assert len(results) == 4
        for i, result in enumerate(results, 1):
            assert result.success is True
            assert result.variant == i
            assert result.image_url is not None
        
        await client.close()

    def test_generation_result(self):
        """Test GenerationResult model"""
        result = GenerationResult(
            success=True,
            grid_message_id="123456",
            image_url="https://example.com/image.png"
        )
        
        assert result.success is True
        assert result.grid_message_id == "123456"
        assert result.image_url == "https://example.com/image.png"
        assert result.error is None
        
        # Test with error
        error_result = GenerationResult(
            success=False,
            error="Something went wrong"
        )
        
        assert error_result.success is False
        assert error_result.error == "Something went wrong"
        assert error_result.grid_message_id is None
        assert error_result.image_url is None


if __name__ == "__main__":
    pytest.main(["-v"]) 