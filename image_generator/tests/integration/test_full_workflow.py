#!/usr/bin/env python3
"""
Integration test for complete generate_and_upscale workflow.

This test verifies that the generate_and_upscale script properly chains
method calls from prompt to generation to upscaling and saves results correctly.
"""

import os
import sys
import json
import pytest
import pytest_asyncio
import asyncio
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
component_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, component_dir)

# Import generate_and_upscale and models
import generate_and_upscale
from src.models import GenerationResult, UpscaleResult

class TestFullWorkflow:
    """Test complete generate and upscale workflow"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for test outputs"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Mock environment variables for testing"""
        env_vars = {
            "DISCORD_USER_TOKEN": "mock_user_token",
            "DISCORD_BOT_TOKEN": "mock_bot_token", 
            "DISCORD_CHANNEL_ID": "123456789012345678",
            "DISCORD_GUILD_ID": "987654321098765432"
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        return env_vars
    
    @pytest.mark.asyncio
    async def test_generate_and_upscale_workflow_chaining(self, mock_env_vars, temp_output_dir):
        """Test that the workflow properly chains method calls"""
        
        # Track method calls
        method_calls = {
            "initialize": False,
            "generate_image": False,
            "upscale_all_variants": False,
            "save_from_url": 0,
            "close": False
        }
        
        # Test data
        test_prompt = "cosmic space dolphins, digital art --ar 16:9 --v 6"
        grid_message_id = "mock_grid_id_456"
        grid_image_url = "https://example.com/grid.png"
        
        with patch('generate_and_upscale.MidjourneyClient') as mock_client_class, \
             patch('generate_and_upscale.FileSystemStorage') as mock_storage_class:
            # Create client instance mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Create storage instance mock
            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            
            # Mock storage.save_from_url
            async def mock_save_from_url(url, filename, metadata=None):
                method_calls["save_from_url"] += 1
                # Create a fake file in temp directory
                filepath = Path(temp_output_dir) / filename
                filepath.write_text("mock_image_data")
                return str(filepath)
            mock_storage.save_from_url = mock_save_from_url
            
            # Mock client.initialize
            async def mock_initialize():
                method_calls["initialize"] = True
                return True
            mock_client.initialize = mock_initialize
            
            # Mock client.generate_image  
            async def mock_generate_image(prompt):
                method_calls["generate_image"] = True
                return GenerationResult(
                    success=True,
                    grid_message_id=grid_message_id,
                    image_url=grid_image_url
                )
            mock_client.generate_image = mock_generate_image
            
            # Mock client.upscale_all_variants
            async def mock_upscale_all_variants(message_id):
                method_calls["upscale_all_variants"] = True
                return [
                    UpscaleResult(success=True, variant=1, image_url="https://example.com/upscale1.png"),
                    UpscaleResult(success=True, variant=2, image_url="https://example.com/upscale2.png"),
                    UpscaleResult(success=True, variant=3, image_url="https://example.com/upscale3.png"),
                    UpscaleResult(success=True, variant=4, image_url="https://example.com/upscale4.png")
                ]
            mock_client.upscale_all_variants = mock_upscale_all_variants
            
            # Mock client.close
            async def mock_close():
                method_calls["close"] = True
            mock_client.close = mock_close
            
            # Call the generate_and_upscale function directly (not main, which uses asyncio.run)
            result = await generate_and_upscale.generate_and_upscale(test_prompt, temp_output_dir)
        
        # Verify all methods were called in correct order
        assert method_calls["initialize"], "Should call client.initialize()"
        assert method_calls["generate_image"], "Should call client.generate_image()"
        assert method_calls["upscale_all_variants"], "Should call client.upscale_all_variants()"
        assert method_calls["save_from_url"] >= 5, "Should save grid + 4 upscales (at least 5 files)"
        assert method_calls["close"], "Should call client.close()"
        
        # Verify result indicates success
        assert result is not None, "Workflow should return a result"
        assert result.get("success") is True, "Workflow should complete successfully"
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling_on_generation_failure(self, mock_env_vars, temp_output_dir):
        """Test workflow handles generation failures gracefully"""
        
        with patch('generate_and_upscale.MidjourneyClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock successful initialization
            mock_client.initialize = AsyncMock(return_value=True)
            
            # Mock failing generation
            async def failing_generate(prompt):
                raise Exception("Mock generation failure")
            mock_client.generate_image = failing_generate
            
            # Mock close method
            mock_client.close = AsyncMock()
            
            # Call the function directly to handle the error gracefully
            result = await generate_and_upscale.generate_and_upscale('test prompt', temp_output_dir)
        
        # Should still call close even on failure
        mock_client.close.assert_called_once()
        
        # Result should indicate failure
        assert result is not None, "Should return a result even on failure"
        assert result.get("success") is False, "Should indicate failure in result"
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling_on_upscale_failure(self, mock_env_vars, temp_output_dir):
        """Test workflow handles upscale failures gracefully"""
        
        with patch('generate_and_upscale.MidjourneyClient') as mock_client_class, \
             patch('generate_and_upscale.FileSystemStorage') as mock_storage_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock storage
            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            mock_storage.save_from_url = AsyncMock(return_value="/path/to/saved/file")
            
            # Mock successful initialization and generation
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.generate_image = AsyncMock(return_value=GenerationResult(
                success=True,
                grid_message_id="mock_id",
                image_url="https://example.com/grid.png"
            ))
            
            # Mock failing upscale
            async def failing_upscale(message_id):
                raise Exception("Mock upscale failure")
            mock_client.upscale_all_variants = failing_upscale
            
            # Mock close method
            mock_client.close = AsyncMock()
            
            # Call the function directly
            result = await generate_and_upscale.generate_and_upscale('test prompt', temp_output_dir)
        
        # Should still save the grid image even if upscales fail
        mock_storage.save_from_url.assert_called()
        mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_workflow_file_output_structure(self, mock_env_vars, temp_output_dir):
        """Test that workflow creates proper file output structure"""
        
        with patch('generate_and_upscale.MidjourneyClient') as mock_client_class, \
             patch('generate_and_upscale.FileSystemStorage') as mock_storage_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Track saved files
            saved_files = []
            
            # Mock storage
            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            
            async def track_save_from_url(url, filename, metadata=None):
                filepath = Path(temp_output_dir) / filename
                filepath.write_text(f"mock_data_for_{filename}")
                saved_files.append(filename)
                return str(filepath)
            
            mock_storage.save_from_url = track_save_from_url
            
            # Mock successful flow
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.generate_image = AsyncMock(return_value=GenerationResult(
                success=True,
                grid_message_id="mock_grid_123",
                image_url="https://example.com/grid.png"
            ))
            mock_client.upscale_all_variants = AsyncMock(return_value=[
                UpscaleResult(success=True, variant=1, image_url="https://example.com/up1.png"),
                UpscaleResult(success=True, variant=2, image_url="https://example.com/up2.png")
            ])
            mock_client.close = AsyncMock()
            
            # Call the function directly
            test_prompt = "test image generation"
            await generate_and_upscale.generate_and_upscale(test_prompt, temp_output_dir)
        
        # Verify expected files were created
        assert len(saved_files) >= 3, "Should save grid + upscales"
        
        # Check that files exist in temp directory
        output_files = list(Path(temp_output_dir).glob("*"))
        assert len(output_files) >= 3, "Should create actual output files"
        
        # Verify file naming patterns (basic check)
        file_names = [f.name for f in output_files]
        assert any("grid" in name.lower() or "png" in name for name in file_names), "Should create grid file"
    
    @pytest.mark.asyncio
    async def test_workflow_prompt_preservation(self, mock_env_vars, temp_output_dir):
        """Test that the original prompt is preserved throughout the workflow"""
        
        test_prompt = "very specific test prompt with --ar 16:9 --v 6"
        captured_prompts = []
        
        with patch('generate_and_upscale.MidjourneyClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            mock_client.initialize = AsyncMock(return_value=True)
            
            # Capture the prompt passed to generate_image
            async def capture_generate_image(prompt):
                captured_prompts.append(prompt)
                return GenerationResult(
                    success=True,
                    grid_message_id="mock_id",
                    image_url="https://example.com/grid.png"
                )
            mock_client.generate_image = capture_generate_image
            
            mock_client.upscale_all_variants = AsyncMock(return_value=[])
            mock_client.storage = AsyncMock()
            mock_client.storage.save_from_url = AsyncMock(return_value="/mock/path")
            mock_client.close = AsyncMock()
            
            # Call the function directly with specific prompt
            await generate_and_upscale.generate_and_upscale(test_prompt, temp_output_dir)
        
        # Verify the exact prompt was passed through
        assert len(captured_prompts) == 1, "Should call generate_image exactly once"
        assert captured_prompts[0] == test_prompt, f"Should preserve prompt exactly. Expected: {test_prompt}, Got: {captured_prompts[0]}"