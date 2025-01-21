"""Database service for handling MongoDB operations"""

import os
import logging
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
import gridfs
from datetime import datetime, timezone

from ..models import Generation, Image

class DatabaseService:
    """Service to manage database operations"""
    
    def __init__(self, uri: Optional[str] = None):
        """Initialize database service
        
        Args:
            uri: MongoDB connection URI (defaults to env var)
        """
        self.uri = uri or os.getenv('MONGODB_URI')
        if not self.uri:
            raise ValueError("MONGODB_URI environment variable is not set")
            
        self.client = self._init_client()
        self.db = self.client['instagram_db']
        self.fs = gridfs.GridFS(self.db)
        
    def _init_client(self) -> MongoClient:
        """Initialize MongoDB client"""
        try:
            client = MongoClient(self.uri, serverSelectionTimeoutMS=5000, authSource='admin')
            client.admin.command('ping')
            return client
        except Exception as e:
            logging.error(f"DB Connection error: {str(e)}")
            raise
            
    def save_generation(self, post_id: str, generation: Generation) -> bool:
        """Save a single generation to database"""
        try:
            # Get post_images document
            post = self.db.posts.find_one({'_id': post_id})
            if not post or 'image_ref' not in post:
                logging.error(f"Post {post_id} not found or has no image_ref")
                return False
                
            post_images = self.db.post_images.find_one({'_id': post['image_ref']})
            if not post_images:
                logging.error(f"Post_images document not found for {post_id}")
                return False
                
            # Update or append generation data
            generation_dict = generation.to_dict()
            updated = False
            
            for img in post_images.get('images', []):
                generations = img.get('midjourney_generations', [])
                
                # Check if this variation already exists
                existing_idx = next((i for i, g in enumerate(generations) 
                                   if g.get('variation') == generation.variation), None)
                                   
                if existing_idx is not None:
                    # Update existing generation
                    generations[existing_idx] = generation_dict
                    updated = True
                else:
                    # Append new generation
                    generations.append(generation_dict)
                    updated = True
                    
                img['midjourney_generations'] = generations
                img['updated_at'] = datetime.now(timezone.utc)
                
            if not updated:
                logging.error("No generations were updated or added")
                return False
                
            # Save changes
            result = self.db.post_images.update_one(
                {'_id': post['image_ref']},
                {'$set': {
                    'images': post_images['images'],
                    'updated_at': datetime.now(timezone.utc)
                }}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logging.error(f"Error saving generation: {str(e)}")
            return False
            
    def verify_generation(self, post_id: str, generation: Generation) -> bool:
        """Verify that a generation was properly saved"""
        try:
            # Get post document
            post = self.db.posts.find_one({'_id': post_id})
            if not post or 'image_ref' not in post:
                logging.error(f"Post {post_id} not found or has no image_ref")
                return False
                
            # Get post_images document
            post_images = self.db.post_images.find_one({'_id': post['image_ref']})
            if not post_images:
                logging.error(f"Post_images document not found for {post_id}")
                return False
                
            # Find matching generation
            for img in post_images.get('images', []):
                for gen in img.get('midjourney_generations', []):
                    if gen.get('variation') == generation.variation:
                        # Verify GridFS file exists
                        try:
                            self.fs.get(gen['midjourney_image_id'])
                            return True
                        except Exception as e:
                            logging.error(f"Failed to get GridFS file: {str(e)}")
                            return False
                            
            logging.error(f"Generation {generation.variation} not found")
            return False
            
        except Exception as e:
            logging.error(f"Error verifying generation: {str(e)}")
            return False