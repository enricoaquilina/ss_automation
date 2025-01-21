"""Generation model for tracking image generations"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

class Generation:
    def __init__(self, 
                 variation: str,
                 prompt: str,
                 upscaled_photo_url: str,
                 imagine_message_id: str,
                 midjourney_image_id: str,
                 status: str = "active",
                 metadata: Optional[Dict[str, Any]] = None):
        self.variation = variation
        self.prompt = prompt
        self.upscaled_photo_url = upscaled_photo_url
        self.imagine_message_id = imagine_message_id
        self.midjourney_image_id = midjourney_image_id
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.status = status
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert generation to dictionary format"""
        return {
            "variation": self.variation,
            "prompt": self.prompt,
            "upscaled_photo_url": self.upscaled_photo_url,
            "imagine_message_id": self.imagine_message_id,
            "midjourney_image_id": self.midjourney_image_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Generation':
        """Create Generation instance from dictionary"""
        return cls(
            variation=data["variation"],
            prompt=data["prompt"],
            upscaled_photo_url=data["upscaled_photo_url"],
            imagine_message_id=data["imagine_message_id"],
            midjourney_image_id=data["midjourney_image_id"],
            status=data.get("status", "active"),
            metadata=data.get("metadata", {})
        ) 