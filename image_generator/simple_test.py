#!/usr/bin/env python3
import asyncio, sys
from src.utils import RateLimiter
async def test():
    limiter = RateLimiter(base_delay=0.01)
    async def mock_func():
        return "success"
    result = await limiter.with_retry(mock_func)
    print("Result:", result)
    assert result == "success"
asyncio.run(test())
