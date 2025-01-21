from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

class ImageGenerationProvider(ABC):
    """Base class for image generation providers"""
    
    @abstractmethod
    def generate(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate an image from a prompt
        
        Args:
            prompt: The text prompt to generate from
            options: Provider-specific options
            
        Returns:
            Dict containing generation results including:
            - id: Unique identifier for this generation
            - images: List of generated image data
            - metadata: Provider-specific metadata
        """
        pass
    
    @abstractmethod
    def get_variations(self, generation_id: str, count: int = 4) -> List[Dict[str, Any]]:
        """Get variations of a generated image
        
        Args:
            generation_id: ID of the original generation
            count: Number of variations to generate
            
        Returns:
            List of variation data dictionaries
        """
        pass
    
    @abstractmethod
    def upscale(self, generation_id: str, variation_index: int) -> Dict[str, Any]:
        """Upscale a specific variation
        
        Args:
            generation_id: ID of the original generation
            variation_index: Index of the variation to upscale
            
        Returns:
            Dict containing upscaled image data
        """
        pass
        
    @abstractmethod
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a message by ID
        
        Args:
            message_id: Message ID to retrieve
            
        Returns:
            Message data if found, None otherwise
        """
        pass
        
    def format_generation_data(self, generation_id: str, prompt: str, 
                             image_url: str, image_id: str, 
                             variation: str = None) -> Dict[str, Any]:
        """Format generation data in a consistent structure
        
        Args:
            generation_id: Unique ID for this generation
            prompt: Original generation prompt
            image_url: URL of the generated image
            image_id: GridFS ID of the stored image
            variation: Optional variation identifier
            
        Returns:
            Standardized generation data dictionary
        """
        return {
            "variation": variation,
            "prompt": prompt,
            "upscaled_photo_url": image_url,
            "imagine_message_id": generation_id,
            "midjourney_image_id": image_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "status": "active",
            "metadata": {
                "provider": self.__class__.__name__,
                "original_filename": f"{self.__class__.__name__.lower()}_{prompt[:30]}_{variation}.jpg",
                "content_type": "image/jpeg"
            }
        } 