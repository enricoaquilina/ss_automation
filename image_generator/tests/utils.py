#!/usr/bin/env python3
"""
Test Utilities

Common utilities for Midjourney testing
"""

import os
import json
import random
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, Set
import aiohttp
import uuid
from pathlib import Path
import string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("test_utils")

# Test data generation utilities
def generate_mock_message(message_type: str, variant: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate mock Discord message data for testing message parsing logic
    
    Args:
        message_type: Type of message to generate ('generation', 'upscale', 'waiting', 'stopped')
        variant: For upscale messages, which variant (1-4)
    
    Returns:
        Mock message dictionary in Discord format
    """
    message_id = f"{random.randint(100000000000000000, 999999999999999999)}"
    timestamp = datetime.now().isoformat() + "Z"
    
    base_message = {
        "id": message_id,
        "type": 0,
        "channel_id": "123456789012345678",
        "author": {
            "id": "936929561302675456",  # Midjourney bot ID
            "username": "Midjourney Bot",
            "global_name": "Midjourney Bot",
            "avatar": "f6ce562a6b4979c4b1cbc5b436d3be76"
        },
        "timestamp": timestamp,
        "components": []
    }
    
    prompt = "test prompt with parameters"
    
    if message_type == "waiting":
        base_message["content"] = f"**{prompt}** - <@123456789012345678> (Waiting to start)"
        
    elif message_type == "stopped":
        base_message["content"] = f"**{prompt}** - <@123456789012345678> (Stopped)"
        
    elif message_type == "generation":
        # Grid with 4 images
        base_message["content"] = f"**{prompt}** - <@123456789012345678> (fast)"
        base_message["attachments"] = [{
            "id": f"{random.randint(100000000000000000, 999999999999999999)}",
            "filename": "grid.png",
            "content_type": "image/png",
            "size": 1234567,
            "url": "https://cdn.discordapp.com/attachments/123456789012345678/123456789012345678/grid.png",
            "width": 2048,
            "height": 2048
        }]
        
        # Add buttons for upscaling
        base_message["components"] = [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 2,
                        "label": "U1",
                        "custom_id": f"MJ::JOB::upsample::1::{random.randint(100000, 999999)}"
                    },
                    {
                        "type": 2,
                        "style": 2,
                        "label": "U2",
                        "custom_id": f"MJ::JOB::upsample::2::{random.randint(100000, 999999)}"
                    },
                    {
                        "type": 2,
                        "style": 2,
                        "label": "U3",
                        "custom_id": f"MJ::JOB::upsample::3::{random.randint(100000, 999999)}"
                    },
                    {
                        "type": 2,
                        "style": 2,
                        "label": "U4",
                        "custom_id": f"MJ::JOB::upsample::4::{random.randint(100000, 999999)}"
                    }
                ]
            }
        ]
        
    elif message_type == "upscale" and variant is not None:
        # Single upscaled image
        base_message["content"] = f"**{prompt}** - Image #{variant} <@123456789012345678> (upscaled)"
        base_message["attachments"] = [{
            "id": f"{random.randint(100000000000000000, 999999999999999999)}",
            "filename": f"upscale_{variant}.png",
            "content_type": "image/png",
            "size": 2345678,
            "url": f"https://cdn.discordapp.com/attachments/123456789012345678/123456789012345678/upscale_{variant}.png",
            "width": 2048,
            "height": 2048
        }]
    
    return base_message

def generate_mock_gateway_data(event_type: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate mock Discord gateway data for testing WebSocket handlers
    
    Args:
        event_type: Type of gateway event ('MESSAGE_CREATE', 'READY', etc.)
        message: Message data to include
        
    Returns:
        Mock gateway data in Discord format
    """
    return {
        "t": event_type,
        "s": random.randint(1, 100),
        "op": 0,  # DISPATCH
        "d": message
    }

# Environment utilities
def load_env_vars() -> Dict[str, str]:
    """
    Load environment variables required for testing
    
    Returns:
        Dictionary of environment variables
    """
    required_vars = [
        "DISCORD_CHANNEL_ID",
        "DISCORD_GUILD_ID",
        "DISCORD_BOT_TOKEN",
        "DISCORD_USER_TOKEN"
    ]
    
    # If FULLY_MOCKED=true, use mock values
    if os.environ.get("FULLY_MOCKED", "").lower() == "true":
        return {
            "DISCORD_USER_TOKEN": "mock_user_token",
            "DISCORD_BOT_TOKEN": "mock_bot_token",
            "DISCORD_CHANNEL_ID": "1234567890",
            "DISCORD_GUILD_ID": "0987654321"
        }
    
    # Check if all variables are present
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        logger.warning(f"Missing environment variables: {', '.join(missing)}")
        return None
    
    # Return dictionary of environment variables
    return {
        var: os.environ.get(var) for var in required_vars
    }

# Test result handling
def save_test_results(test_name: str, results: Dict[str, Any], output_dir: Optional[str] = None) -> str:
    """
    Save test results to a JSON file
    
    Args:
        test_name: Name of the test
        results: Test results dictionary
        output_dir: Directory to save results (default: test_results)
        
    Returns:
        Path to the saved results file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not output_dir:
        output_dir = "test_results"
    
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{test_name}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Test results saved to {filepath}")
    return filepath

# Network error simulation
async def simulate_network_error(duration: float = 5.0):
    """
    Simulate a network error by sleeping for the specified duration
    
    Args:
        duration: Duration of the simulated network error in seconds
    """
    logger.info(f"Simulating network error for {duration} seconds...")
    await asyncio.sleep(duration)
    logger.info("Network error simulation complete")

# Message processing utilities
def extract_button_custom_ids(message: Dict[str, Any]) -> Dict[int, str]:
    """
    Extract button custom IDs from a message
    
    Args:
        message: Message data
        
    Returns:
        Dictionary mapping variant numbers to custom IDs
    """
    custom_ids = {}
    
    if "components" not in message:
        return custom_ids
        
    for row in message.get("components", []):
        for component in row.get("components", []):
            if component.get("type") == 2:  # Button type
                label = component.get("label", "")
                if label.startswith("U") and len(label) == 2:
                    try:
                        variant = int(label[1])
                        custom_id = component.get("custom_id")
                        if custom_id:
                            custom_ids[variant] = custom_id
                    except ValueError:
                        pass
    
    return custom_ids

async def download_image(url: str, path: Union[str, Path]) -> bool:
    """Download an image from URL and save to the specified path"""
    if not url:
        logger.error("No URL provided for download")
        return False
    
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(path, 'wb') as f:
                        f.write(await response.read())
                    logger.info(f"Downloaded image to {path}")
                    return True
                else:
                    logger.error(f"Failed to download image: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return False

def setup_test_directory(prefix: str = "test") -> Path:
    """
    Create a timestamped test directory
    
    Args:
        prefix: Prefix for the directory name
        
    Returns:
        Path: Path to the created directory
    """
    # Create a timestamped directory name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{prefix}_{timestamp}"
    
    # Create the directory in the test_output folder
    base_dir = os.path.join(os.path.dirname(__file__), "test_output")
    test_dir = os.path.join(base_dir, dir_name)
    
    # Create the directory
    os.makedirs(test_dir, exist_ok=True)
    
    logger.info(f"Created test directory: {test_dir}")
    return Path(test_dir)

def generate_mock_aspect_ratio_result(ratio_name: str, ratio_param: str) -> Dict[str, Any]:
    """Generate a mock result for aspect ratio testing"""
    # In most test cases, we want successful results
    success = random.random() < 0.9  # 90% success rate for mock
    
    result = {
        "aspect_ratio": ratio_name,
        "ratio_param": ratio_param,
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "error": None,
        "generation": {
            "grid_message_id": str(random.randint(10**17, 10**18 - 1)),
            "image_url": f"https://cdn.discordapp.com/attachments/123456789012345678/123456789012345678/cosmic_space_dolphin_{ratio_name}_{uuid.uuid4().hex[:6]}.png"
        },
        "upscales": []
    }
    
    # If test should fail, add error and return
    if not success:
        result["error"] = f"Mock failure for {ratio_name}"
        result["generation"] = None
        return result
    
    # Add mock upscale results
    for i in range(1, 5):
        # Make random upscales fail occasionally
        upscale_success = random.random() < 0.95  # 95% success rate for individual upscales
        
        upscale = {
            "variant": i,
            "success": upscale_success,
            "error": None
        }
        
        if upscale_success:
            upscale["image_url"] = f"https://cdn.discordapp.com/attachments/123456789012345678/123456789012345678/cosmic_space_dolphin_{ratio_name}_Upscale_{i}_{uuid.uuid4().hex[:6]}.png"
        else:
            upscale["error"] = f"Mock upscale failure for variant {i}"
        
        result["upscales"].append(upscale)
    
    return result 

# NEW: Improved fallback method for upscale detection with correlation
async def improved_fallback_get_upscale_result(variant: int, 
                                               grid_message_id: Optional[str] = None,
                                               messages: Optional[List[Dict[str, Any]]] = None,
                                               start_time: Optional[float] = None,
                                               track_prompt: Optional[str] = None) -> Optional[str]:
    """
    Improved fallback method for detecting upscale completion with correlation to the grid
    
    This implementation addresses the issue where upscales could be mistakenly matched
    from previous prompts instead of the current grid image.
    
    Args:
        variant: The variant being upscaled (1-4)
        grid_message_id: ID of the grid message these upscales belong to
        messages: Optional list of messages to use (for testing)
        start_time: The time when the upscale request was sent
        track_prompt: The original prompt text to match against upscale messages
        
    Returns:
        str or None: URL of upscaled image if found and correlated, or None
    """
    # Default start time to now if not provided
    if start_time is None:
        start_time = time.time()
    
    # Convert to timestamp for comparison
    start_timestamp = datetime.fromtimestamp(start_time).isoformat()
    
    # Use provided messages or create mock messages
    if messages is None:
        # These would normally be fetched from Discord
        messages = [
            # Old upscale message that should be ignored
            {
                "id": "old_message_1",
                "content": "**Previous prompt** - Image #1 (574kB)",
                "timestamp": "2025-05-10T10:15:30.000Z",  # Old timestamp
                "attachments": [{"url": "https://example.com/old_upscale.png"}]
            },
            # Current upscale message that should be selected
            {
                "id": "current_message_1",
                "content": f"**{track_prompt or 'Current prompt'}** - Image #{variant} (621kB)",
                "timestamp": datetime.now().isoformat() + "Z",  # Current timestamp
                "attachments": [{"url": f"https://example.com/current_upscale_{variant}.png"}],
                "referenced_message": {"id": grid_message_id} if grid_message_id else None
            }
        ]
    
    # Keep track of processed message IDs to avoid duplicates
    processed_msg_ids = set()
    
    # Filter for valid upscale messages
    valid_upscales = []
    
    for msg in messages:
        msg_id = msg.get("id")
        
        # Skip already processed messages
        if msg_id in processed_msg_ids:
            continue
        
        # Add to processed set
        processed_msg_ids.add(msg_id)
        
        # Check for valid upscale indicators
        content = msg.get("content", "").lower()
        is_upscale = False
        
        upscale_indicators = [
            f"image #{variant}",
            f"variant {variant}",
            f"u{variant}",
            f"upscaled (u{variant})"
        ]
        
        if any(indicator in content for indicator in upscale_indicators):
            is_upscale = True
        
        # Skip if not an upscale message for our variant
        if not is_upscale:
            continue
        
        # Check timestamp if available
        msg_time = msg.get("timestamp", "").replace("Z", "+00:00")
        if msg_time and msg_time < start_timestamp:
            # This upscale message is from before we started the upscale
            continue
        
        # Check prompt matching if prompt provided
        if track_prompt and "**" in msg.get("content", ""):
            # Extract text between ** if present
            content_parts = msg.get("content", "").split("**")
            if len(content_parts) >= 3:
                msg_prompt = content_parts[1].strip().lower()
                if track_prompt.lower() not in msg_prompt:
                    # Prompt doesn't match, skip
                    continue
        
        # Check reference to grid message if provided
        if grid_message_id and msg.get("referenced_message", {}).get("id") != grid_message_id:
            # If direct reference exists but doesn't match our grid, skip
            if msg.get("referenced_message") is not None:
                continue
        
        # Message passed all checks - if it has an attachment, add to valid upscales
        if msg.get("attachments"):
            valid_upscales.append(msg)
    
    # Sort by timestamp (newest first)
    valid_upscales.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
    
    # Return the URL from the most recent valid message
    if valid_upscales and valid_upscales[0].get("attachments"):
        return valid_upscales[0]["attachments"][0]["url"]
    
    return None 