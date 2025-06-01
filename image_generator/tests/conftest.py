#!/usr/bin/env python3
"""
Pytest fixtures for the image_generator component tests.
"""

import os
import sys
import pytest
import pytest_asyncio
import asyncio
import dotenv
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src import MidjourneyClient, FileSystemStorage, GridFSStorage
    from src.client import DiscordGateway
except ImportError:
    print("Failed to import required modules. Check your import paths.")
    sys.exit(1)

# Load environment variables from .env files
def load_env_files():
    """Load environment variables from all possible .env files"""
    env_files = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', '.env')
    ]
    
    for env_file in env_files:
        if os.path.exists(env_file):
            dotenv.load_dotenv(env_file)
            break

# Load environment variables before running tests
load_env_files()

# Get common environment variables
USER_TOKEN = os.environ.get("DISCORD_USER_TOKEN")
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
MONGODB_URI = os.environ.get("MONGODB_URI")
MOCK_MODE = os.environ.get("MOCK_MODE", "true").lower() == "true"
DISCORD_MOCK_RESPONSES = os.environ.get("DISCORD_MOCK_RESPONSES", "true").lower() == "true"

# Set default test output directory
DEFAULT_TEST_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_output")
TEST_OUTPUT_DIR = os.environ.get("TEST_DOWNLOAD_DIR", DEFAULT_TEST_OUTPUT_DIR)

@pytest.fixture
def test_output_dir():
    """Create and provide a test output directory"""
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    return TEST_OUTPUT_DIR

@pytest.fixture
def filesystem_storage(test_output_dir):
    """Create a FileSystemStorage instance for testing"""
    return FileSystemStorage(test_output_dir)

@pytest.fixture
def mongodb_available():
    """Check if MongoDB is available for testing"""
    return bool(MONGODB_URI)

@pytest.fixture
def gridfs_storage(mongodb_available):
    """Create a GridFSStorage instance for testing"""
    if not mongodb_available:
        pytest.skip("MongoDB not available for testing")
    return GridFSStorage(mongodb_uri=MONGODB_URI, db_name="test_midjourney")

@pytest.fixture
def discord_credentials_available():
    """Check if Discord credentials are available for testing"""
    return all([USER_TOKEN, BOT_TOKEN, CHANNEL_ID, GUILD_ID])

@pytest.fixture
def mock_gateway():
    """Create a mock Discord gateway for testing"""
    gateway = MagicMock(spec=DiscordGateway)
    gateway.connect = AsyncMock(return_value=True)
    gateway.close = AsyncMock(return_value=True)
    gateway.session_id = "mock_session_id"
    gateway.connected = MagicMock()
    gateway.connected.is_set = MagicMock(return_value=True)
    gateway.register_handler = MagicMock()
    return gateway

@pytest_asyncio.fixture
async def mock_midjourney_client(mock_gateway, filesystem_storage):
    """Create a mock Midjourney client for testing"""
    # Create a client instance with test tokens
    client = MidjourneyClient(
        user_token="mock_user_token",
        bot_token="mock_bot_token",
        channel_id="mock_channel_id",
        guild_id="mock_guild_id"
    )
    
    # Set the storage
    client.storage = filesystem_storage
    
    # Replace gateway connections with mocks
    client.user_gateway = mock_gateway
    client.bot_gateway = mock_gateway
    
    # Set up generation future
    client.generation_future = asyncio.Future()
    client.generation_future.set_result({
        'message_id': 'mock_message_id',
        'image_url': 'https://example.com/mock.png'
    })
    
    # Set up mock responses for HTTP requests
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status = 204  # Discord returns 204 No Content on success
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # Initialize the client
        await client.initialize()
        
        # Use await for the fixture to ensure it's consumed correctly
        yield client
        
        # Close the client
        await client.close()

@pytest_asyncio.fixture
async def midjourney_client(discord_credentials_available):
    """Create and initialize a MidjourneyClient for testing"""
    if MOCK_MODE:
        pytest.skip("Skipping live client test in mock mode")
    
    if not discord_credentials_available:
        pytest.skip("Discord credentials not available for testing")
    
    client = MidjourneyClient(
        user_token=USER_TOKEN,
        bot_token=BOT_TOKEN,
        channel_id=CHANNEL_ID,
        guild_id=GUILD_ID
    )
    
    await client.initialize()
    yield client
    await client.close()

# Setup mock mode
if MOCK_MODE:
    # Apply global patches for tests running in mock mode
    @pytest.fixture(autouse=True)
    def mock_aiohttp_session(monkeypatch):
        """Mock aiohttp ClientSession to prevent actual HTTP requests"""
        async def mock_get(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=[])
            mock_resp.read = AsyncMock(return_value=b'mock_image_data')
            mock_resp.text = AsyncMock(return_value='mock_text')
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=None)
            return mock_resp
            
        async def mock_post(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status = 204
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=None)
            return mock_resp
            
        monkeypatch.setattr('aiohttp.ClientSession.get', mock_get)
        monkeypatch.setattr('aiohttp.ClientSession.post', mock_post) 