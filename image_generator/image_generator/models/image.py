"""Image model for storing generated images"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

class Image:
    def __init__(self,
                 post_id: str,
                 generations: Optional[List[Dict[str, Any]]] = None):
        self.post_id = post_id
        self.generations = generations or []
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert image to dictionary format"""
        return {
            "post_id": self.post_id,
            "generations": self.generations,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Image':
        """Create Image instance from dictionary"""
        return cls(
            post_id=data["post_id"],
            generations=data.get("generations", [])
        ) 