#!/usr/bin/env python3
"""
Multi-Provider Image Generation Script

This script demonstrates the new multi-provider system that can use Replicate
as a backup to Midjourney, providing better reliability for SiliconSentiments Art.

Usage:
    python multi_provider_generate.py [prompt] [--model MODEL] [--variations COUNT]
"""

import os
import sys
import asyncio
import logging
import argparse
import json
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.image_generator.services.multi_provider_service import (
    MultiProviderGenerationService,
    GenerationRequest,
    ProviderStrategy
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("multi_provider_generate")


def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.json or environment variables
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    # Try to load from config.json first
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_file):
        logger.info(f"Loading configuration from {config_file}")
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Fallback to environment variables
    logger.info("Loading configuration from environment variables")
    load_dotenv()
    
    config = {
        "providers": {
            "replicate": {
                "api_token": os.environ.get("REPLICATE_API_TOKEN"),
                "default_model": os.environ.get("REPLICATE_DEFAULT_MODEL", "flux_dev"),
                "max_retries": int(os.environ.get("REPLICATE_MAX_RETRIES", "3")),
                "timeout": int(os.environ.get("REPLICATE_TIMEOUT", "300"))
            }
        },
        "storage": {
            "mongodb_uri": os.environ.get("MONGODB_URI"),
            "db_name": os.environ.get("DB_NAME", "silicon_sentiments")
        },
        "generation": {
            "default_strategy": os.environ.get("DEFAULT_STRATEGY", "brand_optimized"),
            "max_concurrent_generations": int(os.environ.get("MAX_CONCURRENT", "3")),
            "max_cost_per_generation": float(os.environ.get("MAX_COST", "0.10")),
            "timeout": int(os.environ.get("GENERATION_TIMEOUT", "300"))
        }
    }
    
    # Validate required fields
    if not config["providers"]["replicate"]["api_token"]:
        raise ValueError("REPLICATE_API_TOKEN is required")
    
    return config


def enhance_prompt_for_brand(prompt: str, config: Dict[str, Any]) -> str:
    """
    Enhance prompt with SiliconSentiments brand styling
    
    Args:
        prompt: Original prompt
        config: Configuration containing brand settings
        
    Returns:
        str: Enhanced prompt
    """
    brand_settings = config.get("brand_settings", {})
    style_prompts = brand_settings.get("style_prompts", {})
    
    # Add SiliconSentiments style
    enhanced = prompt
    if "siliconsentiments_style" in style_prompts:
        enhanced += f", {style_prompts['siliconsentiments_style']}"
    
    if "instagram_optimized" in style_prompts:
        enhanced += f", {style_prompts['instagram_optimized']}"
    
    return enhanced


async def generate_for_siliconsentiments(prompt: str, **kwargs) -> Dict[str, Any]:
    """
    Generate images optimized for SiliconSentiments Art brand
    
    Args:
        prompt: Text prompt for image generation
        **kwargs: Additional generation parameters
        
    Returns:
        Dict[str, Any]: Generation results
    """
    try:
        # Load configuration
        config = load_config()
        
        # Initialize service
        service = MultiProviderGenerationService(config)
        if not await service.initialize():
            return {"success": False, "error": "Failed to initialize any providers"}
        
        # Enhance prompt for brand consistency
        enhanced_prompt = enhance_prompt_for_brand(prompt, config)
        logger.info(f"Enhanced prompt: {enhanced_prompt}")
        
        # Prepare generation request
        generation_config = config.get("generation", {})
        brand_settings = config.get("brand_settings", {})
        
        request = GenerationRequest(
            prompt=enhanced_prompt,
            metadata={
                "original_prompt": prompt,
                "brand": "siliconsentiments",
                "platform": "instagram",
                "width": brand_settings.get("preferred_dimensions", {}).get("width", 1024),
                "height": brand_settings.get("preferred_dimensions", {}).get("height", 1024),
                "negative_prompt": ", ".join(brand_settings.get("negative_prompts", [])),
                **kwargs
            },
            strategy=ProviderStrategy(generation_config.get("default_strategy", "brand_optimized")),
            max_cost=generation_config.get("max_cost_per_generation", 0.10),
            timeout=generation_config.get("timeout", 300),
            save_to_storage=True,
            variations_needed=kwargs.get("variations", 1)
        )
        
        # Generate image(s)
        if request.variations_needed > 1:
            logger.info(f"Generating {request.variations_needed} variations")
            response = await service.generate_variations(request)
        else:
            logger.info("Generating single image")
            response = await service.generate_image(request)
        
        # Close service
        await service.close()
        
        # Return results
        result = {
            "success": response.success,
            "provider_used": response.provider_used,
            "generation_id": response.generation_id,
            "image_urls": response.image_urls,
            "storage_ids": response.storage_ids,
            "cost": response.cost,
            "generation_time": response.generation_time,
            "metadata": response.metadata
        }
        
        if not response.success:
            result["error"] = response.error
        
        # Log statistics
        stats = service.get_stats()
        logger.info(f"Generation stats: {stats}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_for_siliconsentiments: {e}")
        return {"success": False, "error": str(e)}


async def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Generate images using multi-provider system")
    parser.add_argument("prompt", help="Text prompt for image generation")
    parser.add_argument("--model", help="Specific model to use (e.g., flux_dev, sdxl)")
    parser.add_argument("--variations", type=int, default=1, help="Number of variations to generate")
    parser.add_argument("--strategy", choices=["cost_optimized", "speed_optimized", "quality_optimized", "brand_optimized"], 
                       default="brand_optimized", help="Provider selection strategy")
    parser.add_argument("--no-enhance", action="store_true", help="Don't enhance prompt with brand styling")
    parser.add_argument("--output-dir", default="./output", help="Directory to save results")
    
    args = parser.parse_args()
    
    # Prepare generation parameters
    kwargs = {
        "variations": args.variations
    }
    
    if args.model:
        kwargs["model"] = args.model
    
    # Generate images
    if args.no_enhance:
        # Use original prompt without brand enhancement
        config = load_config()
        service = MultiProviderGenerationService(config)
        await service.initialize()
        
        request = GenerationRequest(
            prompt=args.prompt,
            metadata=kwargs,
            strategy=ProviderStrategy(args.strategy),
            variations_needed=args.variations
        )
        
        response = await service.generate_image(request)
        await service.close()
        
        result = {
            "success": response.success,
            "provider_used": response.provider_used,
            "image_urls": response.image_urls,
            "cost": response.cost,
            "error": response.error if not response.success else None
        }
    else:
        # Use brand-enhanced generation
        result = await generate_for_siliconsentiments(args.prompt, **kwargs)
    
    # Display results
    if result["success"]:
        print(f"✅ Generation successful!")
        print(f"Provider used: {result['provider_used']}")
        print(f"Cost: ${result['cost']:.4f}")
        print(f"Generation time: {result.get('generation_time', 0):.2f}s")
        
        if result["image_urls"]:
            print(f"Image URLs:")
            for i, url in enumerate(result["image_urls"], 1):
                print(f"  {i}. {url}")
        
        if result["storage_ids"]:
            print(f"Storage IDs:")
            for i, storage_id in enumerate(result["storage_ids"], 1):
                print(f"  {i}. {storage_id}")
    else:
        print(f"❌ Generation failed: {result['error']}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))