"""
Mock adapter for Discord API testing

This module provides mocks and stubs for testing Discord API interactions
without making actual API calls.
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger("mock_discord")

class MockDiscordAdapter:
    """Mock adapter for Discord API testing"""
    
    def __init__(self):
        self.messages = []
        self.interaction_count = 0
        self.grid_message_id = None
        self.upscale_message_ids = []
        
    async def mock_send_imagine_command(self, prompt: str) -> Dict[str, Any]:
        """Mock sending an imagine command"""
        logger.info(f"MOCK: Sending imagine command with prompt: {prompt}")
        self.interaction_count += 1
        
        # Simulate successful command
        return {
            "status": 204,
            "success": True,
            "nonce": str(uuid.uuid4())
        }
    
    async def mock_get_grid_message(self) -> Dict[str, Any]:
        """Mock getting a grid message with upscale buttons"""
        logger.info("MOCK: Getting grid message")
        
        # Generate a mock message ID
        self.grid_message_id = f"mock_grid_{uuid.uuid4().hex[:8]}"
        
        # Create a mock grid message
        grid_message = {
            "id": self.grid_message_id,
            "content": f"**Test prompt** - <@12345> (fast)",
            "channel_id": "1125101062454513738",
            "author": {
                "id": "936929561302675456",  # Midjourney bot ID
                "username": "Midjourney Bot",
                "bot": True
            },
            "attachments": [
                {
                    "id": f"mock_attachment_{uuid.uuid4().hex[:8]}",
                    "filename": "grid.png",
                    "content_type": "image/png",
                    "size": 1024 * 1024,  # 1MB
                    "url": "https://picsum.photos/1024",
                    "proxy_url": "https://picsum.photos/1024"
                }
            ],
            "components": [
                {
                    "type": 1,  # Action row
                    "components": [
                        {
                            "type": 2,  # Button
                            "style": 2,
                            "label": "U1",
                            "custom_id": f"MJ::JOB::upsample::1::{uuid.uuid4().hex}"
                        },
                        {
                            "type": 2,  # Button
                            "style": 2,
                            "label": "U2",
                            "custom_id": f"MJ::JOB::upsample::2::{uuid.uuid4().hex}"
                        },
                        {
                            "type": 2,  # Button
                            "style": 2,
                            "label": "U3",
                            "custom_id": f"MJ::JOB::upsample::3::{uuid.uuid4().hex}"
                        },
                        {
                            "type": 2,  # Button
                            "style": 2,
                            "label": "U4",
                            "custom_id": f"MJ::JOB::upsample::4::{uuid.uuid4().hex}"
                        }
                    ]
                }
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return grid_message
    
    async def mock_upscale_variant(self, variant: int) -> Dict[str, Any]:
        """Mock upscaling a variant"""
        logger.info(f"MOCK: Upscaling variant {variant}")
        
        # Generate a mock message ID for the upscaled variant
        message_id = f"mock_upscale_{variant}_{uuid.uuid4().hex[:8]}"
        self.upscale_message_ids.append(message_id)
        
        # Create a mock upscale message
        upscale_message = {
            "id": message_id,
            "content": f"**Image #{variant}** - <@12345>",
            "channel_id": "1125101062454513738",
            "author": {
                "id": "936929561302675456",  # Midjourney bot ID
                "username": "Midjourney Bot",
                "bot": True
            },
            "attachments": [
                {
                    "id": f"mock_upscale_attachment_{uuid.uuid4().hex[:8]}",
                    "filename": f"upscale_{variant}.png",
                    "content_type": "image/png",
                    "size": 2 * 1024 * 1024,  # 2MB
                    "url": f"https://picsum.photos/seed/{variant}/1024/1024",
                    "proxy_url": f"https://picsum.photos/seed/{variant}/1024/1024"
                }
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return upscale_message
    
    async def mock_button_click(self, message_id: str, custom_id: str) -> Dict[str, Any]:
        """Mock clicking a button"""
        logger.info(f"MOCK: Clicking button with custom_id: {custom_id}")
        self.interaction_count += 1
        
        # Extract variant number from custom_id
        try:
            variant = int(custom_id.split("::")[3])
        except (IndexError, ValueError):
            variant = 1
        
        # Simulate successful button click
        return {
            "status": 204,
            "success": True,
            "variant": variant
        }
        
mock_adapter = MockDiscordAdapter() 