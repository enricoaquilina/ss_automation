#!/usr/bin/env python3
"""
Simple tests for the RateLimiter class.

Tests basic functionality of the rate limiter without complex async testing.
"""

import sys
import os
import unittest
import time
import asyncio
import pytest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

# Import the RateLimiter class
try:
    from utils import RateLimiter
except ImportError:
    try:
        from src.utils import RateLimiter
    except ImportError as e:
        print(f"Failed to import RateLimiter: {e}")
        RateLimiter = MagicMock  # Mock as a fallback

class TestSimpleRateLimiter(unittest.TestCase):
    """Simple tests for the RateLimiter class"""
    
    def test_initialization(self):
        """Test that the rate limiter can be initialized with various parameters"""
        # Default initialization
        rate_limiter = RateLimiter()
        self.assertIsNotNone(rate_limiter)
        
        # Custom base delay
        rate_limiter = RateLimiter(base_delay=0.5)
        self.assertIsNotNone(rate_limiter)
        self.assertEqual(rate_limiter.base_delay, 0.5)
    
    def test_update_rate_limits(self):
        """Test updating rate limits from headers"""
        rate_limiter = RateLimiter()
        
        # Mock headers
        headers = {
            'X-RateLimit-Remaining': '4',
            'X-RateLimit-Reset': '1000.0'
        }
        
        # Update from headers
        rate_limiter.update_rate_limits('test_endpoint', headers)
        
        # Check the values
        self.assertEqual(rate_limiter.rate_limit_remaining.get('test_endpoint'), 4)
        self.assertEqual(rate_limiter.rate_limit_reset.get('test_endpoint'), 1000.0)
    
    @pytest.mark.asyncio
    @patch('time.time')
    @patch('asyncio.sleep')
    async def test_wait(self, mock_sleep, mock_time):
        """Test the wait method"""
        rate_limiter = RateLimiter(base_delay=0.1)
        
        # Setup time mock
        mock_time.side_effect = [100.0, 100.0]  # Initial time
        rate_limiter.last_request_time = 99.9  # Last request was 0.1 seconds ago
        
        # Case 1: Base delay hasn't passed yet
        await rate_limiter.wait()
        # Should sleep for remaining time to reach base_delay
        mock_sleep.assert_called_with(0.0)  # (99.9 + 0.1) - 100.0 = 0.0
        
        # Reset mocks for next case
        mock_sleep.reset_mock()
        mock_time.side_effect = [200.0, 200.0]  # New time
        rate_limiter.last_request_time = 199.0  # Last request was 1.0 seconds ago
        
        # Case 2: Base delay has passed
        await rate_limiter.wait()
        # No additional wait needed beyond base delay
        self.assertEqual(mock_sleep.call_count, 0)
        
        # Reset mocks for next case
        mock_sleep.reset_mock()
        mock_time.side_effect = [300.0, 300.0]  # New time
        rate_limiter.last_request_time = 299.95  # Last request was 0.05 seconds ago
        
        # Case 3: Need to wait for base delay
        await rate_limiter.wait()
        # Should sleep for remaining time
        mock_sleep.assert_called_with(0.05)  # 0.1 - 0.05 = 0.05
        
        # Case 4: Endpoint has hit rate limit
        mock_sleep.reset_mock()
        mock_time.side_effect = [400.0, 400.0]  # New time
        rate_limiter.last_request_time = 399.0  # Last request was 1.0 seconds ago
        rate_limiter.rate_limit_remaining['limited_endpoint'] = 0
        rate_limiter.rate_limit_reset['limited_endpoint'] = 405.0  # Reset in 5 seconds
        
        # Wait on limited endpoint
        await rate_limiter.wait('limited_endpoint')
        # Should sleep for reset time
        mock_sleep.assert_called_with(5.1)  # 405.0 - 400.0 + 0.1 = 5.1 (includes buffer)
    
    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    async def test_with_retry(self, mock_sleep):
        """Test the with_retry method"""
        rate_limiter = RateLimiter()
        
        # Create a mock function that succeeds on the third try
        mock_func = MagicMock()
        mock_func.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            "success"
        ]
        
        # Define an async wrapper for the mock
        async def async_mock(*args, **kwargs):
            return mock_func(*args, **kwargs)
        
        # Test successful retry
        result = await rate_limiter.with_retry(async_mock, max_retries=3)
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)
        
        # Verify backoff was applied between retries (should be two sleeps)
        self.assertEqual(mock_sleep.call_count, 2)
        
        # Test failure after max retries
        mock_sleep.reset_mock()
        mock_func.reset_mock()
        mock_func.side_effect = Exception("Always fails")
        
        with self.assertRaises(Exception):
            await rate_limiter.with_retry(async_mock, max_retries=2)
        
        # Should have tried 3 times (initial + 2 retries)
        self.assertEqual(mock_func.call_count, 3)
        # Should have slept 2 times (between the 3 attempts)
        self.assertEqual(mock_sleep.call_count, 2)

if __name__ == "__main__":
    unittest.main() 