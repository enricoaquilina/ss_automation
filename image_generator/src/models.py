"""
Data models for the Midjourney image generator.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GenerationResult:
    """Class to hold the result of an image generation"""
    success: bool
    grid_message_id: Optional[str] = None
    image_url: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "grid_message_id": self.grid_message_id,
            "image_url": self.image_url,
            "error": self.error
        }


@dataclass
class UpscaleResult:
    """Class to hold the result of an upscale operation"""
    success: bool
    variant: int  # 1-4 for U1-U4
    image_url: Optional[str] = None
    error: Optional[str] = None
    grid_message_id: Optional[str] = None  # Reference to parent grid message
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "variant": self.variant,
            "image_url": self.image_url,
            "error": self.error,
            "grid_message_id": self.grid_message_id
        } 