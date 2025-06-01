#!/usr/bin/env python3
"""
Integration Tests for Complete Midjourney Workflow

Tests the entire workflow from image generation to upscaling,
including different model versions and aspect ratios.
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock

# Add the src directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Import from the image_generator modules
from src.client import MidjourneyClient
from src.models import GenerationResult, UpscaleResult

# Import from test_adapter using a relative import
from .adapter import TestMidjourneyClient, TestGenerationResult

# Import test utilities
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import load_env_vars, save_test_results
from test_config import get_test_cases, TIMING, ASPECT_RATIOS, MODEL_VERSIONS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("integration_test")

async def run_single_test(
    client: TestMidjourneyClient, 
    prompt: str, 
    test_id: str,
    save_images: bool = True,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run a single generation and upscale test
    
    Args:
        client: Initialized TestMidjourneyClient
        prompt: Prompt to generate with
        test_id: Unique test identifier
        save_images: Whether to save the generated images
        output_dir: Directory to save images in
        
    Returns:
        Dictionary with test results
    """
    logger.info(f"Test {test_id}: Starting generation with prompt: {prompt}")
    
    start_time = datetime.now()
    
    # Generate the initial grid
    gen_result = await client.generate(prompt)
    
    if not gen_result.success:
        logger.error(f"Test {test_id}: Generation failed: {gen_result.error}")
        return {
            "test_id": test_id,
            "prompt": prompt,
            "success": False,
            "generation_success": False,
            "stage": "generation",
            "error": gen_result.error,
            "duration_seconds": (datetime.now() - start_time).total_seconds()
        }
    
    logger.info(f"Test {test_id}: Generation successful, grid available at {gen_result.image_url}")
    
    # Save grid image if requested
    grid_path = None
    if save_images and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        grid_path = os.path.join(output_dir, f"{test_id}_grid.png")
        # Save image URL to file for manual inspection
        with open(grid_path + '.url', 'w') as f:
            f.write(gen_result.image_url)
    
    # Upscale all variants
    logger.info(f"Test {test_id}: Upscaling all variants")
    upscale_results = await client.upscale_all_variants(gen_result.message_id)
    
    upscale_success = all(result.success for result in upscale_results)
    
    # Save upscaled images if requested
    upscale_paths = []
    if save_images and output_dir:
        for i, result in enumerate(upscale_results, 1):
            if result.success:
                upscale_path = os.path.join(output_dir, f"{test_id}_upscale_{i}.png")
                upscale_paths.append(upscale_path)
                # Save image URL to file for manual inspection
                with open(upscale_path + '.url', 'w') as f:
                    f.write(result.image_url)
    
    # Prepare result dictionary
    result = {
        "test_id": test_id,
        "prompt": prompt,
        "success": gen_result.success and upscale_success,
        "generation_success": gen_result.success,
        "generation_message_id": gen_result.message_id,
        "grid_image_url": gen_result.image_url,
        "upscale_results": [
            {
                "variant": result.variant,
                "success": result.success,
                "image_url": result.image_url if result.success else None,
                "error": result.error if not result.success else None
            }
            for result in upscale_results
        ],
        "upscale_success_rate": sum(1 for r in upscale_results if r.success) / len(upscale_results),
        "duration_seconds": (datetime.now() - start_time).total_seconds()
    }
    
    logger.info(f"Test {test_id}: Completed in {result['duration_seconds']:.2f} seconds")
    logger.info(f"Test {test_id}: Overall success: {result['success']}")
    
    return result

async def run_model_version_tests(
    env_vars: Dict[str, str],
    model_versions: List[str] = None,
    num_tests: int = 1,
    save_images: bool = True
) -> Dict[str, Any]:
    """
    Run tests with different model versions
    
    Args:
        env_vars: Environment variables
        model_versions: List of model versions to test
        num_tests: Number of tests per model version
        save_images: Whether to save images
        
    Returns:
        Dictionary with test results
    """
    if not model_versions:
        model_versions = list(MODEL_VERSIONS.keys())
    
    # Initialize client with our test adapter
    client = TestMidjourneyClient(
        user_token=env_vars["DISCORD_USER_TOKEN"],
        bot_token=env_vars["DISCORD_BOT_TOKEN"],
        channel_id=env_vars["DISCORD_CHANNEL_ID"],
        guild_id=env_vars["DISCORD_GUILD_ID"]
    )
    
    try:
        await client.initialize()
        
        results = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"test_results/model_versions_{timestamp}"
        
        # Run tests for each model version
        for model in model_versions:
            logger.info(f"Testing model version: {model}")
            
            # Get test cases for this model
            test_cases = get_test_cases(category="simple", count=num_tests, model=model)
            
            for i, test_case in enumerate(test_cases):
                test_id = f"model_{model}_{i+1}"
                
                # Run the test
                result = await run_single_test(
                    client=client,
                    prompt=test_case["full_prompt"],
                    test_id=test_id,
                    save_images=save_images,
                    output_dir=output_dir
                )
                
                results.append(result)
                
                # Wait between tests to avoid rate limiting
                if i < len(test_cases) - 1:
                    logger.info(f"Waiting {TIMING['delay_between_tests']} seconds before next test...")
                    await asyncio.sleep(TIMING['delay_between_tests'])
        
        # Save and return all results
        save_test_results("model_version_tests", {"results": results}, output_dir)
        return {"results": results}
        
    finally:
        # Ensure client is closed
        await client.close()

