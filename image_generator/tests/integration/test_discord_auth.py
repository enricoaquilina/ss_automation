#!/usr/bin/env python3
"""
Test Discord API Authentication

This script tests Discord API authentication by making a real API call
to verify that the token is valid.
"""

import os
import sys
import requests
import dotenv
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("discord_auth_test")

def find_and_load_env_file():
    """Find and load the first available .env file"""
    # Start with the current working directory and work up
    current_dir = os.getcwd()
    
    # Define potential .env file paths
    potential_paths = [
        os.path.join(current_dir, '.env'),
        os.path.join(current_dir, 'src', '.env'),
        os.path.join(current_dir, '.env-files', '.env'),
        os.path.join(os.path.dirname(current_dir), '.env'),  # Parent directory
    ]
    
    # Project root (assuming we're in tests/integration)
    if 'tests' in current_dir:
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
        potential_paths.append(os.path.join(project_root, '.env'))
    
    logger.info(f"Searching for .env files in {len(potential_paths)} locations")
    
    # Try each potential path
    for env_path in potential_paths:
        if os.path.exists(env_path):
            logger.info(f"Found .env file at {env_path}")
            dotenv.load_dotenv(env_path)
            return env_path
    
    logger.warning("No .env file found in any of the expected locations")
    return None

def test_discord_auth():
    """Test Discord API authentication"""
    print("\n=== DISCORD AUTHENTICATION TEST ===")
    
    # Find and load environment variables
    env_file = find_and_load_env_file()
    if not env_file:
        logger.warning("No .env file found, attempting to use environment variables directly")
    
    # Check for Discord tokens (user token is primary, bot token is secondary)
    token = os.environ.get('DISCORD_USER_TOKEN')
    if not token:
        token = os.environ.get('DISCORD_TOKEN')  # Legacy name
    
    channel_id = os.environ.get('DISCORD_CHANNEL_ID')
    
    # Check if token is missing
    if not token:
        logger.error("❌ No Discord token found in environment variables")
        print("❌ No Discord token found in environment variables")
        print("Please set DISCORD_USER_TOKEN in your .env file or environment")
        return False
    
    # Check if channel ID is missing
    if not channel_id:
        logger.warning("No channel ID found, using default test channel")
        channel_id = "1125101062454513738"  # Default test channel
    
    # Clean up token
    token = token.strip("\"' \t\n\r")
    
    # Log token info (safely)
    if len(token) > 10:
        logger.info(f"Using token: {token[:5]}...{token[-5:]}")
    else:
        logger.warning("Token seems too short")
    
    # Test API call to validate token
    try:
        test_endpoint = f"https://discord.com/api/v9/channels/{channel_id}"
        
        # First try with Bot prefix
        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (https://github.com/discord/discord-api-docs, 9)"
        }
        
        logger.info(f"Testing Discord API authentication with channel ID: {channel_id}")
        logger.info("Trying with Bot prefix first...")
        
        response = requests.get(test_endpoint, headers=headers)
        
        if response.status_code == 200:
            logger.info("✅ Discord API authentication successful with Bot prefix")
            print("✅ Discord API authentication successful with Bot prefix")
            print(f"Response: {response.json()}")
            return True
        else:
            logger.warning(f"Bot authorization failed: {response.status_code}")
            
            # Try with direct token (user token)
            logger.info("Trying with direct token (for user token)...")
            headers["Authorization"] = token
            
            response = requests.get(test_endpoint, headers=headers)
            
            if response.status_code == 200:
                logger.info("✅ Discord API authentication successful with direct token")
                print("✅ Discord API authentication successful with direct token")
                print(f"Response: {response.json()}")
                return True
            else:
                # Check if this is a 401 Unauthorized error (common for invalid tokens)
                if response.status_code == 401:
                    logger.error("❌ Discord API authentication failed: 401 Unauthorized")
                    print("❌ Discord API authentication failed: 401 Unauthorized")
                    print("This typically means your token is invalid or expired.")
                    
                    # Try to parse error response for more details
                    try:
                        error_data = response.json()
                        if 'message' in error_data:
                            print(f"Error message: {error_data['message']}")
                    except:
                        pass
                
                # General error case
                logger.error(f"❌ Discord API authentication failed: {response.status_code}")
                print(f"❌ Discord API authentication failed: {response.status_code}")
                print(f"Response: {response.text}")
                
                # Add common error help
                if response.status_code == 429:
                    print("You are being rate limited. Please wait before trying again.")
                elif response.status_code == 404:
                    print(f"Channel ID {channel_id} not found. Please check your DISCORD_CHANNEL_ID.")
                
                return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Connection error: {str(e)}")
        print(f"❌ Connection error: {str(e)}")
        print("Please check your internet connection and try again.")
        return False
    except Exception as e:
        logger.error(f"❌ Exception during Discord API authentication test: {str(e)}")
        print(f"❌ Exception during Discord API authentication test: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_discord_auth()
    sys.exit(0 if success else 1) 