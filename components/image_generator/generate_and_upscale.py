#!/usr/bin/env python3
"""
Generate and Upscale Script for Midjourney

This script demonstrates how to use the Silicon Sentiments Midjourney client to:
1. Generate an image using a prompt
2. Upscale all four variants
3. Save all images to storage

Usage:
    python generate_and_upscale.py [prompt]
"""

import os
import sys
import asyncio
import logging
import argparse
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# Import from the src directory
from src.client import MidjourneyClient
from src.models import GenerationResult, UpscaleResult
from src.storage import FileSystemStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("generate_and_upscale")

def load_env_vars() -> Dict[str, str]:
    """
    Load environment variables from the appropriate .env file
    
    Returns:
        Dict[str, str]: Dictionary of environment variables
    """
    # Try to load from each possible .env file location
    env_files = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), "src", ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    
    for env_file in env_files:
        if os.path.exists(env_file):
            logger.info(f"Loading environment from {env_file}")
            load_dotenv(env_file)
            break
    
    # Check if required environment variables are set
    required_vars = [
        "DISCORD_USER_TOKEN",
        "DISCORD_BOT_TOKEN",
        "DISCORD_CHANNEL_ID",
        "DISCORD_GUILD_ID"
    ]
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return {}
    
    return {
        "DISCORD_USER_TOKEN": os.environ.get("DISCORD_USER_TOKEN"),
        "DISCORD_BOT_TOKEN": os.environ.get("DISCORD_BOT_TOKEN"),
        "DISCORD_CHANNEL_ID": os.environ.get("DISCORD_CHANNEL_ID"),
        "DISCORD_GUILD_ID": os.environ.get("DISCORD_GUILD_ID")
    }

async def generate_and_upscale(prompt: str, output_dir: str = "./output") -> Dict[str, Any]:
    """
    Generate an image with Midjourney and upscale all variants
    
    Args:
        prompt: The prompt to send to Midjourney
        output_dir: Directory to save images to
        
    Returns:
        Dict[str, Any]: Results dictionary with paths to saved images
    """
    # Load environment variables
    env_vars = load_env_vars()
    if not env_vars:
        return {"success": False, "error": "Failed to load environment variables"}
    
    # Create client
    client = MidjourneyClient(
        user_token=env_vars["DISCORD_USER_TOKEN"],
        bot_token=env_vars["DISCORD_BOT_TOKEN"],
        channel_id=env_vars["DISCORD_CHANNEL_ID"],
        guild_id=env_vars["DISCORD_GUILD_ID"]
    )
    
    # Create storage
    storage = FileSystemStorage(base_dir=output_dir)
    
    # Initialize client
    logger.info("Initializing client...")
    if not await client.initialize():
        return {"success": False, "error": "Failed to initialize client"}
    
    try:
        # Generate image
        logger.info(f"Generating image with prompt: {prompt}")
        gen_result = await client.generate_image(prompt)
        
        if not gen_result.success:
            return {"success": False, "error": f"Generation failed: {gen_result.error}"}
        
        logger.info(f"Generation successful! Message ID: {gen_result.grid_message_id}")
        
        # Save grid image
        grid_path = await storage.save_from_url(
            gen_result.image_url,
            filename=f"grid_{gen_result.grid_message_id}.png"
        )
        logger.info(f"Saved grid image to: {grid_path}")
        
        # Upscale all variants
        logger.info("Upscaling all variants...")
        upscale_results = await client.upscale_all_variants(gen_result.grid_message_id)
        
        # Save upscaled images
        saved_paths = []
        for result in upscale_results:
            if result.success:
                path = await storage.save_from_url(
                    result.image_url,
                    filename=f"upscale_{gen_result.grid_message_id}_variant_{result.variant}.png"
                )
                saved_paths.append(str(path))
                logger.info(f"Saved upscale {result.variant} to: {path}")
            else:
                logger.error(f"Failed to upscale variant {result.variant}: {result.error}")
        
        return {
            "success": True,
            "prompt": prompt,
            "grid_message_id": gen_result.grid_message_id,
            "grid_image_path": str(grid_path),
            "upscale_paths": saved_paths,
            "upscale_results": [r.to_dict() for r in upscale_results]
        }
    
    except Exception as e:
        logger.error(f"Error during generation and upscaling: {e}")
        return {"success": False, "error": str(e)}
    
    finally:
        # Close client
        logger.info("Closing client...")
        await client.close()

def main():
    """Main entry point for command line usage"""
    parser = argparse.ArgumentParser(description="Generate and upscale Midjourney images")
    parser.add_argument("prompt", nargs="?", default="beautiful sunset over mountains, digital art", 
                        help="Prompt to generate (default: beautiful sunset over mountains, digital art)")
    parser.add_argument("--output-dir", "-o", default="./output",
                        help="Directory to save images to (default: ./output)")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run the async function
    result = asyncio.run(generate_and_upscale(args.prompt, args.output_dir))
    
    if result["success"]:
        logger.info("Generation and upscaling completed successfully!")
        logger.info(f"Grid image saved to: {result['grid_image_path']}")
        logger.info(f"Upscaled images saved to: {', '.join(result['upscale_paths'])}")
    else:
        logger.error(f"Failed: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main() 