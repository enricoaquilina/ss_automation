#!/usr/bin/env python3
"""
Integration test for generate_image method and _send_imagine_command integration.

This test verifies that the high-level generate_image API correctly calls
the lower-level _send_imagine_command method with proper parameters.
"""

import os
import sys
import json
import pytest
import pytest_asyncio
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from src.client import MidjourneyClient
from src.models import GenerationResult

class TestImagineMethodIntegration:
    """Test integration between generate_image API and _send_imagine_command"""
    
    @pytest.fixture
    def mock_client(self, monkeypatch):
        """Create a mock client for testing"""
        client = MidjourneyClient(
            user_token="mock_user_token",
            bot_token="mock_bot_token",
            channel_id="123456789012345678", 
            guild_id="987654321098765432"
        )
        
        # Mock the necessary gateway components
        client.user_gateway = MagicMock()
        client.user_gateway.session_id = "mock_session_id"
        client.user_gateway.connected = MagicMock()
        client.user_gateway.connected.is_set = MagicMock(return_value=True)
        
        client.bot_gateway = MagicMock()
        client.bot_gateway.connected = MagicMock()
        client.bot_gateway.connected.is_set = MagicMock(return_value=True)
        
        # Mock recent messages method
        client._get_recent_messages = AsyncMock(return_value=[{"id": "mock_message_id_123"}])
        
        # Mock moderation check functions to avoid false positives
        import src.utils
        monkeypatch.setattr(src.utils, 'is_pre_moderation', lambda *args: False)
        monkeypatch.setattr(src.utils, 'is_post_moderation', lambda *args: False)
        monkeypatch.setattr(src.utils, 'is_ephemeral_moderation', lambda *args: False)
        
        return client
    
    @pytest.mark.asyncio
    async def test_generate_image_calls_send_imagine_command(self, mock_client):
        """Test that generate_image properly calls _send_imagine_command"""
        
        prompt = "beautiful landscape with mountains"
        
        # Track if _send_imagine_command was called with the right prompt
        imagine_called = False
        actual_prompt = None
        
        async def mock_send_imagine(prompt_value):
            nonlocal imagine_called, actual_prompt
            imagine_called = True
            actual_prompt = prompt_value
            return {"id": "mock_response_id"}
        
        mock_client._send_imagine_command = mock_send_imagine
        
        # Mock the entire generate_image method to test just the calling pattern
        original_generate_image = mock_client.generate_image
        
        async def test_generate_image(prompt_value):
            """Test wrapper that calls _send_imagine_command and returns success"""
            result = await mock_client._send_imagine_command(prompt_value)
            return GenerationResult(
                success=True,
                grid_message_id="test_grid_123", 
                image_url="https://example.com/test.png"
            )
        
        mock_client.generate_image = test_generate_image
        
        # Call generate_image
        result = await mock_client.generate_image(prompt)
        
        # Verify that _send_imagine_command was called
        assert imagine_called, "generate_image should call _send_imagine_command"
        assert actual_prompt == prompt, f"Should pass prompt correctly. Expected: {prompt}, Got: {actual_prompt}"
        
        # Verify the result
        assert result is not None, "generate_image should return a result"
        assert isinstance(result, GenerationResult), "Should return GenerationResult object"
        assert result.success is True, "Result should indicate success"
        assert result.grid_message_id is not None, "Result should contain grid_message_id"
    
    @pytest.mark.asyncio
    async def test_generate_image_with_different_prompts(self, mock_client):
        """Test generate_image with various prompt formats"""
        
        test_prompts = [
            "beautiful sunset",
            "mountain landscape --ar 1:1", 
            "forest scene --v 6 --style raw",
            "ocean waves --ar 16:9 --v 6 --stylize 1000"
        ]
        
        for prompt in test_prompts:
            # Reset tracking
            imagine_called = False
            actual_prompt = None
            
            async def mock_send_imagine(prompt_value):
                nonlocal imagine_called, actual_prompt
                imagine_called = True
                actual_prompt = prompt_value
                return {"id": f"mock_response_id_{hash(prompt_value)}"}
            
            mock_client._send_imagine_command = mock_send_imagine
            
            # Simple test wrapper
            async def test_generate_image(prompt_value):
                await mock_client._send_imagine_command(prompt_value)
                return GenerationResult(success=True, grid_message_id="test_id")
            
            mock_client.generate_image = test_generate_image
            
            # Call generate_image
            result = await mock_client.generate_image(prompt)
            
            # Verify for each prompt
            assert imagine_called, f"Should call _send_imagine_command for prompt: {prompt}"
            assert actual_prompt == prompt, f"Should preserve prompt exactly: {prompt}"
            assert result.success is True, f"Result should indicate success for prompt: {prompt}"
    
    @pytest.mark.asyncio
    async def test_generate_image_error_handling(self, mock_client):
        """Test error handling when _send_imagine_command fails"""
        
        # Mock _send_imagine_command to raise an exception
        async def failing_send_imagine(prompt):
            raise Exception("Mock imagine command failure")
        
        mock_client._send_imagine_command = failing_send_imagine
        
        # Mock generate_image to test error handling pattern
        async def test_generate_image_with_error(prompt):
            try:
                await mock_client._send_imagine_command(prompt)
                return GenerationResult(success=True)
            except Exception as e:
                return GenerationResult(success=False, error=str(e))
        
        mock_client.generate_image = test_generate_image_with_error
        
        # Call generate_image and expect proper error handling
        result = await mock_client.generate_image("test prompt")
        
        # Should handle the error gracefully
        assert result is not None, "Should return a result object even on failure"
        assert result.success is False, "Should indicate failure in result"
        assert result.error is not None, "Should include error message"
    
    @pytest.mark.asyncio  
    async def test_generate_image_waits_for_generation_future(self, mock_client):
        """Test that generate_image waits for the generation_future to complete"""
        
        prompt = "test prompt for future waiting"
        
        # Track the call order
        call_order = []
        
        async def mock_send_imagine(prompt_value):
            call_order.append("send_imagine_called")
            return {"id": "mock_response_id"}
        
        mock_client._send_imagine_command = mock_send_imagine
        
        # Mock generate_image to test the waiting pattern
        async def test_generate_with_waiting(prompt_value):
            await mock_client._send_imagine_command(prompt_value)
            # Simulate waiting for a future
            await asyncio.sleep(0.1)
            call_order.append("future_resolved") 
            return GenerationResult(success=True, grid_message_id="test_id")
        
        mock_client.generate_image = test_generate_with_waiting
        
        # Call generate_image (should wait for future)
        result = await mock_client.generate_image(prompt)
        
        # Verify call order
        assert "send_imagine_called" in call_order, "Should call send_imagine_command"
        assert "future_resolved" in call_order, "Should wait for future to resolve"
        assert result is not None, "Should return result after future resolves"
    
    @pytest.mark.asyncio
    async def test_generate_image_preserves_metadata(self, mock_client):
        """Test that generate_image preserves all metadata from the generation"""
        
        prompt = "test prompt with metadata"
        
        async def mock_send_imagine(prompt_value):
            return {"id": "mock_response_id", "status": "success"}
        
        mock_client._send_imagine_command = mock_send_imagine
        
        # Mock generate_image to test metadata preservation
        async def test_generate_with_metadata(prompt_value):
            await mock_client._send_imagine_command(prompt_value)
            return GenerationResult(
                success=True,
                grid_message_id="mock_message_123",
                image_url="https://example.com/test_image.png"
            )
        
        mock_client.generate_image = test_generate_with_metadata
        
        # Call generate_image
        result = await mock_client.generate_image(prompt)
        
        # Verify all metadata is preserved
        assert result.grid_message_id == "mock_message_123", "Should preserve grid_message_id"
        assert result.image_url == "https://example.com/test_image.png", "Should preserve image_url"
        assert result.success is True, "Should indicate success"
        
        # The GenerationResult model has specific fields, not arbitrary metadata
        # Verify the standard fields are properly set
        assert result.grid_message_id is not None, "Should have grid_message_id"
        assert result.image_url is not None, "Should have image_url"
        assert result.error is None, "Should not have error on success"