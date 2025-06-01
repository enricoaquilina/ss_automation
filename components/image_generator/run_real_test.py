#!/usr/bin/env python3
"""
Run a real Midjourney test using the Silicon Sentiments client.

This script will:
1. Prompt for Discord credentials if not found in .env
2. Create a client with those credentials
3. Generate an image with a user-provided prompt
4. Upscale all variants (or optionally just one)
5. Save the results to an output directory

Usage:
    python run_real_test.py
"""

import os
import sys
import asyncio
import logging
import getpass
import argparse
import requests
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

try:
    # Try to load from dotenv package
    from dotenv import load_dotenv
except ImportError:
    # Create a simple stub if dotenv is not available
    def load_dotenv(dotenv_path=None):
        if dotenv_path and os.path.exists(dotenv_path):
            with open(dotenv_path) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value.strip('"\'')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("midjourney_test")

def get_credentials() -> Dict[str, str]:
    """
    Get Discord credentials from environment or user input
    
    Returns:
        Dict[str, str]: Dictionary with credential keys
    """
    # First try to load from .env file
    dotenv_paths = [
        '.env',
        'src/.env',
        '../.env',
        '../../.env'
    ]
    
    for path in dotenv_paths:
        if os.path.exists(path):
            logger.info(f"Loading environment from {path}")
            load_dotenv(path)
            break
    
    # Define required credentials
    required_keys = {
        "DISCORD_USER_TOKEN": "Discord User Token",
        "DISCORD_BOT_TOKEN": "Discord Bot Token",
        "DISCORD_CHANNEL_ID": "Discord Channel ID",
        "DISCORD_GUILD_ID": "Discord Guild/Server ID"
    }
    
    # Check if any credentials are missing
    missing_keys = [key for key in required_keys if not os.environ.get(key)]
    
    if missing_keys:
        logger.warning(f"Missing required credentials: {', '.join(missing_keys)}")
        logger.info("Please provide the missing credentials:")
        
        for key in missing_keys:
            value = None
            if "TOKEN" in key:
                # Use getpass for sensitive information
                value = getpass.getpass(f"Enter {required_keys[key]}: ")
            else:
                value = input(f"Enter {required_keys[key]}: ")
            
            os.environ[key] = value
    
    # Return dictionary of credentials
    return {
        "user_token": os.environ.get("DISCORD_USER_TOKEN"),
        "bot_token": os.environ.get("DISCORD_BOT_TOKEN"),
        "channel_id": os.environ.get("DISCORD_CHANNEL_ID"),
        "guild_id": os.environ.get("DISCORD_GUILD_ID")
    }

