"""Image processing operations"""
from typing import Optional, List, Dict
import os
import stat
from bson import ObjectId
import asyncio
from pathlib import Path
import logging
from ..config import settings

class ImageProcessor:
    def __init__(self, publisher):
        self.publisher = publisher
        self.logger = publisher.logger
        self.fs = publisher.db.fs
        self.instagram_images_dir = publisher.path_config.instagram_images_dir

    async def save_image_from_gridfs(self, variation_data: dict, output_path: str) -> bool:
        """Save image from GridFS using either message ID or direct GridFS ID"""
        try:
            gridfs_id = variation_data.get('midjourney_image_id')
            if not gridfs_id:
                return False
                
            if isinstance(gridfs_id, str):
                gridfs_id = ObjectId(gridfs_id)
                
            # Use async GridFS download
            grid_out = await self.fs.open_download_stream(gridfs_id)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Read the entire file content
            content = await grid_out.read()
            
            # Write to file
            with open(output_path, 'wb') as f:
                f.write(content)
                
            os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            return True
                
        except Exception as e:
            self.logger.error(f"Error saving file: {str(e)}")
            return False

    async def process_generations(self, post: dict, generations: List[dict]) -> List[str]:
        """Process generations and create carousel items"""
        item_ids = []
        for generation in generations:
            try:
                if 'midjourney_image_id' not in generation:
                    self.logger.error(f"Missing midjourney_image_id in generation: {generation}")
                    continue

                filename = f"post_{post['shortcode']}_{generation['variation']}.jpg"
                image_path = self.instagram_images_dir / filename

                self.logger.info(f"Processing variation: {generation['variation']}")
                
                if await self._process_single_generation(generation, image_path, filename):
                    item_id = await self._create_carousel_item_with_retry(filename)
                    if item_id:
                        item_ids.append(item_id)
                    
            except Exception as e:
                self.logger.error(f"Error processing generation: {str(e)}")
                continue
                
        return item_ids

    async def _process_single_generation(self, generation: dict, image_path: Path, filename: str) -> bool:
        """Process a single generation and save its image"""
        if not self.save_image_from_gridfs(generation, str(image_path)):
            self.logger.error(f"Failed to save image from GridFS: {filename}")
            return False

        if not os.path.exists(image_path):
            self.logger.error(f"File not found after save: {image_path}")
            return False
            
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            self.logger.error(f"Empty file created: {image_path}")
            return False
            
        self.logger.info(f"File ready for upload: {image_path} ({file_size} bytes)")
        return True

    async def _create_carousel_item_with_retry(self, filename: str) -> Optional[str]:
        """Create carousel item with retries"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                image_url = f"{settings.IMAGE_HOST}/{filename}"
                item_id = await self.publisher.carousel_processor.create_carousel_item(image_url)
                if item_id:
                    self.logger.info(f"Created carousel item: {item_id}")
                    await asyncio.sleep(2)
                    return item_id
                    
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                    
            except Exception as e:
                self.logger.error(f"Carousel item creation failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    raise
        return None
    
    def cleanup_images(self, shortcode: str) -> None:
        """Clean up temporary image files"""
        try:
            for file in self.instagram_images_dir.glob(f"post_{shortcode}_*.jpg"):
                file.unlink()
                self.logger.info(f"Cleaned up file: {file}")
        except Exception as e:
            self.logger.warning(f"Error cleaning up images: {e}")
