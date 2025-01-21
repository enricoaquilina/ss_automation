"""Database manager for Instagram publisher"""
import logging
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from ..config import settings
from pymongo import MongoClient
from gridfs import GridFS

class DatabaseManager:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize MongoDB connection
        self.client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=300000,
            waitQueueTimeoutMS=30000,
            maxPoolSize=10,
            retryWrites=True
        )
        
        # Get database
        self.db = self.client[settings.DB_NAME]
        
        # Initialize GridFS
        self.fs = AsyncIOMotorGridFSBucket(self.db)
        
        # Get collections
        self.posts = self.db.posts
        self.post_images = self.db.post_images
        
        self.logger.info("✓ MongoDB connection successful")

    async def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict]:
        """Find a single document in the specified collection"""
        try:
            result = await getattr(self.db, collection).find_one(query)
            return result
        except Exception as e:
            self.logger.error(f"Error finding document in {collection}: {e}")
            return None

    async def update_one(self, collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """Update a single document in the specified collection"""
        try:
            result = await getattr(self.db, collection).update_one(query, update)
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Error updating document in {collection}: {e}")
            return False

    async def insert_one(self, collection: str, document: Dict[str, Any]) -> Optional[str]:
        """Insert a single document into the specified collection"""
        try:
            result = await getattr(self.db, collection).insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            self.logger.error(f"Error inserting document into {collection}: {e}")
            return None 

    async def find(self, collection: str, query: dict) -> List[Dict]:
        """Find multiple documents in the specified collection"""
        try:
            cursor = self.db[collection].find(query)
            documents = await cursor.to_list(length=None)  # None means no limit
            return documents
        except Exception as e:
            self.logger.error(f"Error in find: {e}")
            return [] 