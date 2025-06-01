"""
Storage backends for Midjourney images.

Supports both filesystem storage and MongoDB GridFS storage.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, BinaryIO, Union
from abc import ABC, abstractmethod
from pathlib import Path

# Optional imports for GridFS
try:
    from pymongo import MongoClient
    from gridfs import GridFS
    from bson import ObjectId
    GRIDFS_AVAILABLE = True
except ImportError:
    GRIDFS_AVAILABLE = False

# Configure logging
logger = logging.getLogger("midjourney_storage")


class Storage(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    async def save_grid(self, data: bytes, metadata: Dict[str, Any]) -> str:
        """
        Save grid image data
        
        Args:
            data: Binary image data
            metadata: Image metadata
            
        Returns:
            str: Unique identifier for the saved image
        """
        pass
    
    @abstractmethod
    async def save_upscale(self, data: bytes, metadata: Dict[str, Any]) -> str:
        """
        Save upscale image data
        
        Args:
            data: Binary image data
            metadata: Image metadata
            
        Returns:
            str: Unique identifier for the saved image
        """
        pass
    
    @abstractmethod
    def get_image(self, image_id: str) -> Optional[bytes]:
        """
        Retrieve image data by ID
        
        Args:
            image_id: Unique identifier for the image
            
        Returns:
            Optional[bytes]: Image data or None if not found
        """
        pass
    
    @abstractmethod
    def save_metadata(self, metadata: Dict[str, Any], image_id: str) -> bool:
        """
        Save metadata for an image
        
        Args:
            metadata: Metadata to save
            image_id: Unique identifier for the image
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass


