"""
Replicate provider implementation for AI image generation.

This module implements the BaseImageProvider interface for Replicate API,
providing access to multiple state-of-the-art image generation models.
"""

import asyncio
import logging
import time
import aiohttp
from typing import Dict, Any, Optional, List
import replicate
from replicate.exceptions import ReplicateError

from ..base import (
    BaseImageProvider, 
    ProviderResult, 
    ProviderType, 
    ProviderCapabilities,
    GenerationStatus,
    ProviderError,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderModerationError,
    ProviderTimeoutError
)
from .models import (
    ReplicateModel, 
    AVAILABLE_MODELS, 
    BRAND_PREFERRED_MODELS,
    suggest_model_for_prompt,
    get_model_by_name
)

logger = logging.getLogger("replicate_provider")


class ReplicateProvider(BaseImageProvider):
    """
    Replicate API provider for image generation.
    
    Supports multiple models with automatic fallback and cost optimization.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Replicate provider
        
        Args:
            config: Configuration dictionary containing:
                - api_token: Replicate API token
                - default_model: Default model to use (optional)
                - preferred_models: List of preferred models (optional)
                - max_retries: Maximum retry attempts (default: 3)
                - timeout: Generation timeout in seconds (default: 300)
        """
        super().__init__(config)
        
        self.api_token = config.get("api_token")
        if not self.api_token:
            raise ValueError("Replicate API token is required")
        
        self.default_model = config.get("default_model", "flux_dev")
        self.preferred_models = config.get("preferred_models", BRAND_PREFERRED_MODELS)
        self.max_retries = config.get("max_retries", 3)
        self.timeout = config.get("timeout", 300)
        
        # Set up replicate client
        replicate.api_token = self.api_token
        
        # Track active generations
        self.active_generations = {}
        
        logger.info(f"Initialized Replicate provider with default model: {self.default_model}")
    
    def _get_provider_type(self) -> ProviderType:
        """Return provider type"""
        return ProviderType.REPLICATE
    
    def _get_capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities"""
        return ProviderCapabilities(
            supports_grid_generation=False,  # Replicate generates single images
            supports_upscaling=True,         # Via upscaling models
            supports_variations=True,        # Via seed variation
            supports_style_reference=True,   # Via image prompts
            supports_aspect_ratios=True,     # Configurable dimensions
            max_prompt_length=2000,
            estimated_generation_time=30,
            cost_per_generation=0.02
        )
    
    async def initialize(self) -> bool:
        """
        Initialize the provider connection
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Test API connection by listing models
            # Note: replicate.models.list() is sync, so we'll do a simple validation
            test_model = get_model_by_name(self.default_model)
            if not test_model:
                logger.error(f"Default model {self.default_model} not found")
                return False
            
            logger.info("Replicate provider initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Replicate provider: {e}")
            return False
    
    async def generate_image(self, prompt: str, **kwargs) -> ProviderResult:
        """
        Generate an image using Replicate
        
        Args:
            prompt: Text prompt for image generation
            **kwargs: Additional parameters:
                - model: Specific model to use
                - width: Image width (default: 1024)
                - height: Image height (default: 1024)
                - seed: Random seed for reproducibility
                - negative_prompt: Negative prompt text
                - guidance_scale: How closely to follow prompt
                - num_inference_steps: Quality vs speed tradeoff
                - style: Style preference for model selection
                
        Returns:
            ProviderResult: Generation result
        """
        start_time = time.time()
        
        # Determine which model to use
        model_name = kwargs.get("model")
        if not model_name:
            style = kwargs.get("style", "general")
            if style == "auto":
                model_name = suggest_model_for_prompt(prompt)
            else:
                model_name = self.default_model
        
        model_config = get_model_by_name(model_name)
        if not model_config:
            return ProviderResult(
                success=False,
                provider=self.provider_type,
                error=f"Model {model_name} not found"
            )
        
        try:
            # Prepare generation parameters
            params = model_config.default_params.copy()
            
            # Override with user parameters
            params.update({
                "prompt": prompt,
                "width": kwargs.get("width", params.get("width", 1024)),
                "height": kwargs.get("height", params.get("height", 1024))
            })
            
            # Add optional parameters if provided
            if "seed" in kwargs and kwargs["seed"] is not None:
                params["seed"] = kwargs["seed"]
            
            if "negative_prompt" in kwargs and model_config.supports_negative_prompt:
                params["negative_prompt"] = kwargs["negative_prompt"]
                
            if "guidance_scale" in kwargs:
                params["guidance_scale"] = kwargs["guidance_scale"]
                
            if "num_inference_steps" in kwargs:
                params["num_inference_steps"] = kwargs["num_inference_steps"]
            
            logger.info(f"Generating image with {model_name}: {prompt[:100]}...")
            logger.debug(f"Generation parameters: {params}")
            
            # Run generation with timeout
            try:
                # Use replicate.run in a thread to avoid blocking
                loop = asyncio.get_event_loop()
                output = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: replicate.run(
                            model_config.get_full_model_path(),
                            input=params
                        )
                    ),
                    timeout=self.timeout
                )
                
                # Handle different output formats
                image_url = None
                if isinstance(output, list) and output:
                    image_url = output[0] if isinstance(output[0], str) else str(output[0])
                elif isinstance(output, str):
                    image_url = output
                else:
                    image_url = str(output)
                
                if not image_url:
                    return ProviderResult(
                        success=False,
                        provider=self.provider_type,
                        error="No image URL returned from model"
                    )
                
                # Download image data
                image_data = await self.download_image(image_url)
                
                generation_time = time.time() - start_time
                
                return ProviderResult(
                    success=True,
                    provider=self.provider_type,
                    generation_id=f"replicate_{int(start_time)}",
                    image_url=image_url,
                    image_data=image_data,
                    metadata={
                        "model": model_name,
                        "prompt": prompt,
                        "parameters": params,
                        "generation_time": generation_time,
                        "estimated_cost": model_config.cost_per_run
                    },
                    cost=model_config.cost_per_run
                )
                
            except asyncio.TimeoutError:
                raise ProviderTimeoutError(
                    f"Generation timed out after {self.timeout} seconds",
                    self.provider_type
                )
                
        except ReplicateError as e:
            error_msg = str(e)
            
            # Handle specific Replicate errors
            if "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                raise ProviderAuthError(
                    f"Authentication failed: {error_msg}",
                    self.provider_type
                )
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                raise ProviderQuotaError(
                    f"Quota exceeded: {error_msg}",
                    self.provider_type
                )
            elif "nsfw" in error_msg.lower() or "safety" in error_msg.lower():
                raise ProviderModerationError(
                    f"Content moderated: {error_msg}",
                    self.provider_type
                )
            else:
                return ProviderResult(
                    success=False,
                    provider=self.provider_type,
                    error=f"Replicate error: {error_msg}"
                )
                
        except Exception as e:
            logger.error(f"Unexpected error in Replicate generation: {e}")
            return ProviderResult(
                success=False,
                provider=self.provider_type,
                error=f"Unexpected error: {str(e)}"
            )
    
    async def generate_with_fallback(self, prompt: str, **kwargs) -> ProviderResult:
        """
        Generate image with automatic fallback to other models
        
        Args:
            prompt: Text prompt
            **kwargs: Generation parameters
            
        Returns:
            ProviderResult: Result from first successful model
        """
        models_to_try = kwargs.get("models", self.preferred_models[:3])  # Try top 3
        
        last_error = None
        for model_name in models_to_try:
            try:
                logger.info(f"Attempting generation with {model_name}")
                result = await self.generate_image(prompt, model=model_name, **kwargs)
                
                if result.success:
                    logger.info(f"Successfully generated with {model_name}")
                    return result
                else:
                    last_error = result.error
                    logger.warning(f"Generation failed with {model_name}: {result.error}")
                    
            except (ProviderQuotaError, ProviderTimeoutError) as e:
                logger.warning(f"Recoverable error with {model_name}: {e}")
                last_error = str(e)
                continue
            except (ProviderAuthError, ProviderModerationError) as e:
                # These errors won't be fixed by trying other models
                logger.error(f"Non-recoverable error: {e}")
                return ProviderResult(
                    success=False,
                    provider=self.provider_type,
                    error=str(e)
                )
        
        return ProviderResult(
            success=False,
            provider=self.provider_type,
            error=f"All models failed. Last error: {last_error}"
        )
    
    async def get_generation_status(self, generation_id: str) -> GenerationStatus:
        """
        Check generation status (Replicate runs are synchronous, so always completed)
        
        Args:
            generation_id: Generation ID
            
        Returns:
            GenerationStatus: Status of the generation
        """
        # Replicate runs are synchronous, so if we have an ID, it's completed
        if generation_id in self.active_generations:
            return GenerationStatus.COMPLETED
        else:
            return GenerationStatus.FAILED
    
    async def download_image(self, image_url: str) -> Optional[bytes]:
        """
        Download image data from URL
        
        Args:
            image_url: URL of the image
            
        Returns:
            Optional[bytes]: Image data or None if download failed
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download image: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None
    
    async def create_variations(self, base_prompt: str, count: int = 4, **kwargs) -> List[ProviderResult]:
        """
        Create variations by using different seeds
        
        Args:
            base_prompt: Base prompt for variations
            count: Number of variations to create
            **kwargs: Additional parameters
            
        Returns:
            List[ProviderResult]: List of variation results
        """
        results = []
        base_seed = kwargs.get("seed", int(time.time()))
        
        for i in range(count):
            variation_kwargs = kwargs.copy()
            variation_kwargs["seed"] = base_seed + i
            
            result = await self.generate_image(base_prompt, **variation_kwargs)
            results.append(result)
            
            # Small delay between generations to avoid rate limits
            await asyncio.sleep(1)
        
        return results
    
    def get_available_models(self) -> List[str]:
        """Get list of available model names"""
        return list(AVAILABLE_MODELS.keys())
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model"""
        model = get_model_by_name(model_name)
        if model:
            return {
                "name": model.name,
                "category": model.category.value,
                "description": model.description,
                "cost_per_run": model.cost_per_run,
                "avg_runtime": model.avg_runtime,
                "supports_negative_prompt": model.supports_negative_prompt
            }
        return None
    
    async def close(self):
        """Clean up provider resources"""
        # Clear active generations
        self.active_generations.clear()
        logger.info("Replicate provider closed")