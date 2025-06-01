"""
Multi-Provider Image Generation Service

This service orchestrates image generation across multiple providers (Midjourney, Replicate, etc.)
with automatic failover, cost optimization, and provider-specific handling.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from ..providers.base import (
    BaseImageProvider,
    ProviderResult,
    ProviderType,
    GenerationStatus,
    ProviderError,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderModerationError,
    ProviderTimeoutError
)
from ..providers.replicate import ReplicateProvider
from ...storage import GridFSStorage
from ...models import GenerationResult

logger = logging.getLogger("multi_provider_service")


class ProviderStrategy(Enum):
    """Strategy for selecting providers"""
    COST_OPTIMIZED = "cost_optimized"      # Cheapest first
    SPEED_OPTIMIZED = "speed_optimized"    # Fastest first
    QUALITY_OPTIMIZED = "quality_optimized" # Best quality first
    BRAND_OPTIMIZED = "brand_optimized"    # SiliconSentiments preferred


@dataclass
class GenerationRequest:
    """Request for image generation"""
    prompt: str
    metadata: Dict[str, Any]
    provider_preferences: Optional[List[str]] = None
    strategy: ProviderStrategy = ProviderStrategy.BRAND_OPTIMIZED
    max_cost: Optional[float] = None
    timeout: int = 300
    save_to_storage: bool = True
    variations_needed: int = 1


@dataclass
class GenerationResponse:
    """Response from image generation"""
    success: bool
    provider_used: Optional[str] = None
    generation_id: Optional[str] = None
    image_urls: List[str] = None
    storage_ids: List[str] = None
    metadata: Dict[str, Any] = None
    cost: float = 0.0
    generation_time: float = 0.0
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []
        if self.storage_ids is None:
            self.storage_ids = []
        if self.metadata is None:
            self.metadata = {}


class MultiProviderGenerationService:
    """
    Service that manages multiple image generation providers with intelligent
    failover, cost optimization, and provider-specific handling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the multi-provider service
        
        Args:
            config: Configuration dictionary containing:
                - providers: Dict of provider configurations
                - storage: Storage configuration
                - default_strategy: Default provider selection strategy
                - max_concurrent_generations: Max concurrent generations
        """
        self.config = config
        self.providers: Dict[str, BaseImageProvider] = {}
        self.storage: Optional[GridFSStorage] = None
        self.default_strategy = ProviderStrategy(
            config.get("default_strategy", "brand_optimized")
        )
        self.max_concurrent = config.get("max_concurrent_generations", 3)
        
        # Track generation statistics
        self.stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "provider_usage": {},
            "total_cost": 0.0,
            "avg_generation_time": 0.0
        }
        
        # Provider priority configurations
        self.provider_priorities = {
            ProviderStrategy.COST_OPTIMIZED: ["replicate_flux_schnell", "replicate_sdxl", "midjourney"],
            ProviderStrategy.SPEED_OPTIMIZED: ["replicate_flux_schnell", "replicate_flux_dev", "midjourney"],
            ProviderStrategy.QUALITY_OPTIMIZED: ["midjourney", "replicate_flux_dev", "replicate_playground_v2"],
            ProviderStrategy.BRAND_OPTIMIZED: ["replicate_flux_dev", "replicate_playground_v2", "midjourney"]
        }
        
        logger.info("Initialized MultiProviderGenerationService")
    
    async def initialize(self) -> bool:
        """
        Initialize all configured providers
        
        Returns:
            bool: True if at least one provider initialized successfully
        """
        provider_configs = self.config.get("providers", {})
        initialized_count = 0
        
        # Initialize Replicate provider if configured
        if "replicate" in provider_configs:
            try:
                replicate_provider = ReplicateProvider(provider_configs["replicate"])
                if await replicate_provider.initialize():
                    self.providers["replicate"] = replicate_provider
                    initialized_count += 1
                    logger.info("Replicate provider initialized successfully")
                else:
                    logger.error("Failed to initialize Replicate provider")
            except Exception as e:
                logger.error(f"Error initializing Replicate provider: {e}")
        
        # TODO: Initialize Midjourney provider (existing implementation)
        # if "midjourney" in provider_configs:
        #     try:
        #         midjourney_provider = MidjourneyProvider(provider_configs["midjourney"])
        #         if await midjourney_provider.initialize():
        #             self.providers["midjourney"] = midjourney_provider
        #             initialized_count += 1
        #     except Exception as e:
        #         logger.error(f"Error initializing Midjourney provider: {e}")
        
        # Initialize storage if configured
        storage_config = self.config.get("storage")
        if storage_config:
            try:
                self.storage = GridFSStorage(
                    mongodb_uri=storage_config.get("mongodb_uri"),
                    db_name=storage_config.get("db_name", "silicon_sentiments")
                )
                logger.info("Storage initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing storage: {e}")
        
        success = initialized_count > 0
        if success:
            logger.info(f"MultiProviderService initialized with {initialized_count} providers")
        else:
            logger.error("No providers initialized successfully")
        
        return success
    
    async def generate_image(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate image using the best available provider
        
        Args:
            request: Generation request parameters
            
        Returns:
            GenerationResponse: Result of the generation
        """
        start_time = time.time()
        
        try:
            # Determine provider order based on strategy
            provider_order = self._get_provider_order(
                request.strategy, 
                request.provider_preferences
            )
            
            if not provider_order:
                return GenerationResponse(
                    success=False,
                    error="No providers available"
                )
            
            # Try providers in order until one succeeds
            last_error = None
            for provider_name in provider_order:
                if provider_name not in self.providers:
                    continue
                
                provider = self.providers[provider_name]
                
                # Check cost constraints
                if request.max_cost and provider.get_estimated_cost() > request.max_cost:
                    logger.info(f"Skipping {provider_name} due to cost constraint")
                    continue
                
                try:
                    logger.info(f"Attempting generation with {provider_name}")
                    
                    # Generate image
                    result = await self._generate_with_provider(
                        provider, 
                        provider_name,
                        request
                    )
                    
                    if result.success:
                        # Save to storage if requested
                        storage_ids = []
                        if request.save_to_storage and self.storage and result.image_data:
                            try:
                                storage_id = await self.storage.save_grid(
                                    result.image_data, 
                                    {
                                        **request.metadata,
                                        "provider": provider_name,
                                        "generation_id": result.generation_id,
                                        "prompt": request.prompt,
                                        "cost": result.cost
                                    }
                                )
                                storage_ids.append(storage_id)
                            except Exception as e:
                                logger.error(f"Failed to save to storage: {e}")
                        
                        # Update statistics
                        self._update_stats(provider_name, True, result.cost, time.time() - start_time)
                        
                        return GenerationResponse(
                            success=True,
                            provider_used=provider_name,
                            generation_id=result.generation_id,
                            image_urls=[result.image_url] if result.image_url else [],
                            storage_ids=storage_ids,
                            metadata=result.metadata or {},
                            cost=result.cost or 0.0,
                            generation_time=time.time() - start_time
                        )
                    else:
                        last_error = result.error
                        logger.warning(f"Generation failed with {provider_name}: {result.error}")
                        
                except (ProviderQuotaError, ProviderTimeoutError) as e:
                    logger.warning(f"Recoverable error with {provider_name}: {e}")
                    last_error = str(e)
                    continue
                    
                except (ProviderAuthError, ProviderModerationError) as e:
                    logger.error(f"Non-recoverable error with {provider_name}: {e}")
                    last_error = str(e)
                    # These errors might be provider-specific, so continue to next provider
                    continue
                    
                except Exception as e:
                    logger.error(f"Unexpected error with {provider_name}: {e}")
                    last_error = str(e)
                    continue
            
            # All providers failed
            self._update_stats("none", False, 0.0, time.time() - start_time)
            
            return GenerationResponse(
                success=False,
                error=f"All providers failed. Last error: {last_error}",
                generation_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in generate_image: {e}")
            self._update_stats("none", False, 0.0, time.time() - start_time)
            
            return GenerationResponse(
                success=False,
                error=f"Service error: {str(e)}",
                generation_time=time.time() - start_time
            )
    
    async def generate_variations(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate multiple variations of an image
        
        Args:
            request: Generation request (variations_needed will be used)
            
        Returns:
            GenerationResponse: Combined result for all variations
        """
        if request.variations_needed <= 1:
            return await self.generate_image(request)
        
        start_time = time.time()
        
        # For Replicate, we can generate variations efficiently
        if "replicate" in self.providers:
            provider = self.providers["replicate"]
            
            try:
                # Use Replicate's variation support if available
                if hasattr(provider, 'create_variations'):
                    results = await provider.create_variations(
                        request.prompt,
                        count=request.variations_needed,
                        **request.metadata
                    )
                    
                    # Process results
                    successful_results = [r for r in results if r.success]
                    
                    if successful_results:
                        image_urls = [r.image_url for r in successful_results if r.image_url]
                        storage_ids = []
                        total_cost = sum(r.cost or 0.0 for r in successful_results)
                        
                        # Save to storage
                        if request.save_to_storage and self.storage:
                            for i, result in enumerate(successful_results):
                                if result.image_data:
                                    try:
                                        storage_id = await self.storage.save_grid(
                                            result.image_data,
                                            {
                                                **request.metadata,
                                                "provider": "replicate",
                                                "generation_id": result.generation_id,
                                                "prompt": request.prompt,
                                                "variation_index": i,
                                                "cost": result.cost
                                            }
                                        )
                                        storage_ids.append(storage_id)
                                    except Exception as e:
                                        logger.error(f"Failed to save variation {i} to storage: {e}")
                        
                        self._update_stats("replicate", True, total_cost, time.time() - start_time)
                        
                        return GenerationResponse(
                            success=True,
                            provider_used="replicate",
                            generation_id=successful_results[0].generation_id,
                            image_urls=image_urls,
                            storage_ids=storage_ids,
                            metadata={"variations_generated": len(successful_results)},
                            cost=total_cost,
                            generation_time=time.time() - start_time
                        )
            except Exception as e:
                logger.error(f"Error generating variations with Replicate: {e}")
        
        # Fallback: Generate individual images
        logger.info(f"Generating {request.variations_needed} individual variations")
        
        tasks = []
        for i in range(request.variations_needed):
            individual_request = GenerationRequest(
                prompt=request.prompt,
                metadata={**request.metadata, "variation_index": i},
                provider_preferences=request.provider_preferences,
                strategy=request.strategy,
                max_cost=request.max_cost,
                timeout=request.timeout,
                save_to_storage=request.save_to_storage,
                variations_needed=1
            )
            tasks.append(self.generate_image(individual_request))
        
        # Wait for all generations with concurrency limit
        results = []
        for i in range(0, len(tasks), self.max_concurrent):
            batch = tasks[i:i + self.max_concurrent]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)
        
        # Process results
        successful_results = [r for r in results if isinstance(r, GenerationResponse) and r.success]
        
        if successful_results:
            all_urls = []
            all_storage_ids = []
            total_cost = 0.0
            
            for result in successful_results:
                all_urls.extend(result.image_urls)
                all_storage_ids.extend(result.storage_ids)
                total_cost += result.cost
            
            return GenerationResponse(
                success=True,
                provider_used="mixed",
                image_urls=all_urls,
                storage_ids=all_storage_ids,
                metadata={"variations_generated": len(successful_results)},
                cost=total_cost,
                generation_time=time.time() - start_time
            )
        else:
            return GenerationResponse(
                success=False,
                error="Failed to generate any variations",
                generation_time=time.time() - start_time
            )
    
    async def _generate_with_provider(self, 
                                    provider: BaseImageProvider, 
                                    provider_name: str,
                                    request: GenerationRequest) -> ProviderResult:
        """
        Generate image with a specific provider
        
        Args:
            provider: Provider instance
            provider_name: Name of the provider
            request: Generation request
            
        Returns:
            ProviderResult: Provider-specific result
        """
        # Handle Replicate provider
        if provider_name == "replicate":
            return await provider.generate_image(
                request.prompt,
                **request.metadata
            )
        
        # TODO: Handle Midjourney provider
        # elif provider_name == "midjourney":
        #     return await provider.generate_image(request.prompt)
        
        else:
            return ProviderResult(
                success=False,
                provider=provider.provider_type,
                error=f"Unknown provider: {provider_name}"
            )
    
    def _get_provider_order(self, 
                          strategy: ProviderStrategy,
                          preferences: Optional[List[str]]) -> List[str]:
        """
        Get ordered list of providers to try based on strategy
        
        Args:
            strategy: Provider selection strategy
            preferences: User-specified provider preferences
            
        Returns:
            List[str]: Ordered list of provider names
        """
        if preferences:
            # Filter preferences to only include available providers
            return [p for p in preferences if p in self.providers]
        
        # Use strategy-based ordering
        strategy_order = self.provider_priorities.get(strategy, [])
        return [p for p in strategy_order if p in self.providers]
    
    def _update_stats(self, provider: str, success: bool, cost: float, time_taken: float):
        """Update generation statistics"""
        self.stats["total_generations"] += 1
        
        if success:
            self.stats["successful_generations"] += 1
        else:
            self.stats["failed_generations"] += 1
        
        self.stats["total_cost"] += cost
        
        # Update provider usage
        if provider not in self.stats["provider_usage"]:
            self.stats["provider_usage"][provider] = {"count": 0, "cost": 0.0}
        
        self.stats["provider_usage"][provider]["count"] += 1
        self.stats["provider_usage"][provider]["cost"] += cost
        
        # Update average generation time
        total_time = self.stats["avg_generation_time"] * (self.stats["total_generations"] - 1)
        self.stats["avg_generation_time"] = (total_time + time_taken) / self.stats["total_generations"]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics"""
        return self.stats.copy()
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())
    
    async def close(self):
        """Close all providers and clean up resources"""
        for provider in self.providers.values():
            try:
                await provider.close()
            except Exception as e:
                logger.error(f"Error closing provider: {e}")
        
        self.providers.clear()
        logger.info("MultiProviderGenerationService closed")