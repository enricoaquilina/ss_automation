#!/usr/bin/env python3
"""
Mock Midjourney Client for Testing

This module provides a mock implementation of the MidjourneyClient
for testing without making real API calls to Discord.
"""

import logging
import uuid
import asyncio
from typing import List, Optional, Dict, Any

# Configure logging
logger = logging.getLogger("mock_midjourney")

class GenerationResult:
    """Result of a generation operation"""
    def __init__(self, success=True, grid_message_id=None, image_url=None, error=None):
        self.success = success
        self.grid_message_id = grid_message_id
        self.image_url = image_url
        self.error = error

class UpscaleResult:
    """Result of an upscale operation"""
    def __init__(self, success=True, variant=0, image_url=None, error=None):
        self.success = success
        self.variant = variant
        self.image_url = image_url
        self.error = error

class MockMidjourneyClient:
    """Mock implementation of MidjourneyClient for testing"""
    
    def __init__(self, user_token: str, bot_token: str, channel_id: str, guild_id: str):
        """Initialize with mock data"""
        self.user_token = user_token
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.guild_id = guild_id
        
        # Mock internal structures
        self.user_gateway = MockGateway(user_token, is_bot=False)
        self.bot_gateway = MockGateway(bot_token, is_bot=True)
        
        # Tracking fields
        self.generation_future = None
        self.upscale_futures = {}
        self.current_generation_prompt = None
        self.current_upscale_variant = None
        self.seen_message_ids = set()
        self.matched_message_ids = set()
        
        logger.info("Initialized MockMidjourneyClient")
    
    async def initialize(self) -> bool:
        """Mock initialization"""
        logger.info("Initializing mock client")
        
        # Mock successful gateway connections
        await self.user_gateway.connect()
        await self.bot_gateway.connect()
        
        return True
    
    async def generate_image(self, prompt: str) -> GenerationResult:
        """Mock image generation"""
        logger.info(f"Mock generating image with prompt: {prompt}")
        
        # Store prompt
        self.current_generation_prompt = prompt
        
        # Generate mock data
        grid_id = f"mock_grid_{uuid.uuid4().hex[:8]}"
        image_url = f"https://example.com/mock/grid_{uuid.uuid4().hex[:8]}.png"
        
        return GenerationResult(
            success=True,
            grid_message_id=grid_id,
            image_url=image_url
        )
    
    async def upscale_all_variants(self, grid_message_id: str) -> List[UpscaleResult]:
        """Mock upscaling all variants"""
        logger.info(f"Mock upscaling all variants for grid: {grid_message_id}")
        
        results = []
        for variant in range(1, 5):
            # Generate a unique mock image URL for each variant
            image_url = f"https://example.com/mock/upscale_{variant}_{uuid.uuid4().hex[:8]}.png"
            
            results.append(UpscaleResult(
                success=True,
                variant=variant,
                image_url=image_url
            ))
        
        return results
    
    async def _get_message_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Mock getting message details"""
        logger.info(f"Mock getting message details for: {message_id}")
        
        return {
            "id": message_id,
            "content": "**Mock message**",
            "attachments": [{"url": f"https://example.com/mock/attachment_{uuid.uuid4().hex[:8]}.png"}],
            "components": [
                {
                    "type": 1,
                    "components": [
                        {"type": 2, "label": "U1", "custom_id": f"mock::u1::{uuid.uuid4().hex}"},
                        {"type": 2, "label": "U2", "custom_id": f"mock::u2::{uuid.uuid4().hex}"},
                        {"type": 2, "label": "U3", "custom_id": f"mock::u3::{uuid.uuid4().hex}"},
                        {"type": 2, "label": "U4", "custom_id": f"mock::u4::{uuid.uuid4().hex}"}
                    ]
                }
            ]
        }
    
    async def close(self):
        """Mock cleanup"""
        logger.info("Closing mock client")
        
        # Close gateways
        await self.user_gateway.close()
        await self.bot_gateway.close()
        
        # Clean up any pending futures
        if self.generation_future and not self.generation_future.done():
            self.generation_future.cancel()
        
        for variant, future in list(self.upscale_futures.items()):
            if not future.done():
                future.cancel()
        
        # Clear state
        self.upscale_futures.clear()
        self.current_generation_prompt = None
        self.current_upscale_variant = None
        self.seen_message_ids.clear()
        self.matched_message_ids.clear()


class MockGateway:
    """Mock implementation of DiscordGateway"""
    
    def __init__(self, token: str, is_bot: bool = False):
        """Initialize with token"""
        self.token = token
        self.is_bot = is_bot
        self.session_id = None
        self.connected = asyncio.Event()
        self.message_handlers = []
        self._closed = False
    
    async def connect(self) -> bool:
        """Mock connecting to gateway"""
        logger.info(f"Mock connecting to gateway with {'bot' if self.is_bot else 'user'} token")
        
        # Generate a mock session ID
        self.session_id = f"mock_session_{uuid.uuid4().hex}"
        
        # Set connected flag
        self.connected.set()
        
        # Run handler processing
        for handler in list(self.message_handlers):
            await handler({"t": "READY", "d": {"session_id": self.session_id}})
        
        return True
    
    async def close(self):
        """Mock closing connection"""
        logger.info("Mock closing gateway connection")
        
        self._closed = True
        self.connected.clear()
        self.message_handlers.clear()
    
    def register_handler(self, handler):
        """Register a message handler"""
        self.message_handlers.append(handler)
    
    def unregister_handler(self, handler):
        """Unregister a message handler"""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler) 