class FileSystemStorage(Storage):
    """Filesystem storage backend for Midjourney images"""
    
    def __init__(self, base_dir: str = "midjourney_results"):
        """
        Initialize filesystem storage
        
        Args:
            base_dir: Base directory for storing images and metadata
        """
        self.result_dir = base_dir
        # These will be set by the generator function to ensure consistent timestamp/directory
        self.current_timestamp = None
        self.current_save_dir = None
        os.makedirs(self.result_dir, exist_ok=True)
        logger.info(f"Initialized filesystem storage in {self.result_dir}")
    
    async def save_grid(self, data: bytes, metadata: Dict[str, Any]) -> str:
        """
        Save grid image data to filesystem
        
        Args:
            data: Binary image data
            metadata: Image metadata
            
        Returns:
            str: Path to the saved image
        """
        # Determine the model variation from the prompt
        prompt = metadata.get("prompt", "midjourney")
        variation = "niji_6" if "--niji" in prompt.lower() else "v7_0"
        
        # Use the timestamp provided by the generator function if available
        # Otherwise, create a new one for backward compatibility
        timestamp = self.current_timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_timestamp = timestamp  # Store for upscales to match
        
        # For test_consistent_output or test_output directories, use the directory provided by the generator
        target_dir = self.current_save_dir or self.result_dir
        if not self.current_save_dir and ("test_consistent_output" in self.result_dir or "test_output" in self.result_dir):
            # Create a timestamped subfolder for this test run only if one wasn't already provided
            target_dir = os.path.join(self.result_dir, timestamp)
            os.makedirs(target_dir, exist_ok=True)
            logger.info(f"Created timestamped test directory: {target_dir}")
            
            # Store the created directory for future use
            self.current_save_dir = target_dir
        
        # Create grid image filename with model prefix
        grid_filename = f"{variation}_grid_{timestamp}_{self._sanitize_filename(prompt)}.png"
        grid_path = os.path.join(target_dir, grid_filename)
        
        # Save grid image
        with open(grid_path, "wb") as f:
            f.write(data)
        
        # Update metadata with timestamp and consistent output location
        enhanced_metadata = {
            **metadata,
            "timestamp": timestamp,
            "variation": variation,
            "storage_path": grid_path,
            "type": "grid"
        }
        
        # Save metadata
        self.save_metadata(enhanced_metadata, grid_path)
        
        # Additionally save a prompt text file with just the prompt text for reference
        prompt_path = os.path.join(target_dir, f"prompt_{timestamp}.txt")
        try:
            with open(prompt_path, "w") as f:
                f.write(prompt)
        except Exception as e:
            logger.warning(f"Failed to save prompt file: {e}")
        
        # Save a consolidated metadata file for this generation run
        consolidated_path = os.path.join(target_dir, f"generation_{timestamp}.json")
        try:
            consolidated_data = {
                "timestamp": timestamp,
                "prompt": prompt,
                "grid_message_id": metadata.get("grid_message_id", ""),
                "grid_path": grid_path,
                "upscales": []  # This will be populated by upscale_variant calls
            }
            with open(consolidated_path, "w") as f:
                json.dump(consolidated_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save consolidated metadata: {e}")
        
        logger.info(f"Saved grid image to {grid_path}")
        return grid_path
    
    async def save_upscale(self, data: bytes, metadata: Dict[str, Any]) -> str:
        """
        Save upscale image data to filesystem
        
        Args:
            data: Binary image data
            metadata: Image metadata
            
        Returns:
            str: Path to the saved image
        """
        # Get variant and format variation string for filename (replace spaces with underscores)
        variant = metadata.get("variant", 0)
        variation = metadata.get("variation", "v7.0").replace(" ", "_")
        
        # Use the timestamp provided by the generator function if available
        # Otherwise, create a new one for backward compatibility
        timestamp = self.current_timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # If self.current_save_dir is set, directly use that instead of searching
        if self.current_save_dir:
            target_dir = self.current_save_dir
        else:
            # For test_consistent_output or test_output directories, use existing directory logic
            target_dir = self.result_dir
            if "test_consistent_output" in self.result_dir or "test_output" in self.result_dir:
                # Use the existing timestamped subfolder if it exists
                subdirs = [d for d in os.listdir(self.result_dir) 
                          if os.path.isdir(os.path.join(self.result_dir, d)) 
                          and d.startswith(timestamp[:8])]  # Match today's date
                
                if subdirs:
                    # Sort by timestamp to get the most recent one
                    subdirs.sort(reverse=True)
                    target_dir = os.path.join(self.result_dir, subdirs[0])
                    logger.info(f"Using existing test directory: {target_dir}")
                    
                    # Store the found directory for future use
                    self.current_save_dir = target_dir
                else:
                    # Create a new timestamped directory
                    target_dir = os.path.join(self.result_dir, timestamp)
                    os.makedirs(target_dir, exist_ok=True)
                    logger.info(f"Created timestamped test directory: {target_dir}")
                    
                    # Store the created directory for future use
                    self.current_save_dir = target_dir
        
        # Create upscale image filename with model prefix
        upscale_filename = f"{variation}_variant_{variant}_{timestamp}.png"
        upscale_path = os.path.join(target_dir, upscale_filename)
        
        # Ensure the target directory exists
        os.makedirs(os.path.dirname(upscale_path), exist_ok=True)
        
        # Save upscale image
        with open(upscale_path, "wb") as f:
            f.write(data)
        
        # Update metadata with additional correlation information
        enhanced_metadata = {
            **metadata,
            "timestamp": timestamp,
            "variation": variation,
            "storage_path": upscale_path,
            "type": "upscale",
            "grid_message_id": metadata.get("grid_message_id", "")  # Ensure grid_message_id is included
        }
        
        # Save metadata for this individual upscale
        self.save_metadata(enhanced_metadata, upscale_path)
        
        # Update the consolidated upscales JSON file
        try:
            consolidated_path = os.path.join(target_dir, f"upscales_{timestamp}.json")
            
            # Create or load existing upscales file
            if os.path.exists(consolidated_path):
                with open(consolidated_path, "r") as f:
                    consolidated_data = json.load(f)
            else:
                prompt = metadata.get("prompt", "")
                grid_message_id = metadata.get("grid_message_id", "")
                consolidated_data = {
                    "timestamp": timestamp,
                    "prompt": prompt,
                    "grid_message_id": grid_message_id,
                    "upscales": []
                }
            
            # Add this upscale
            upscale_data = {
                "variant": variant,
                "success": True,
                "image_file": os.path.basename(upscale_path),
                "grid_message_id": metadata.get("grid_message_id", "")  # Important for correlation
            }
            
            # Check if this variant already exists
            found = False
            for i, existing in enumerate(consolidated_data["upscales"]):
                if existing.get("variant") == variant:
                    consolidated_data["upscales"][i] = upscale_data
                    found = True
                    break
            
            # Add as new if not found
            if not found:
                consolidated_data["upscales"].append(upscale_data)
            
            # Save the updated file
            with open(consolidated_path, "w") as f:
                json.dump(consolidated_data, f, indent=2)
            
            logger.info(f"Updated upscales metadata in {consolidated_path}")
        except Exception as e:
            logger.warning(f"Failed to update consolidated upscales metadata: {e}")
        
        logger.info(f"Saved upscale image to {upscale_path}")
        return upscale_path
    
    def get_image(self, image_id: str) -> Optional[bytes]:
        """
        Retrieve image data by path
        
        Args:
            image_id: Path to the image
            
        Returns:
            Optional[bytes]: Image data or None if not found
        """
        try:
            with open(image_id, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading image {image_id}: {e}")
            return None
    
    def save_metadata(self, metadata: Dict[str, Any], image_id: str) -> bool:
        """
        Save metadata for an image
        
        Args:
            metadata: Metadata to save
            image_id: Path to the image
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            metadata_path = f"{image_id}.meta.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved metadata to {metadata_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving metadata for {image_id}: {e}")
            return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a string for use as a filename
        
        Args:
            filename: String to sanitize
            
        Returns:
            str: Sanitized filename
        """
        # Remove or replace invalid filename characters
        sanitized = "".join(c if c.isalnum() or c in "-_. " else "_" for c in filename)
        # Limit length
        return sanitized[:50]


class GridFSStorage(Storage):
    """MongoDB GridFS storage backend for Midjourney images"""
    
    def __init__(self, 
                 mongodb_uri: str = None, 
                 db_name: str = "silicon_sentiments",
                 post_id: Optional[str] = None):
        """
        Initialize GridFS storage
        
        Args:
            mongodb_uri: MongoDB connection URI
            db_name: MongoDB database name
            post_id: Optional post ID to associate with images
        """
        if not GRIDFS_AVAILABLE:
            raise ImportError("GridFS storage requires pymongo to be installed")
        
        # Connect to MongoDB
        self.mongodb_uri = mongodb_uri or os.environ.get("MONGODB_URI")
        if not self.mongodb_uri:
            raise ValueError("MongoDB URI is required. Provide it as a parameter or set MONGODB_URI environment variable")
        
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[db_name]
        self.fs = GridFS(self.db)
        self.post_id = post_id
        
        logger.info(f"Initialized GridFS storage in database {db_name}")
    
    async def save_grid(self, data: bytes, metadata: Dict[str, Any]) -> str:
        """
        Save grid image data to GridFS
        
        Args:
            data: Binary image data
            metadata: Image metadata
            
        Returns:
            str: GridFS file ID
        """
        # Prepare GridFS metadata
        prompt = metadata.get("prompt", "midjourney")
        grid_filename = f"grid_{self._sanitize_filename(prompt)}.png"
        
        gridfs_metadata = {
            "is_grid": True,
            "timestamp": datetime.now(timezone.utc),
            **metadata
        }
        
        # Add post_id if available
        if self.post_id:
            gridfs_metadata["post_id"] = ObjectId(self.post_id)
        
        # Save to GridFS
        file_id = self.fs.put(
            data,
            filename=grid_filename,
            contentType="image/png",
            metadata=gridfs_metadata
        )
        
        # Update post_images collection if post_id is available
        if self.post_id:
            generation_record = {
                "file_id": file_id,
                "is_grid": True,
                "timestamp": gridfs_metadata.get("timestamp", datetime.now(timezone.utc))
            }
            
            # Add fields from metadata
            for field in ['message_id', 'prompt', 'image_url', 'grid_message_id']:
                if field in metadata:
                    generation_record[field] = metadata[field]
            
            # Update MongoDB
            result = self.db.post_images.update_one(
                {"post_id": ObjectId(self.post_id)},
                {"$push": {"generations": generation_record}},
                upsert=True
            )
            
            logger.info(f"Updated post_images record: {result.modified_count} modified, {result.upserted_id} upserted")
        
        logger.info(f"Saved grid image to GridFS with ID {file_id}")
        return str(file_id)
    
    async def save_upscale(self, data: bytes, metadata: Dict[str, Any]) -> str:
        """
        Save upscale image data to GridFS
        
        Args:
            data: Binary image data
            metadata: Image metadata
            
        Returns:
            str: GridFS file ID
        """
        # Prepare GridFS metadata
        variant = metadata.get("variant", 0)
        variation = metadata.get("variation", "v7.0")
        upscale_filename = f"{variation}_variant_{variant}.png"
        
        gridfs_metadata = {
            "is_grid": False,
            "is_upscale": True,
            "variant_idx": variant,
            "variation": variation,
            "timestamp": datetime.now(timezone.utc),
            **metadata
        }
        
        # Add post_id if available
        if self.post_id:
            gridfs_metadata["post_id"] = ObjectId(self.post_id)
        
        # Save to GridFS
        file_id = self.fs.put(
            data,
            filename=upscale_filename,
            contentType="image/png",
            metadata=gridfs_metadata
        )
        
        # Update post_images collection if post_id is available
        if self.post_id:
            generation_record = {
                "file_id": file_id,
                "is_grid": False,
                "is_upscale": True,
                "variant_idx": variant,
                "variation": variation,
                "timestamp": gridfs_metadata.get("timestamp", datetime.now(timezone.utc))
            }
            
            # Add fields from metadata
            for field in ['message_id', 'prompt', 'image_url', 'grid_message_id', 'component_id']:
                if field in metadata:
                    generation_record[field] = metadata[field]
            
            # Update MongoDB
            result = self.db.post_images.update_one(
                {"post_id": ObjectId(self.post_id)},
                {"$push": {"generations": generation_record}}
            )
            
            # Also update the post document with upscale information
            self.db.posts.update_one(
                {"_id": ObjectId(self.post_id)},
                {"$push": {"upscales": {
                    "button": variant,
                    "file_id": file_id,
                    "timestamp": gridfs_metadata.get("timestamp")
                }}}
            )
            
            logger.info(f"Updated records for variant {variant}: {result.modified_count} modified")
        
        logger.info(f"Saved upscale image to GridFS with ID {file_id}")
        return str(file_id)
    
    def get_image(self, image_id: str) -> Optional[bytes]:
        """
        Retrieve image data by GridFS ID
        
        Args:
            image_id: GridFS file ID
            
        Returns:
            Optional[bytes]: Image data or None if not found
        """
        try:
            # Convert string ID to ObjectId
            if isinstance(image_id, str):
                image_id = ObjectId(image_id)
                
            # Retrieve file from GridFS
            if self.fs.exists(image_id):
                return self.fs.get(image_id).read()
            else:
                logger.error(f"File {image_id} not found in GridFS")
                return None
        except Exception as e:
            logger.error(f"Error retrieving image {image_id}: {e}")
            return None
    
    def save_metadata(self, metadata: Dict[str, Any], image_id: str) -> bool:
        """
        Save metadata for an image
        
        Args:
            metadata: Metadata to save
            image_id: GridFS file ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert string ID to ObjectId
            if isinstance(image_id, str):
                file_id = ObjectId(image_id)
            else:
                file_id = image_id
                
            # Update file metadata
            self.db.fs.files.update_one(
                {"_id": file_id},
                {"$set": {"metadata": metadata}}
            )
            
            logger.info(f"Updated metadata for file {file_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving metadata for {image_id}: {e}")
            return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a string for use as a filename
        
        Args:
            filename: String to sanitize
            
        Returns:
            str: Sanitized filename
        """
        # Remove or replace invalid filename characters
        sanitized = "".join(c if c.isalnum() or c in "-_. " else "_" for c in filename)
        # Limit length
        return sanitized[:50] 