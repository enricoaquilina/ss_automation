#!/usr/bin/env python3
"""
Adapter for Midjourney Client

This adapter provides compatibility between the test suite and the implementation.
"""

import sys
import os
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Add the src directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Import the MidjourneyClient class
from src.client import MidjourneyClient
from src.models import GenerationResult as OriginalGenerationResult

# Create a compatible GenerationResult for tests
@dataclass
class TestGenerationResult:
    """Compatible GenerationResult for tests"""
    success: bool
    message_id: Optional[str] = None
    image_url: Optional[str] = None
    error: Optional[str] = None
    variant: Optional[int] = None

class TestMidjourneyClient(MidjourneyClient):
    """
    Adapter class for testing that provides compatibility with the test suite.
    """
    
    async def generate(self, prompt: str) -> TestGenerationResult:
        """
        Generate an image using Midjourney's /imagine command.
        This is an adapter method that calls generate_image() to maintain test compatibility.
        
        Args:
            prompt: The prompt to generate an image with
            
        Returns:
            TestGenerationResult with success flag, message_id and image_url if successful
        """
        # Call the implementation method
        gen_result = await self.generate_image(prompt)
        
        # Create a compatible result for tests
        return TestGenerationResult(
            success=gen_result.success,
            message_id=gen_result.grid_message_id,  # Map grid_message_id to message_id for tests
            image_url=gen_result.image_url,
            error=gen_result.error
        ) 
    
    async def close(self):
        """
        Close the client connection.
        This is an adapter method to ensure test compatibility.
        In mock mode, this is a no-op since we mock the connections.
        In live mode, it calls the parent close method.
        
        Returns:
            None
        """
        if hasattr(self, 'user_gateway') and hasattr(self.user_gateway, 'close'):
            try:
                await self.user_gateway.close()
            except Exception as e:
                print(f"Error closing user gateway: {e}")
                
        if hasattr(self, 'bot_gateway') and hasattr(self.bot_gateway, 'close'):
            try:
                await self.bot_gateway.close()
            except Exception as e:
                print(f"Error closing bot gateway: {e}") 