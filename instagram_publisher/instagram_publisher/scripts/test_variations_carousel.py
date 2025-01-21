"""Script to test publishing carousels with image variations from different models"""

import asyncio
import logging
import random
import os
from typing import Dict, Any, List, Tuple
from datetime import datetime
from collections import defaultdict
from pathlib import Path

from instagram_publisher.core.publisher import InstagramCarouselPublisher
from instagram_publisher.core.database import DatabaseManager
from instagram_publisher.processors.carousel import CarouselProcessor
from instagram_publisher.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

async def get_posts_with_multiple_upscales(db_manager: DatabaseManager) -> List[Dict[str, Any]]:
    """Get list of posts with multiple upscales for each variation type"""
    successful_posts = []
    
    try:
        # Get all posts with images, including published ones
        posts = list(db_manager.db.posts.find({
            'image_ref': {'$exists': True}
        }))
        
        for post in posts:
            post_images = db_manager.db.post_images.find_one({'_id': post['image_ref']})
            if not post_images:
                continue
                
            variations_found = defaultdict(list)
            all_files_exist = True
            
            for img in post_images.get('images', []):
                generations = img.get('midjourney_generations', [])
                
                for gen in generations:
                    variation = gen.get('variation', '')
                    
                    # Categorize by model type
                    if 'niji' in variation:
                        model = 'niji'
                    elif 'v6.1' in variation:
                        model = 'v6.1'
                    elif 'v6.0' in variation:
                        model = 'v6.0'
                    else:
                        continue
                        
                    # Verify GridFS file exists
                    if 'midjourney_image_id' in gen:
                        try:
                            if db_manager.db.fs.files.find_one({'_id': gen['midjourney_image_id']}):
                                variations_found[model].append({
                                    'image_id': gen['midjourney_image_id'],
                                    'variant_idx': int(variation.split('_')[-1]),
                                    'generation': gen
                                })
                        except Exception:
                            all_files_exist = False
                            break
            
            # Check if we have at least 2 upscales for each variation
            if (all_files_exist and 
                len(variations_found['niji']) >= 2 and 
                len(variations_found['v6.1']) >= 2 and 
                len(variations_found['v6.0']) >= 2):
                
                # Log the number of variations found
                logger.info(f"Post {post['_id']} has:")
                for model, variations in variations_found.items():
                    logger.info(f"- {len(variations)} {model} variations")
                
                successful_posts.append({
                    'post_id': post['_id'],
                    'post_data': post,
                    'variations': variations_found
                })
                
        logger.info(f"Found {len(successful_posts)} posts with multiple upscales")
        return successful_posts
        
    except Exception as e:
        logger.error(f"Error getting posts with multiple upscales: {str(e)}")
        return []

async def save_and_process_images(publisher: InstagramCarouselPublisher, post_data: Dict[str, Any]) -> List[str]:
    """Save images to disk and create carousel items"""
    item_ids = []
    
    try:
        variations = post_data['variations']
        shortcode = post_data['post_data'].get('shortcode', 'test')
        
        # Select 2 random images from each variation type in specific order
        for model in ['niji', 'v6.1', 'v6.0']:  # Order images will appear in carousel
            model_variations = variations[model]
            if len(model_variations) < 2:
                logger.error(f"Not enough {model} variations")
                return []
                
            # Select 2 random variations
            selected = random.sample(model_variations, 2)
            logger.info(f"Selected {model} variations with indices: {[v['variant_idx'] for v in selected]}")
            
            for idx, var in enumerate(selected):
                # Save image to disk
                filename = f"post_{shortcode}_{model}_{idx}.jpg"
                image_path = publisher.path_config.instagram_images_dir / filename
                
                if not publisher.image_processor.save_image_from_gridfs(var['generation'], str(image_path)):
                    logger.error(f"Failed to save image: {filename}")
                    return []
                
                # Create carousel item
                image_url = f"{settings.IMAGE_HOST}/{filename}"
                item_id = await publisher.carousel_processor.create_carousel_item(image_url)
                if not item_id:
                    logger.error(f"Failed to create carousel item for {filename}")
                    return []
                    
                item_ids.append(item_id)
                await asyncio.sleep(2)  # Small delay between items
                
        return item_ids
        
    except Exception as e:
        logger.error(f"Error saving and processing images: {str(e)}")
        return []

async def process_post(publisher: InstagramCarouselPublisher, post_data: Dict[str, Any], db_manager: DatabaseManager) -> bool:
    """Process a single post for carousel publishing"""
    try:
        logger.info(f"Processing post {post_data['post_id']}")
        
        # Save images and create carousel items
        item_ids = await save_and_process_images(publisher, post_data)
        if not item_ids or len(item_ids) != 6:
            logger.error("Failed to prepare all carousel items")
            return False
            
        # Generate caption using existing processor
        caption = await publisher.caption_generator.generate_caption(
            post_data['post_data'].get('prompt', ''),
            post_data['post_data']
        )
        
        # Create and publish carousel
        logger.info("Creating carousel container...")
        container_id = await publisher.carousel_processor.create_carousel_container(item_ids, caption)
        if not container_id:
            logger.error("Failed to create carousel container")
            return False
            
        logger.info("Publishing carousel...")
        result = await publisher.carousel_processor.publish_container(container_id)
        if not result:
            logger.error("Failed to publish carousel")
            return False
            
        logger.info(f"Successfully published carousel for post {post_data['post_id']}")
        logger.info(f"Instagram post ID: {result.get('id')} - Delete this post after testing")
        
        # Cleanup temporary files
        shortcode = post_data['post_data'].get('shortcode', 'test')
        publisher.image_processor.cleanup_images(shortcode)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing post: {str(e)}")
        return False

async def main():
    """Main function to test carousel publishing"""
    try:
        db_manager = DatabaseManager(logger)
        publisher = InstagramCarouselPublisher()
        
        logger.info("Getting posts with multiple upscales...")
        successful_posts = await get_posts_with_multiple_upscales(db_manager)
        
        if not successful_posts:
            logger.info("No suitable posts found for testing")
            return
            
        # Process first post with multiple upscales
        post_data = successful_posts[0]
        logger.info(f"\nProcessing test post {post_data['post_id']}")
        
        success = await process_post(publisher, post_data, db_manager)
        if success:
            logger.info("Carousel publishing completed successfully")
        else:
            logger.error("Carousel publishing failed")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 