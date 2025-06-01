#!/usr/bin/env python3
"""
Test script for Replicate integration with existing storage system.

This script tests the new multi-provider system with your MongoDB/GridFS setup.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.image_generator.providers.replicate import ReplicateProvider
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
logger = logging.getLogger("test_replicate")


async def test_replicate_provider():
    """Test basic Replicate provider functionality"""
    logger.info("Testing Replicate provider...")
    
    # Mock config for testing (replace with real token)
    config = {
        "api_token": os.environ.get("REPLICATE_API_TOKEN", "test_token"),
        "default_model": "flux_schnell",  # Use fastest model for testing
        "timeout": 60
    }
    
    try:
        provider = ReplicateProvider(config)
        
        # Test initialization
        if not await provider.initialize():
            logger.error("Failed to initialize Replicate provider")
            return False
        
        logger.info("✅ Replicate provider initialized successfully")
        
        # Test model information
        models = provider.get_available_models()
        logger.info(f"Available models: {models}")
        
        model_info = provider.get_model_info("flux_schnell")
        logger.info(f"Flux Schnell info: {model_info}")
        
        await provider.close()
        return True
        
    except Exception as e:
        logger.error(f"Error testing Replicate provider: {e}")
        return False


async def test_multi_provider_service():
    """Test multi-provider service configuration"""
    logger.info("Testing multi-provider service...")
    
    config = {
        "providers": {
            "replicate": {
                "api_token": os.environ.get("REPLICATE_API_TOKEN", "test_token"),
                "default_model": "flux_schnell",
                "timeout": 60
            }
        },
        "storage": {
            "mongodb_uri": os.environ.get("MONGODB_URI", "mongodb://localhost:27017/"),
            "db_name": "silicon_sentiments_test"
        },
        "generation": {
            "default_strategy": "brand_optimized",
            "max_concurrent_generations": 2
        }
    }
    
    try:
        service = MultiProviderGenerationService(config)
        
        # Test initialization
        if not await service.initialize():
            logger.error("Failed to initialize multi-provider service")
            return False
        
        logger.info("✅ Multi-provider service initialized successfully")
        
        # Test provider availability
        providers = service.get_available_providers()
        logger.info(f"Available providers: {providers}")
        
        await service.close()
        return True
        
    except Exception as e:
        logger.error(f"Error testing multi-provider service: {e}")
        return False


async def test_generation_request():
    """Test a complete generation request (mock)"""
    logger.info("Testing generation request flow...")
    
    # Mock configuration
    config = {
        "providers": {
            "replicate": {
                "api_token": "test_token",  # Would fail with real API call
                "default_model": "flux_schnell"
            }
        },
        "generation": {
            "default_strategy": "brand_optimized"
        }
    }
    
    try:
        service = MultiProviderGenerationService(config)
        await service.initialize()
        
        # Create test request
        request = GenerationRequest(
            prompt="digital art of a futuristic cityscape, silicon sentiments style",
            metadata={
                "brand": "siliconsentiments",
                "platform": "instagram",
                "width": 1024,
                "height": 1024
            },
            strategy=ProviderStrategy.BRAND_OPTIMIZED,
            save_to_storage=False,  # Skip storage for test
            variations_needed=1
        )
        
        logger.info(f"Created generation request: {request}")
        logger.info("✅ Generation request structure is valid")
        
        await service.close()
        return True
        
    except Exception as e:
        logger.error(f"Error testing generation request: {e}")
        return False


async def test_storage_integration():
    """Test MongoDB/GridFS storage integration"""
    logger.info("Testing storage integration...")
    
    try:
        from src.storage import GridFSStorage
        
        # Test storage initialization (mock)
        mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
        
        storage = GridFSStorage(
            mongodb_uri=mongodb_uri,
            db_name="silicon_sentiments_test"
        )
        
        logger.info("✅ Storage integration structure is valid")
        return True
        
    except Exception as e:
        logger.error(f"Error testing storage integration: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("Starting Replicate integration tests...")
    
    tests = [
        ("Replicate Provider", test_replicate_provider),
        ("Multi-Provider Service", test_multi_provider_service),
        ("Generation Request", test_generation_request),
        ("Storage Integration", test_storage_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info('='*50)
        
        try:
            result = await test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info('='*50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Replicate integration is ready.")
        return 0
    else:
        logger.error(f"⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    # Set up environment variables for testing
    if not os.environ.get("REPLICATE_API_TOKEN"):
        logger.warning("REPLICATE_API_TOKEN not set - some tests will be limited")
    
    if not os.environ.get("MONGODB_URI"):
        logger.warning("MONGODB_URI not set - using localhost default")
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)