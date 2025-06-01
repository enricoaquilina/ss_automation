"""
Base provider interface for image generation services.

This module defines the abstract interface that all image generation providers
must implement to be compatible with the Silicon Sentiments automation system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ProviderType(Enum):
    """Enumeration of supported provider types"""
    MIDJOURNEY = "midjourney"
    REPLICATE = "replicate"
    OPENAI = "openai"
    STABILITY = "stability"


class GenerationStatus(Enum):
    """Status of a generation request"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    MODERATED = "moderated"


@dataclass
class ProviderResult:
    """Standardized result format for all providers"""
    success: bool
    provider: ProviderType
    generation_id: Optional[str] = None
    image_url: Optional[str] = None
    image_data: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cost: Optional[float] = None  # Cost in USD
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "provider": self.provider.value,
            "generation_id": self.generation_id,
            "image_url": self.image_url,
            "metadata": self.metadata,
            "error": self.error,
            "cost": self.cost
        }


@dataclass
class ProviderCapabilities:
    """Capabilities supported by a provider"""
    supports_grid_generation: bool = False
    supports_upscaling: bool = False
    supports_variations: bool = False
    supports_style_reference: bool = False
    supports_aspect_ratios: bool = False
    max_prompt_length: int = 1000
    estimated_generation_time: int = 60  # seconds
    cost_per_generation: float = 0.01  # USD


class BaseImageProvider(ABC):
    """
    Abstract base class for image generation providers.
    
    All providers must implement this interface to be compatible with
    the Silicon Sentiments automation system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider with configuration
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.provider_type = self._get_provider_type()
        self.capabilities = self._get_capabilities()
    
    @abstractmethod
    def _get_provider_type(self) -> ProviderType:
        """Return the provider type"""
        pass
    
    @abstractmethod
    def _get_capabilities(self) -> ProviderCapabilities:
        """Return the provider capabilities"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider connection/authentication
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs) -> ProviderResult:
        """
        Generate an image from a text prompt
        
        Args:
            prompt: Text prompt for image generation
            **kwargs: Provider-specific parameters
            
        Returns:
            ProviderResult: Result of the generation
        """
        pass
    
    @abstractmethod
    async def get_generation_status(self, generation_id: str) -> GenerationStatus:
        """
        Check the status of a generation request
        
        Args:
            generation_id: ID of the generation to check
            
        Returns:
            GenerationStatus: Current status of the generation
        """
        pass
    
    @abstractmethod
    async def download_image(self, image_url: str) -> Optional[bytes]:
        """
        Download image data from a URL
        
        Args:
            image_url: URL of the image to download
            
        Returns:
            Optional[bytes]: Image data or None if download failed
        """
        pass
    
    @abstractmethod
    async def close(self):
        """Clean up provider resources"""
        pass
    
    def supports_upscaling(self) -> bool:
        """Check if provider supports upscaling"""
        return self.capabilities.supports_upscaling
    
    def supports_variations(self) -> bool:
        """Check if provider supports variations"""
        return self.capabilities.supports_variations
    
    def get_estimated_cost(self) -> float:
        """Get estimated cost per generation"""
        return self.capabilities.cost_per_generation
    
    def get_estimated_time(self) -> int:
        """Get estimated generation time in seconds"""
        return self.capabilities.estimated_generation_time


class UpscaleProvider(BaseImageProvider):
    """
    Extended interface for providers that support upscaling
    """
    
    @abstractmethod
    async def upscale_variant(self, 
                            grid_generation_id: str, 
                            variant: int, 
                            **kwargs) -> ProviderResult:
        """
        Upscale a specific variant from a grid
        
        Args:
            grid_generation_id: ID of the original grid generation
            variant: Variant number to upscale (1-4)
            **kwargs: Provider-specific parameters
            
        Returns:
            ProviderResult: Result of the upscale
        """
        pass
    
    @abstractmethod
    async def upscale_all_variants(self, 
                                 grid_generation_id: str, 
                                 **kwargs) -> List[ProviderResult]:
        """
        Upscale all variants from a grid
        
        Args:
            grid_generation_id: ID of the original grid generation
            **kwargs: Provider-specific parameters
            
        Returns:
            List[ProviderResult]: Results for all upscales
        """
        pass


class VariationProvider(BaseImageProvider):
    """
    Extended interface for providers that support variations
    """
    
    @abstractmethod
    async def create_variations(self, 
                              generation_id: str, 
                              count: int = 4, 
                              **kwargs) -> List[ProviderResult]:
        """
        Create variations of an existing generation
        
        Args:
            generation_id: ID of the original generation
            count: Number of variations to create
            **kwargs: Provider-specific parameters
            
        Returns:
            List[ProviderResult]: Results for all variations
        """
        pass


class ProviderError(Exception):
    """Base exception for provider errors"""
    
    def __init__(self, message: str, provider: ProviderType, error_code: Optional[str] = None):
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code


class ProviderAuthError(ProviderError):
    """Authentication/authorization error"""
    pass


class ProviderQuotaError(ProviderError):
    """Quota/rate limit exceeded error"""
    pass


class ProviderModerationError(ProviderError):
    """Content moderation error"""
    pass


class ProviderTimeoutError(ProviderError):
    """Generation timeout error"""
    pass