async def run_aspect_ratio_tests(
    env_vars: Dict[str, str],
    aspect_ratios: List[str] = None,
    model: str = "v6",
    num_tests: int = 1,
    save_images: bool = True
) -> Dict[str, Any]:
    """
    Run tests with different aspect ratios
    
    Args:
        env_vars: Environment variables
        aspect_ratios: List of aspect ratios to test
        model: Model version to use
        num_tests: Number of tests per aspect ratio
        save_images: Whether to save images
        
    Returns:
        Dictionary with test results
    """
    if not aspect_ratios:
        aspect_ratios = list(ASPECT_RATIOS.keys())
    
    # Initialize client with our test adapter
    client = TestMidjourneyClient(
        user_token=env_vars["DISCORD_USER_TOKEN"],
        bot_token=env_vars["DISCORD_BOT_TOKEN"],
        channel_id=env_vars["DISCORD_CHANNEL_ID"],
        guild_id=env_vars["DISCORD_GUILD_ID"]
    )
    
    try:
        await client.initialize()
        
        results = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"test_results/aspect_ratios_{timestamp}"
        
        # Run tests for each aspect ratio
        for aspect_ratio in aspect_ratios:
            logger.info(f"Testing aspect ratio: {aspect_ratio}")
            
            # Get test cases for this aspect ratio
            test_cases = get_test_cases(
                category="simple", 
                count=num_tests, 
                model=model,
                aspect_ratio=aspect_ratio
            )
            
            for i, test_case in enumerate(test_cases):
                test_id = f"aspect_{aspect_ratio}_{i+1}"
                
                # Run the test
                result = await run_single_test(
                    client=client,
                    prompt=test_case["full_prompt"],
                    test_id=test_id,
                    save_images=save_images,
                    output_dir=output_dir
                )
                
                results.append(result)
                
                # Wait between tests to avoid rate limiting
                if i < len(test_cases) - 1:
                    logger.info(f"Waiting {TIMING['delay_between_tests']} seconds before next test...")
                    await asyncio.sleep(TIMING['delay_between_tests'])
        
        # Save and return all results
        save_test_results("aspect_ratio_tests", {"results": results}, output_dir)
        return {"results": results}
        
    finally:
        # Ensure client is closed
        await client.close()

