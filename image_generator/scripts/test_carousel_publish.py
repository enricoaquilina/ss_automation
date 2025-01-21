"""Script to test publishing carousels with successfully reprocessed images"""

import logging
import random
from typing import Dict, Any, List
from datetime import datetime, timezone
from image_generator.core.database import get_database
from instagram_publisher.core.publisher import InstagramPublisher
from instagram_publisher.processors.carousel import CarouselProcessor
from instagram_publisher.processors.caption import CaptionProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_successful_posts(db) -> List[Dict[str, Any]]:
    """Get list of successfully reprocessed posts with complete variations"""
    successful_posts = []
    
    try:
        posts = db.posts.find({'image_ref': {'$exists': True}})
        
        for post in posts:
            post_images = db.post_images.find_one({'_id': post['image_ref']})
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
                            if db.fs.files.find_one({'_id': gen['midjourney_image_id']}):
                                variations_found[model].append({
                                    'image_id': gen['midjourney_image_id'],
                                    'variant_idx': int(variation.split('_')[-1])
                                })
                        except Exception:
                            all_files_exist = False
                            break
            
            # Check if post has complete variations
            if (all_files_exist and 
                len(variations_found['niji']) >= 2 and 
                len(variations_found['v6.1']) >= 2 and 
                len(variations_found['v6.0']) >= 2):
                
                successful_posts.append({
                    'post_id': post['_id'],
                    'post_data': post,
                    'variations': variations_found
                })
                
        return successful_posts
        
    except Exception as e:
        logging.error(f"Error getting successful posts: {str(e)}")
        return []

def prepare_carousel_images(db, post_data: Dict[str, Any]) -> List[bytes]:
    """Prepare carousel images from variations"""
    carousel_images = []
    
    try:
        variations = post_data['variations']
        
        # Select 2 random images from each variation type
        for model in ['niji', 'v6.1', 'v6.0']:
            model_variations = variations[model]
            selected = random.sample(model_variations, 2)
            
            for var in selected:
                image_data = db.fs.get(var['image_id']).read()
                carousel_images.append(image_data)
                
        return carousel_images
        
    except Exception as e:
        logging.error(f"Error preparing carousel images: {str(e)}")
        return []

def main():
    """Main function to test carousel publishing"""
    try:
        db = get_database()
        publisher = InstagramPublisher()
        carousel_processor = CarouselProcessor()
        caption_processor = CaptionProcessor()
        
        logging.info("Getting successfully reprocessed posts...")
        successful_posts = get_successful_posts(db)
        
        logging.info(f"Found {len(successful_posts)} posts ready for carousel testing")
        
        # Process each successful post
        for idx, post_data in enumerate(successful_posts, 1):
            try:
                logging.info(f"\nProcessing post {idx}/{len(successful_posts)}")
                logging.info(f"Post ID: {post_data['post_id']}")
                
                # Prepare carousel images
                carousel_images = prepare_carousel_images(db, post_data)
                if not carousel_images:
                    logging.error("Failed to prepare carousel images")
                    continue
                    
                # Process caption
                caption = caption_processor.process(post_data['post_data'])
                
                # Create carousel
                carousel_result = carousel_processor.process(carousel_images)
                if not carousel_result:
                    logging.error("Failed to process carousel")
                    continue
                    
                # Publish post
                success = publisher.publish_carousel(
                    carousel_result,
                    caption=caption,
                    test_mode=True  # Set to False to actually publish
                )
                
                if success:
                    logging.info(f"Successfully processed carousel for post {post_data['post_id']}")
                else:
                    logging.error(f"Failed to publish carousel for post {post_data['post_id']}")
                
                # Add delay between posts if needed
                if idx < len(successful_posts):
                    time.sleep(5)  # Adjust delay as needed
                    
            except Exception as e:
                logging.error(f"Error processing post {post_data['post_id']}: {str(e)}")
                continue
                
        logging.info("\nCarousel testing completed")
        
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main() 