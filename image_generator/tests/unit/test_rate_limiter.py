#!/usr/bin/env python3
"""
Tests for the rate limiter functionality

This script tests the rate limiter functionality in the utils module,
verifying that rate limiting and retry logic work correctly.
"""

import os
import sys
import time
import pytest
import asyncio
import logging
from unittest.mock import MagicMock, patch

# Add the src directory to the path to allow importing the src package
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import the RateLimiter class from utils
from src.utils import RateLimiter, MidjourneyError

class TestRateLimiter:
    """Tests for the RateLimiter class"""
    
    @pytest.fixture(autouse=True)
    def mock_sleep(self, monkeypatch):
        """Mock asyncio.sleep for all rate limiter tests to avoid delays"""
        from unittest.mock import AsyncMock
        mock_sleep = AsyncMock()
        monkeypatch.setattr('asyncio.sleep', mock_sleep)
        return mock_sleep
    
    @pytest.mark.asyncio
    async def test_rate_limiter_delay(self, mock_sleep):
        """Test that rate limiter enforces delay between API calls"""
        limiter = RateLimiter(base_delay=0.1)  # Use smaller delay for testing
        
        # First call shouldn't wait
        await limiter.wait()
        # Should not call sleep on first request
        mock_sleep.assert_not_called()
        
        # Second call should wait at least base_delay
        await limiter.wait()
        # Should call sleep with at least base_delay
        mock_sleep.assert_called()
        call_args = mock_sleep.call_args[0]
        assert len(call_args) > 0, "Sleep should be called with delay argument"
        assert call_args[0] >= 0.09, f"Sleep delay should be at least 0.09, got {call_args[0]}"
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self):
        """Test updating rate limits from headers"""
        limiter = RateLimiter()
        
        # Mock headers
        headers = {
            'X-RateLimit-Remaining': '5',
            'X-RateLimit-Reset': str(time.time() + 10)  # 10 seconds from now
        }
        
        endpoint = "test_endpoint"
        limiter.update_rate_limits(endpoint, headers)
        
        assert limiter.rate_limit_remaining[endpoint] == 5
        assert endpoint in limiter.rate_limit_reset
    
    @pytest.mark.asyncio
    async def test_with_retry_eventual_success(self):
        """Test retry logic with eventual success"""
        limiter = RateLimiter(base_delay=0.01)  # Small delay for testing
        
        # Mock async function that fails twice then succeeds
        call_count = 0
        
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success after retries"
        
        result = await limiter.with_retry(test_func, max_retries=3)
        
        assert result == "success after retries"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_with_retry_max_retries_exceeded(self):
        """Test retry logic with max retries exceeded"""
        limiter = RateLimiter(base_delay=0.01)  # Small delay for testing
        
        # Mock async function that always fails
        async def test_func():
            raise Exception("Persistent failure")
        
        with pytest.raises(Exception) as excinfo:
            await limiter.with_retry(test_func, max_retries=2)
        
        assert "Persistent failure" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_with_retry_status_code(self):
        """Test retry logic with status code checking"""
        limiter = RateLimiter(base_delay=0.01)  # Small delay for testing
        
        # Mock response object with status code
        class MockResponse:
            def __init__(self, status_code):
                self.status_code = status_code
                self.headers = {}
        
        # Mock async function that returns response with status code
        call_count = 0
        
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MockResponse(429)  # Rate limited
            elif call_count == 2:
                return MockResponse(500)  # Server error
            else:
                return MockResponse(200)  # Success
        
        result = await limiter.with_retry(test_func, max_retries=3, retry_status_codes=[429, 500])
        
        assert result.status_code == 200
        assert call_count == 3

if __name__ == "__main__":
    pytest.main(["-v"])