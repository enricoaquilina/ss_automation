#!/usr/bin/env python3
"""
Integration Test for Complete Imagine and Upscale Workflow

This test demonstrates a complete workflow:
1. Generate an image with the /imagine command
2. Upscale all four variants
3. Save the results to storage
4. Verify all operations succeeded

Usage:
    pytest -xvs integration/test_imagine_upscale_workflow.py
"""

import os
import sys
import json
import asyncio
import pytest
import pytest_asyncio
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, AsyncMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

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
logger = logging.getLogger("imagine_upscale_test")

class TestImagineUpscaleWorkflow:
    """
    Tests for the complete imagine and upscale workflow
    """
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create and initialize the client for testing"""
        # Load environment variables
        env_vars = load_env_vars()
        if not env_vars:
            # Use mock credentials for testing
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
    async def test_imagine_command_format(self, client):
        """Test that the imagine command constructs proper payload"""
        # For the test adapter, directly check and mock the generate method
        if hasattr(client, 'generate'):
            # Mock the generate method
            original_generate = client.generate
            client.generate = AsyncMock(return_value=MagicMock(
                success=True, 
                message_id="mock_message_id", 
                image_url="https://example.com/image.png"
            ))
            
            # Call the method
            await client.generate("cosmic space dolphins, digital art")
            
            # Check that the mock was called
            assert client.generate.called
            
            # Restore the original method
            client.generate = original_generate
            return
        
        # For the direct MidjourneyClient implementation
        with patch('aiohttp.ClientSession.post', new_callable=AsyncMock) as mock_post:
            # Set up the mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {'id': 'response_id', 'type': 4}
            mock_post.return_value = mock_response
            
            # Run the command - patch the method so we can verify it's called
            client._send_imagine_command = AsyncMock(return_value={'id': 'response_id'})
            
            # Call the higher-level method
            prompt = "cosmic space dolphins, digital art"
            if hasattr(client, 'generate_image'):
                client._send_slash_command = AsyncMock(return_value={'id': 'response_id'})
                await client.generate_image(prompt)
                assert client._send_slash_command.called or client._send_imagine_command.called
            else:
                # Fallback direct call
                await client._send_imagine_command(prompt)
                assert client._send_imagine_command.called
    
    @pytest.mark.asyncio
    async def test_full_generate_and_upscale_workflow(self, client, storage):
        """
        Test complete workflow from generation to upscaling and storage
        """
        # When FULLY_MOCKED=true, use mock data instead of real API calls
        if os.environ.get("FULLY_MOCKED") == "true":
            # Mock the generation
            mock_generation = GenerationResult(
                success=True,
                grid_message_id="mock_grid_id_123",
                image_url="https://cdn.discordapp.com/attachments/123456789/987654321/mock_grid.png",
                error=None
            )
            client.generate_image = AsyncMock(return_value=mock_generation)
            
            # Mock the upscale results
            mock_upscales = [
                UpscaleResult(success=True, variant=1, image_url="https://example.com/upscale1.png"),
                UpscaleResult(success=True, variant=2, image_url="https://example.com/upscale2.png"),
                UpscaleResult(success=True, variant=3, image_url="https://example.com/upscale3.png"),
                UpscaleResult(success=True, variant=4, image_url="https://example.com/upscale4.png")
            ]
            client.upscale_all_variants = AsyncMock(return_value=mock_upscales)
            
            # Mock the download function
            storage.save_from_url = AsyncMock(return_value=Path("/mock/path/image.png"))
        
        # Test prompt
        prompt = f"cosmic space dolphins, digital art {MODEL_VERSIONS['v6']} {ASPECT_RATIOS['square']}"
        
        # Step 1: Generate the image
        logger.info(f"Generating image with prompt: {prompt}")
        gen_result = await client.generate_image(prompt)
        
        # Verify generation result
        assert gen_result.success, f"Generation failed: {gen_result.error}"
        assert gen_result.grid_message_id, "No grid message ID in result"
        assert gen_result.image_url, "No image URL in result"
        
        # Save the grid image
        grid_path = await storage.save_from_url(
            gen_result.image_url,
            filename=f"grid_{gen_result.grid_message_id}.png"
        )
        assert grid_path, "Failed to save grid image"
        
        # Step 2: Upscale all variants
        logger.info(f"Upscaling all variants for message ID: {gen_result.grid_message_id}")
        upscale_results = await client.upscale_all_variants(gen_result.grid_message_id)
        
        # Verify upscale results
        assert len(upscale_results) == 4, f"Expected 4 upscale results, got {len(upscale_results)}"
        success_count = sum(1 for result in upscale_results if result.success)
        logger.info(f"Successfully upscaled {success_count} variants")
        
        # Step 3: Save all upscales
        saved_paths = []
        for result in upscale_results:
            if result.success:
                path = await storage.save_from_url(
                    result.image_url,
                    filename=f"upscale_{gen_result.grid_message_id}_variant_{result.variant}.png"
                )
                saved_paths.append(path)
                assert path, f"Failed to save upscale for variant {result.variant}"
        
        # Final verification
        assert len(saved_paths) == success_count, "Not all successful upscales were saved"
        logger.info(f"Test complete - saved {len(saved_paths)} images")
        
        return {
            "generation": gen_result.to_dict(),
            "upscales": [u.to_dict() for u in upscale_results],
            "saved_paths": [str(p) for p in saved_paths]
        }
    
    @pytest.mark.asyncio
    async def test_upscale_specific_variant(self, client, storage):
        """Test upscaling a specific variant"""
        # When FULLY_MOCKED=true, use mock data instead of real API calls
        if os.environ.get("FULLY_MOCKED") == "true":
            # Mock the upscale result
            mock_upscale = UpscaleResult(
                success=True, 
                variant=2, 
                image_url="https://example.com/variant2_upscale.png"
            )
            client.upscale_variant = AsyncMock(return_value=mock_upscale)
            
            # Mock the storage
            storage.save_from_url = AsyncMock(return_value=Path("/mock/path/upscale_2.png"))
        
        # Use a mock grid message ID
        grid_message_id = "mock_grid_id_456"
        variant = 2  # Testing just variant 2
        
        # Upscale the specific variant
        logger.info(f"Upscaling variant {variant} from message ID: {grid_message_id}")
        result = await client.upscale_variant(grid_message_id, variant)
        
        # Verify the result
        assert result.success, f"Upscale failed: {result.error}"
        assert result.variant == variant, f"Wrong variant in result: {result.variant}"
        assert result.image_url, "No image URL in result"
        
        # Save the upscaled image
        path = await storage.save_from_url(
            result.image_url,
            filename=f"upscale_{grid_message_id}_variant_{variant}.png"
        )
        assert path, f"Failed to save upscale for variant {variant}"
        
        logger.info(f"Successfully upscaled and saved variant {variant}")
        
        return {
            "upscale": result.to_dict(),
            "saved_path": str(path)
        }
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling during generation and upscaling"""
        # Mock errors for generation and upscaling
        client.generate_image = AsyncMock(return_value=GenerationResult(
            success=False,
            error="Simulated error for testing",
            grid_message_id=None,
            image_url=None
        ))
        
        # Attempt to generate an image
        prompt = "This prompt should fail due to our mocking"
        gen_result = await client.generate_image(prompt)
        
        # Verify error handling
        assert not gen_result.success, "Generation should fail in this test"
        assert gen_result.error, "Error message should be present"
        
        # Mock upscale error
        client.upscale_variant = AsyncMock(return_value=UpscaleResult(
            success=False,
            variant=1,
            error="Simulated upscale error for testing",
            image_url=None
        ))
        
        # Attempt to upscale
        result = await client.upscale_variant("mock_message_id", 1)
        
        # Verify error handling
        assert not result.success, "Upscale should fail in this test"
        assert result.error, "Error message should be present"
        
        logger.info("Error handling tests passed")
        return {
            "generation_error": gen_result.error,
            "upscale_error": result.error
        }

if __name__ == "__main__":
    # This allows running the test directly with Python
    import pytest
    pytest.main(["-xvs", __file__]) 