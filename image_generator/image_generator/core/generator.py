"""Main coordinator for image generation process"""

import logging
from typing import Optional, Dict, Any, List

from ..services import GenerationService, DatabaseService

class ImageGenerator:
    """Main coordinator for image generation"""
    
    def __init__(self):
        """Initialize the image generator with required services"""
        # Initialize database and generation services
        self.db_service = DatabaseService()
        self.generation_service = GenerationService(self.db_service)
        
    def generate_images(self, 
                       post_id: str, 
                       description: str, 
                       provider: str = 'midjourney',
                       variations: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Generate images for a post
        
        Args:
            post_id: ID of the post to generate for
            description: Text description to generate from
            provider: Name of the provider to use (currently only 'midjourney' supported)
            variations: Optional list of variation options
            
        Returns:
            True if generation was successful
            
        Raises:
            ValueError: If provider is not supported
        """
        try:
            logging.info(f"Starting image generation for post {post_id}")
            logging.debug(f"Using provider: {provider}")
            logging.debug(f"Description: {description}")
            
            if provider.lower() != 'midjourney':
                raise ValueError(f"Unsupported provider: {provider}")
                
            # Use generation service to handle the process
            success = self.generation_service.generate_images(
                post_id=post_id,
                description=description,
                variations=variations
            )
            
            if success:
                logging.info(f"Successfully generated images for post {post_id}")
            else:
                logging.error(f"Failed to generate images for post {post_id}")
                
            return success
            
        except Exception as e:
            logging.error(f"Error in generate_images: {str(e)}")
            return False

def generate_images(post_id: str, 
                   description: str, 
                   provider: str = 'midjourney',
                   variations: Optional[List[Dict[str, Any]]] = None) -> bool:
    """Convenience function to generate images without explicitly creating an ImageGenerator
    
    Args:
        post_id: ID of the post to generate for
        description: Text description to generate from
        provider: Name of the provider to use
        variations: Optional list of variation options
        
    Returns:
        True if generation was successful
    """
    # Create an instance of ImageGenerator and delegate the call
    generator = ImageGenerator()
    return generator.generate_images(
        post_id=post_id,
        description=description,
        provider=provider,
        variations=variations
    ) 