#!/usr/bin/env python3
"""
Test script to verify the integration of generate_and_upscale.py script.
This checks that the script properly chains method calls from prompt to generation to upscaling.

Usage:
    python test_generate_and_upscale.py
"""

import os
import sys
import asyncio
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

# Add parent directory to sys.path for importing from component package
current_dir = os.path.dirname(os.path.abspath(__file__))
component_dir = os.path.dirname(current_dir)
sys.path.insert(0, component_dir)

# Import generate_and_upscale
import generate_and_upscale
from src.models import GenerationResult, UpscaleResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("generate_upscale_test")

async def test_generate_and_upscale_script():
    """Test that the generate_and_upscale script properly chains method calls"""
    
    # Create a temporary directory for output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock environment variables
        env_vars = {
            "DISCORD_USER_TOKEN": "mock_user_token",
            "DISCORD_BOT_TOKEN": "mock_bot_token",
            "DISCORD_CHANNEL_ID": "123456789012345678",
            "DISCORD_GUILD_ID": "987654321098765432"
        }
        
        # Track method calls
        method_calls = {
            "initialize": False,
            "generate_image": False,
            "upscale_all_variants": False,
            "save_from_url": 0,
            "close": False
        }
        
        # Test prompt and mocked results
        test_prompt = "cosmic space dolphins, digital art --ar 16:9 --v 6"
        grid_message_id = "mock_grid_id_456"
        grid_image_url = "https://example.com/grid.png"
        
        # Mock the client and its methods
        with patch('generate_and_upscale.MidjourneyClient') as mock_client_class:
            # Create client instance mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock client.initialize
            mock_client.initialize = AsyncMock(return_value=True)
            
            # Mock client.generate_image
            mock_client.generate_image = AsyncMock(return_value=GenerationResult(
                success=True,
                grid_message_id=grid_message_id,
                image_url=grid_image_url
            ))
            
            # Mock client.upscale_all_variants
            mock_client.upscale_all_variants = AsyncMock(return_value=[
                UpscaleResult(success=True, variant=1, image_url="https://example.com/upscale1.png"),
                UpscaleResult(success=True, variant=2, image_url="https://example.com/upscale2.png"),
                UpscaleResult(success=True, variant=3, image_url="https://example.com/upscale3.png"),
                UpscaleResult(success=True, variant=4, image_url="https://example.com/upscale4.png")
            ])
            
            # Mock client.close
            mock_client.close = AsyncMock()
            
            # Mock the storage
            with patch('generate_and_upscale.FileSystemStorage') as mock_storage_class:
                # Create storage instance mock
                mock_storage = AsyncMock()
                mock_storage_class.return_value = mock_storage
                
                # Mock save_from_url method
                mock_storage.save_from_url = AsyncMock(side_effect=lambda url, filename: Path(f"{temp_dir}/{filename}"))
                
                # Mock the load_env_vars function
                with patch('generate_and_upscale.load_env_vars', return_value=env_vars):
                    # Run the generate_and_upscale function
                    result = await generate_and_upscale.generate_and_upscale(test_prompt, temp_dir)
                    
                    # Verify result
                    assert result["success"], "Result should indicate success"
                    assert result["prompt"] == test_prompt, "Prompt should match input"
                    assert result["grid_message_id"] == grid_message_id, "Grid message ID should match mock"
                    assert len(result["upscale_paths"]) == 4, "Should have 4 upscale paths"
                    
                    # Verify method calls
                    assert mock_client.initialize.called, "Client initialize method should be called"
                    assert mock_client.generate_image.called, "Client generate_image method should be called"
                    mock_client.generate_image.assert_called_with(test_prompt)
                    
                    assert mock_client.upscale_all_variants.called, "Client upscale_all_variants method should be called"
                    mock_client.upscale_all_variants.assert_called_with(grid_message_id)
                    
                    assert mock_storage.save_from_url.call_count == 5, "Should save 5 images (1 grid + 4 upscales)"
                    
                    assert mock_client.close.called, "Client close method should be called"
    
    logger.info("✅ All tests passed! generate_and_upscale script chains methods properly")
    return True

# Run the test
if __name__ == "__main__":
    asyncio.run(test_generate_and_upscale_script()) 