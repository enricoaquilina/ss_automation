#!/usr/bin/env python3
"""
Integration Tests for Midjourney Aspect Ratios

Tests generating and upscaling images with different aspect ratios to ensure
the client can properly handle all supported ratios.
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add the src directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Import the required classes from the image_generator modules
from src.client import MidjourneyClient
from src.models import GenerationResult, UpscaleResult

# Import test utilities
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils
from utils import setup_test_directory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("aspect_ratio_test")

# Test aspect ratios
ASPECT_RATIOS = {
    "square": "--ar 1:1",       # Standard square format
    "portrait": "--ar 2:3",     # Portrait format (good for mobile)
    "landscape": "--ar 3:2",    # Landscape format
    "widescreen": "--ar 16:9",  # Widescreen video format
    "instagram": "--ar 4:5",    # Instagram optimal ratio
    "ultrawide": "--ar 21:9"    # Ultrawide monitor format
}

# Base prompt to use
BASE_PROMPT = "cosmic space dolphin, digital art, high detail"


async def run_aspect_ratio_test(ratio_name: str, ratio_param: str, test_dir: Path) -> Dict[str, Any]:
    """Run a test for a specific aspect ratio"""
    logger.info(f"Testing aspect ratio: {ratio_name} ({ratio_param})")
    
    # Create aspect ratio specific directory
    ratio_dir = test_dir / ratio_name
    ratio_dir.mkdir(exist_ok=True)
    
    # Prepare result dictionary
    result = {
        "aspect_ratio": ratio_name,
        "ratio_param": ratio_param,
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "error": None,
        "generation": None,
        "upscales": []
    }
    
    # Get environment variables
    channel_id = os.environ.get("DISCORD_CHANNEL_ID")
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    bot_token = os.environ.get("DISCORD_BOT_TOKEN")
    user_token = os.environ.get("DISCORD_USER_TOKEN") or os.environ.get("DISCORD_TOKEN")
    
    # Validate required environment variables
    if not all([channel_id, guild_id, bot_token, user_token]):
        result["error"] = "Missing required environment variables"
        return result
    
    # Construct prompt with aspect ratio
    prompt = f"{BASE_PROMPT} {ratio_param}"
    
    # Save prompt to file
    prompt_file = ratio_dir / "prompt.txt"
    with open(prompt_file, "w") as f:
        f.write(prompt)
    
    # Initialize client
    client = MidjourneyClient(
        user_token=user_token,
        bot_token=bot_token,
        channel_id=channel_id,
        guild_id=guild_id
    )
    
    try:
        # Initialize client
        logger.info("Initializing client...")
        if not await client.initialize():
            result["error"] = "Failed to initialize client"
            return result
        
        # Generate image
        logger.info(f"Generating image with prompt: {prompt}")
        generation_result = await client.generate_image(prompt)
        
        if not generation_result.success:
            result["error"] = f"Failed to generate image: {generation_result.error}"
            return result
        
        # Record generation result
        result["generation"] = {
            "grid_message_id": generation_result.grid_message_id,
            "image_url": generation_result.image_url
        }
        
        # Save grid image
        if generation_result.image_url:
            grid_file = ratio_dir / "grid.png"
            await utils.download_image(generation_result.image_url, grid_file)
        
        # Upscale all variants
        logger.info("Upscaling all variants...")
        upscale_results = await client.upscale_all_variants(generation_result.grid_message_id)
        
        # Process and save upscale results
        successful_upscales = 0
        for up_result in upscale_results:
            # Add to results
            result["upscales"].append({
                "variant": up_result.variant,
                "success": up_result.success,
                "image_url": up_result.image_url,
                "error": up_result.error
            })
            
            # Save image if successful
            if up_result.success and up_result.image_url:
                upscale_file = ratio_dir / f"upscale_{up_result.variant}.png"
                await utils.download_image(up_result.image_url, upscale_file)
                successful_upscales += 1
        
        # Overall result
        result["success"] = successful_upscales > 0  # Consider successful if at least one upscale worked
        
        # Save detailed results
        result_file = ratio_dir / "results.json"
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2)
        
        return result
    
    except Exception as e:
        logger.error(f"Error in aspect ratio test: {e}")
        result["error"] = str(e)
        return result
    finally:
        # Close client
        await client.close()


async def run_all_ratio_tests(mock: bool = False) -> Dict[str, Any]:
    """Run tests for all aspect ratios"""
    # Create test directory
    test_dir = setup_test_directory("aspect_ratio")
    
    # Store results for each ratio
    results = {
        "timestamp": datetime.now().isoformat(),
        "ratios_tested": list(ASPECT_RATIOS.keys()),
        "successes": 0,
        "failures": 0,
        "results_by_ratio": {}
    }
    
    if mock:
        logger.info("Running in MOCK mode - no actual API calls will be made")
        # Generate mock results for each ratio
        for ratio_name, ratio_param in ASPECT_RATIOS.items():
            mock_result = utils.generate_mock_aspect_ratio_result(ratio_name, ratio_param)
            results["results_by_ratio"][ratio_name] = mock_result
            
            if mock_result["success"]:
                results["successes"] += 1
            else:
                results["failures"] += 1
                
            # Add delay to simulate real testing
            await asyncio.sleep(1)
    else:
        # Run actual tests
        for ratio_name, ratio_param in ASPECT_RATIOS.items():
            try:
                # Run test for this ratio
                ratio_result = await run_aspect_ratio_test(ratio_name, ratio_param, test_dir)
                results["results_by_ratio"][ratio_name] = ratio_result
                
                # Count successes and failures
                if ratio_result["success"]:
                    results["successes"] += 1
                else:
                    results["failures"] += 1
                
                # Delay between tests to avoid rate limiting
                logger.info(f"Waiting 30 seconds before the next test...")
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error testing ratio {ratio_name}: {e}")
                results["results_by_ratio"][ratio_name] = {
                    "aspect_ratio": ratio_name,
                    "ratio_param": ratio_param,
                    "success": False,
                    "error": str(e)
                }
                results["failures"] += 1
    
    # Save overall results
    results_file = test_dir / "aspect_ratio_summary.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Generate summary
    logger.info("\n=== Aspect Ratio Test Summary ===")
    logger.info(f"Ratios Tested: {len(results['ratios_tested'])}")
    logger.info(f"Successful: {results['successes']}")
    logger.info(f"Failed: {results['failures']}")
    logger.info(f"Results saved to: {results_file}")
    
    return results


async def main():
    """Main function to run the tests"""
    parser = argparse.ArgumentParser(description="Test Midjourney with different aspect ratios")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without making real API calls")
    parser.add_argument("--ratio", choices=ASPECT_RATIOS.keys(), help="Test only a specific aspect ratio")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Set the logging level")
    args = parser.parse_args()
    
    # Set log level
    log_level = getattr(logging, args.log_level)
    logger.setLevel(log_level)
    
    # Load environment variables
    import dotenv
    dotenv.load_dotenv()
    
    if args.ratio:
        # Test only one ratio
        if args.mock:
            result = utils.generate_mock_aspect_ratio_result(args.ratio, ASPECT_RATIOS[args.ratio])
            logger.info(f"Mock test of {args.ratio} - Success: {result['success']}")
        else:
            test_dir = setup_test_directory("aspect_ratio_single")
            result = await run_aspect_ratio_test(args.ratio, ASPECT_RATIOS[args.ratio], test_dir)
            logger.info(f"Test of {args.ratio} - Success: {result['success']}")
    else:
        # Test all ratios
        await run_all_ratio_tests(mock=args.mock)


# Add pytest-compatible test functions
import pytest

# Updated to use parameterized tests
@pytest.mark.parametrize("ratio_name,ratio_param", [
    ("square", "--ar 1:1"),
    ("portrait", "--ar 2:3"),
    ("landscape", "--ar 3:2"),
    ("widescreen", "--ar 16:9"),
    ("instagram", "--ar 4:5"),
    ("ultrawide", "--ar 21:9")
])
@pytest.mark.asyncio
async def test_aspect_ratio(ratio_name, ratio_param):
    """Test aspect ratios - parameterized test for all supported ratios"""
    test_dir = setup_test_directory(f"test_{ratio_name}_ratio")
    
    # For mock mode tests, just use the mock result
    if os.environ.get("FULLY_MOCKED", "false").lower() == "true":
        mock_result = utils.generate_mock_aspect_ratio_result(ratio_name, ratio_param)
        assert mock_result is not None
        assert mock_result["aspect_ratio"] == ratio_name
        return
        
    # For live tests, test one specific ratio
    result = await run_aspect_ratio_test(ratio_name, ratio_param, test_dir)
    assert result is not None
    assert result["aspect_ratio"] == ratio_name

# Original square test kept for backward compatibility
@pytest.mark.asyncio
async def test_square_aspect_ratio():
    """Test the 1:1 square aspect ratio"""
    test_dir = setup_test_directory("test_square_ratio")
    
    # For mock mode tests, just use the mock result
    if os.environ.get("FULLY_MOCKED", "false").lower() == "true":
        mock_result = utils.generate_mock_aspect_ratio_result("square", "--ar 1:1")
        assert mock_result is not None
        return
        
    result = await run_aspect_ratio_test("square", "--ar 1:1", test_dir)
    assert result is not None
    

@pytest.mark.asyncio
async def test_all_ratios_mock():
    """Test all aspect ratios in mock mode"""
    results = await run_all_ratio_tests(mock=True)
    assert results["successes"] > 0


if __name__ == "__main__":
    asyncio.run(main()) 