async def download_image(url: str, output_path: str) -> Path:
    """
    Download an image from a URL to a file
    
    Args:
        url: URL of the image
        output_path: Where to save the image
        
    Returns:
        Path: Path to the saved image
    """
    path = Path(output_path)
    
    # Create parent directory if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    try:
        # Use requests to download the image
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download image from {url}: {response.status_code}")
            return None
        
        # Save the image
        with open(path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        
        logger.debug(f"Downloaded image from {url} to {path}")
        return path
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None

async def run_midjourney_test(prompt: str, output_dir: str, upscale_variant: Optional[int] = None, skip_upscale: bool = False):
    """
    Run the Midjourney test
    
    Args:
        prompt: The prompt to generate an image with
        output_dir: Directory to save results to
        upscale_variant: If provided, only upscale this variant (1-4)
        skip_upscale: If True, skip the upscaling step entirely
    """
    # Import MidjourneyClient
    try:
        from src.client import MidjourneyClient
    except ImportError:
        logger.error("Failed to import MidjourneyClient.")
        logger.error("Make sure you're running this script from the component directory.")
        sys.exit(1)
    
    # Get credentials
    credentials = get_credentials()
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create client
    client = MidjourneyClient(
        user_token=credentials["user_token"],
        bot_token=credentials["bot_token"],
        channel_id=credentials["channel_id"],
        guild_id=credentials["guild_id"]
    )
    
    # Implement the missing methods
    async def get_message_details(message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific Discord message
        
        Args:
            message_id: Discord message ID
            
        Returns:
            Dict or None: Message data or None if not found
        """
        try:
            url = f"https://discord.com/api/v10/channels/{credentials['channel_id']}/messages/{message_id}"
            headers = {
                "Authorization": f"Bot {credentials['bot_token']}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get message details: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting message details: {e}")
            return None
    
    async def extract_button_custom_id(message_data: Dict[str, Any], variant: int) -> Optional[str]:
        """
        Extract the custom_id for a specific upscale button
        
        Args:
            message_data: Message data
            variant: Variant number (1-4)
            
        Returns:
            str or None: Button custom_id or None if not found
        """
        try:
            # Look for components
            if not message_data.get("components"):
                logger.error("No components found in message")
                return None
            
            # Check each component row
            for row in message_data["components"]:
                # Check each button in the row
                for button in row.get("components", []):
                    # Look for upscale buttons
                    if button.get("type") == 2:  # Button type
                        label = button.get("label", "")
                        if label == f"U{variant}" or label.startswith(f"U{variant}"):
                            logger.info(f"Found button with label {label}, custom_id: {button.get('custom_id')}")
                            return button.get("custom_id")
            
            logger.error(f"Could not find button U{variant} in message components")
            return None
        except Exception as e:
            logger.error(f"Error extracting button custom ID: {e}")
            return None
    
    async def fallback_get_upscale_result(variant: int) -> Optional[str]:
        """
        Fallback method to detect upscale completion with improved correlation
        
        This improved implementation ensures upscales are correctly matched to their
        parent grid image based on timestamps, prompt matching, and tracking.
        
        Args:
            variant: The variant being upscaled (1-4)
            
        Returns:
            str or None: URL of upscaled image or None if not found
        """
        # Track the time when the upscale was initiated
        start_time = time.time()
        start_timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time))
        
        # Create a set to track processed message IDs to avoid duplicates
        processed_msg_ids = set()
        
        logger.info(f"Using improved fallback method to detect U{variant} completion (after {start_timestamp})")
        
        try:
            # Get grid message details to retrieve the prompt for correlation
            grid_msg_data = await get_message_details(gen_result.grid_message_id)
            grid_prompt = ""
            
            if grid_msg_data and "**" in grid_msg_data.get("content", ""):
                content_parts = grid_msg_data.get("content", "").split("**")
                if len(content_parts) >= 3:
                    grid_prompt = content_parts[1].strip().lower()
                    logger.info(f"Extracted grid prompt for correlation: {grid_prompt}")
            
            # Try up to 15 times with 2-second intervals (30 seconds total)
            for attempt in range(15):
                # Get most recent messages, limiting to 15 at a time
                url = f"https://discord.com/api/v10/channels/{credentials['channel_id']}/messages?limit=15"
                headers = {
                    "Authorization": f"Bot {credentials['bot_token']}",
                    "Content-Type": "application/json"
                }
                
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    logger.error(f"Failed to get messages: {response.status_code}")
                    await asyncio.sleep(2)
                    continue
                
                messages = response.json()
                
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
                    
                    # More comprehensive indicators for upscale messages
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
                    
                    # Check timestamp to avoid old upscales
                    msg_time = msg.get("timestamp", "")
                    if msg_time:
                        # Convert to comparable format (remove Z and milliseconds)
                        msg_time = msg_time.replace("Z", "").split(".")[0]
                        
                        # Skip if message is older than our start time
                        if msg_time < start_timestamp:
                            logger.debug(f"Skipping old upscale message from {msg_time}")
                            continue
                    
                    # Check prompt matching if we have a grid prompt
                    if grid_prompt and "**" in msg.get("content", ""):
                        # Extract text between ** if present
                        content_parts = msg.get("content", "").split("**")
                        if len(content_parts) >= 3:
                            msg_prompt = content_parts[1].strip().lower()
                            # Skip if prompt doesn't match
                            if grid_prompt not in msg_prompt and msg_prompt not in grid_prompt:
                                logger.debug(f"Skipping message with non-matching prompt: {msg_prompt}")
                                continue
                            else:
                                logger.info(f"Prompt match found: {msg_prompt}")
                    
                    # Message passed all checks - if it has an attachment, add to valid upscales
                    if msg.get("attachments"):
                        valid_upscales.append(msg)
                
                # Sort by timestamp (newest first) if we have multiple candidates
                if valid_upscales:
                    valid_upscales.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
                    
                    # Return the URL from the most recent valid message
                    msg = valid_upscales[0]
                    logger.info(f"Detected U{variant} completion via fallback: {msg.get('id')}")
                    return valid_upscales[0]["attachments"][0]["url"]
                
                # Log progress during attempts
                if attempt % 3 == 0:
                    logger.info(f"Still waiting for U{variant} upscale completion (attempt {attempt+1}/15)...")
                
                # Sleep before next attempt
                await asyncio.sleep(2)
            
            logger.error(f"Failed to detect U{variant} completion after 15 attempts")
            return None
        except Exception as e:
            logger.error(f"Error in fallback upscale detection: {e}")
            return None
    
    # Attach the methods to the client
    client._get_message_details = get_message_details
    client._extract_button_custom_id = extract_button_custom_id
    client._fallback_get_upscale_result = fallback_get_upscale_result
    
    try:
        # Initialize client
        logger.info("Initializing client...")
        if not await client.initialize():
            logger.error("Failed to initialize client")
            sys.exit(1)
        
        # Generate image
        logger.info(f"Generating image with prompt: {prompt}")
        gen_result = await client.generate_image(prompt)
        
        if not gen_result.success:
            logger.error(f"Generation failed: {gen_result.error}")
            sys.exit(1)
        
        logger.info(f"Generation successful! Message ID: {gen_result.grid_message_id}")
        
        # Save grid image
        grid_path = await download_image(
            gen_result.image_url,
            os.path.join(output_dir, f"grid_{gen_result.grid_message_id}.png")
        )
        logger.info(f"Saved grid image to: {grid_path}")
        
        # Create prompt text file in the output directory
        prompt_path = os.path.join(output_dir, f"prompt_{time.strftime('%Y%m%d_%H%M%S')}.txt")
        try:
            with open(prompt_path, "w") as f:
                f.write(prompt)
            logger.info(f"Saved prompt to: {prompt_path}")
        except Exception as e:
            logger.error(f"Failed to save prompt file: {e}")
        
        # Skip upscaling if requested
        if skip_upscale:
            logger.info("Skipping upscale steps as requested")
            logger.info("Test completed successfully!")
            return
        
        # Wait a few seconds before upscaling to ensure message is fully processed
        logger.info("Waiting 5 seconds before upscaling...")
        await asyncio.sleep(5)
        
        # Upscale variants
        if upscale_variant is not None:
            # Upscale just one variant
            logger.info(f"Upscaling variant {upscale_variant}...")
            result = await client.upscale_variant(gen_result.grid_message_id, upscale_variant)
            
            if result.success:
                path = await download_image(
                    result.image_url,
                    os.path.join(output_dir, f"upscale_{gen_result.grid_message_id}_variant_{result.variant}.png")
                )
                logger.info(f"Saved upscale {result.variant} to: {path}")
            else:
                logger.error(f"Failed to upscale variant {upscale_variant}: {result.error}")
        else:
            # Upscale all variants
            logger.info("Upscaling all variants...")
            upscale_results = await client.upscale_all_variants(gen_result.grid_message_id)
            
            # Save upscaled images
            saved_paths = []
            for result in upscale_results:
                if result.success:
                    path = await download_image(
                        result.image_url,
                        os.path.join(output_dir, f"upscale_{gen_result.grid_message_id}_variant_{result.variant}.png")
                    )
                    saved_paths.append(str(path))
                    logger.info(f"Saved upscale {result.variant} to: {path}")
                else:
                    logger.error(f"Failed to upscale variant {result.variant}: {result.error}")
        
        logger.info("Test completed successfully!")
    
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close client
        logger.info("Closing client...")
        await client.close()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run a real Midjourney test")
    parser.add_argument("--prompt", "-p", default=None,
                       help="Prompt to use for generation (will prompt if not provided)")
    parser.add_argument("--output-dir", "-o", default="./test_output",
                       help="Directory to save results to (default: ./test_output)")
    parser.add_argument("--variant", "-v", type=int, choices=[1, 2, 3, 4], default=None,
                       help="Only upscale this variant (1-4) instead of all variants")
    parser.add_argument("--skip-upscale", "-s", action="store_true",
                       help="Skip upscaling and only generate the grid image")
    parser.add_argument("--no-confirm", "-y", action="store_true",
                       help="Skip confirmation prompts (WARNING: Will use real Midjourney credits!)")
    parser.add_argument("--mock", "-m", action="store_true",
                       help="Run in mock mode (no real API calls)")
    
    args = parser.parse_args()
    
    # Set mock mode if specified
    if args.mock:
        os.environ["MOCK_MIDJOURNEY"] = "1"
        print("Running in MOCK mode (no real API calls)")
    
    # Display warning if not using --no-confirm and not in mock mode
    if not args.no_confirm and os.environ.get("MOCK_MIDJOURNEY") != "1":
        print("\033[31mWARNING: This will use real Midjourney API calls and consume credits\033[0m")
        response = input("Are you sure you want to continue? (y/N) ")
        if not response.lower().startswith('y'):
            print("Test cancelled.")
            return
    
    # Get prompt if not provided
    prompt = args.prompt
    if not prompt:
        prompt = input("Enter prompt to generate: ")
    
    # Run the test
    asyncio.run(run_midjourney_test(prompt, args.output_dir, args.variant, args.skip_upscale))

if __name__ == "__main__":
    main() 