async def run_comprehensive_test(
    env_vars: Dict[str, str],
    model: str = "v6",
    aspect_ratio: Optional[str] = None,
    prompt: Optional[str] = None,
    save_images: bool = True
) -> Dict[str, Any]:
    """
    Run a single comprehensive test with detailed logging and verification
    
    Args:
        env_vars: Environment variables
        model: Model version to use
        aspect_ratio: Aspect ratio to use (optional)
        prompt: Custom prompt to use (optional)
        save_images: Whether to save images
        
    Returns:
        Dictionary with test results
    """
    # Initialize client with our test adapter
    client = TestMidjourneyClient(
        user_token=env_vars["DISCORD_USER_TOKEN"],
        bot_token=env_vars["DISCORD_BOT_TOKEN"],
        channel_id=env_vars["DISCORD_CHANNEL_ID"],
        guild_id=env_vars["DISCORD_GUILD_ID"]
    )
    
    # Set up logging
    client_logger = logging.getLogger("complete_midjourney_workflow")
    client_logger.setLevel(logging.DEBUG)
    
    try:
        await client.initialize()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"test_results/comprehensive_{timestamp}"
        
        # Prepare prompt
        if not prompt:
            test_case = get_test_cases(
                category="artistic", 
                count=1, 
                model=model,
                aspect_ratio=aspect_ratio
            )[0]
            full_prompt = test_case["full_prompt"]
        else:
            # Add model version and aspect ratio to custom prompt
            full_prompt = prompt
            if aspect_ratio:
                full_prompt += f" {ASPECT_RATIOS[aspect_ratio]}"
            full_prompt += f" {MODEL_VERSIONS[model]}"
        
        test_id = f"comprehensive_{model}"
        if aspect_ratio:
            test_id += f"_{aspect_ratio}"
        
        # Run the test
        result = await run_single_test(
            client=client,
            prompt=full_prompt,
            test_id=test_id,
            save_images=save_images,
            output_dir=output_dir
        )
        
        # Save and return the result
        save_test_results("comprehensive_test", result, output_dir)
        return result
        
    finally:
        # Ensure client is closed
        await client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run integration tests for Midjourney workflow")
    parser.add_argument("--test-type", type=str, choices=["model", "aspect", "comprehensive"], 
                        default="comprehensive", help="Type of test to run")
    parser.add_argument("--model", type=str, choices=list(MODEL_VERSIONS.keys()), 
                        default="v6", help="Model version to use")
    parser.add_argument("--aspect-ratio", type=str, choices=list(ASPECT_RATIOS.keys()), 
                        default=None, help="Aspect ratio to use")
    parser.add_argument("--prompt", type=str, default=None, 
                        help="Custom prompt to use (comprehensive test only)")
    parser.add_argument("--num-tests", type=int, default=1, 
                        help="Number of tests to run per configuration")
    parser.add_argument("--save-images", action="store_true", 
                        help="Save generated images")
    
    args = parser.parse_args()
    
    # Load environment variables
    env_vars = load_env_vars()
    
    # Run the selected test
    if args.test_type == "model":
        asyncio.run(run_model_version_tests(
            env_vars=env_vars,
            model_versions=[args.model] if args.model else None,
            num_tests=args.num_tests,
            save_images=args.save_images
        ))
    elif args.test_type == "aspect":
        asyncio.run(run_aspect_ratio_tests(
            env_vars=env_vars,
            aspect_ratios=[args.aspect_ratio] if args.aspect_ratio else None,
            model=args.model,
            num_tests=args.num_tests,
            save_images=args.save_images
        ))
    elif args.test_type == "comprehensive":
        asyncio.run(run_comprehensive_test(
            env_vars=env_vars,
            model=args.model,
            aspect_ratio=args.aspect_ratio,
            prompt=args.prompt,
            save_images=args.save_images
        ))

# Add pytest-compatible test functions
import pytest

@pytest.mark.asyncio
async def test_run_single_test_mock():
    """Test the run_single_test function with a mock client"""
    # Create a mock client
    env_vars = load_env_vars()
    if not env_vars:
        # Use dummy values if no env vars are available
        env_vars = {
            "DISCORD_USER_TOKEN": "mock_user_token",
            "DISCORD_BOT_TOKEN": "mock_bot_token",
            "DISCORD_CHANNEL_ID": "123456789",
            "DISCORD_GUILD_ID": "987654321"
        }
    
    # Initialize the test client
    client = TestMidjourneyClient(
        user_token=env_vars.get("DISCORD_USER_TOKEN", "mock_token"),
        bot_token=env_vars.get("DISCORD_BOT_TOKEN", "mock_token"),
        channel_id=env_vars.get("DISCORD_CHANNEL_ID", "123456789"),
        guild_id=env_vars.get("DISCORD_GUILD_ID", "987654321")
    )
    
    # Monkey patch the client to return mock responses
    client.generate = AsyncMock(return_value=TestGenerationResult(
        success=True,
        message_id="mock_message_id_123",
        image_url="https://example.com/mock_image.png"
    ))
    client.upscale_all_variants = AsyncMock(return_value=[
        TestGenerationResult(success=True, variant=1, image_url="https://example.com/upscale1.png"),
        TestGenerationResult(success=True, variant=2, image_url="https://example.com/upscale2.png"),
        TestGenerationResult(success=True, variant=3, image_url="https://example.com/upscale3.png"),
        TestGenerationResult(success=True, variant=4, image_url="https://example.com/upscale4.png")
    ])
    client.initialize = AsyncMock(return_value=True)
    client.close = AsyncMock(return_value=True)
    
    # Run a single test
    result = await run_single_test(
        client=client,
        prompt="test prompt for mock run",
        test_id="mock_test_123",
        save_images=False
    )
    
    # Check results
    assert result["success"] is True
    assert result["generation_success"] is True
    assert result["generation_message_id"] == "mock_message_id_123"
    assert result["grid_image_url"] == "https://example.com/mock_image.png"
    assert len(result["upscale_results"]) == 4
    assert result["upscale_success_rate"] == 1.0  # All successful 