"""Script to analyze posts and their image structures"""
import asyncio
from pymongo import MongoClient
from bson import ObjectId
import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from datetime import datetime, timezone
import gridfs
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        # Get MongoDB credentials from environment variables
        self.mongo_uri = os.getenv('MONGO_URI', 'localhost:27017')
        self.db_name = os.getenv('MONGO_DB_NAME', 'instagram_db')
        self.username = os.getenv('MONGO_USERNAME', 'tappiera00')
        self.password = os.getenv('MONGO_PASSWORD', 'tappiera00')
        
        # Initialize database connection with authentication
        connection_string = f"mongodb://{self.username}:{self.password}@{self.mongo_uri}/{self.db_name}?authSource=admin"
        self.client = MongoClient(connection_string)
        
        # Test connection
        try:
            self.client.admin.command('ping')
            logging.info("✓ MongoDB connection successful")
        except Exception as e:
            logging.error(f"MongoDB connection failed: {e}")
            raise

        self.db = self.client[self.db_name]
        self.fs = gridfs.GridFS(self.db)
        
        # Create indexes
        self._create_indexes()

    def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            self.db.posts.create_index([
                ('instagram_published', 1),
                ('timestamp', 1)
            ])
        except Exception as e:
            logging.warning(f"Index creation failed: {e}")

    async def find_unpublished_post(self) -> Tuple[Optional[Dict[str, Any]], Optional[list]]:
        """Find an unpublished post with multiple generations"""
        try:
            cursor = self.db.posts.find({
                'instagram_status': {'$ne': 'published'},
                'generations': {'$exists': True, '$ne': []}
            }).sort('timestamp', 1)

            for post in cursor:
                generations = post.get('generations', [])
                if not generations:
                    continue

                logging.info(f"Processing post: {post.get('shortcode')}")
                
                model_counts = {}
                for gen in generations:
                    variation = gen.get('variation')
                    if variation:
                        if variation not in model_counts:
                            model_counts[variation] = 0
                        model_counts[variation] += 1
                
                logging.info(f"Generation distribution by model: {model_counts}")

                valid_generations = []
                for gen in generations:
                    if gen and isinstance(gen, dict):
                        if all(key in gen and gen[key] for key in ['variation', 'midjourney_image_id']):
                            valid_generations.append(gen)

                if valid_generations:
                    return post, valid_generations

            logging.info("No suitable unpublished posts found")
            return None, None

        except Exception as e:
            logging.error(f"Error finding unpublished post: {e}")
            raise

    def update_post_status(self, post_id: str, status: str, instagram_id: str = None) -> None:
        """Update post status in database"""
        update_data = {
            'instagram_status': status,
            'instagram_published_at': datetime.now(timezone.utc)
        }
        if instagram_id:
            update_data['instagram_post_id'] = instagram_id

        self.db.posts.update_one(
            {'_id': post_id},
            {'$set': update_data}
        )

def analyze_specific_post(db, shortcode):
    logger.info(f"\n=== Detailed Analysis for Post {shortcode} ===")
    
    try:
        # Find the post
        post = db.posts.find_one({"shortcode": shortcode})
        if not post:
            logger.error(f"Post {shortcode} not found in posts collection")
            return
        
        logger.info(f"Post found:")
        logger.info(f"- ID: {post['_id']}")
        logger.info(f"- Created: {post.get('created_at', 'Not available')}")
        logger.info(f"- Updated: {post.get('updated_at', 'Not available')}")
        logger.info(f"- Status: {post.get('instagram_status', 'Not available')}")
        
        # Check image reference
        image_ref = post.get('image_ref')
        if not image_ref:
            logger.error("No image_ref found in post")
            return
            
        logger.info(f"Image reference found: {image_ref}")
        
        # Find post image document
        post_image = db.post_images.find_one({"_id": image_ref})
        if not post_image:
            logger.error(f"No post_image document found for ref {image_ref}")
            return
            
        logger.info("\nPost image document details:")
        logger.info(f"- Status: {post_image.get('status', 'Not available')}")
        logger.info(f"- Updated: {post_image.get('updated_at', 'Not available')}")
        
        # Check images array
        images = post_image.get('images', [])
        if not images:
            logger.error("No images array found in post_image document")
            return
            
        logger.info(f"\nFound {len(images)} images:")
        for idx, img in enumerate(images):
            logger.info(f"\nImage {idx + 1}:")
            logger.info(f"- ID: {img.get('_id', 'Not available')}")
            logger.info(f"- Filename: {img.get('filename', 'Not available')}")
            logger.info(f"- Type: {img.get('type', 'Not available')}")
            logger.info(f"- Status: {img.get('status', 'Not available')}")
            
            # Check GridFS
            try:
                grid_file = db.fs.files.find_one({"_id": img['_id']})
                if grid_file:
                    logger.info("  GridFS file exists:")
                    logger.info(f"  - Size: {grid_file.get('length', 0) / 1024:.1f} KB")
                    logger.info(f"  - Upload date: {grid_file.get('uploadDate', 'Not available')}")
                else:
                    logger.error(f"  No GridFS file found for ID {img['_id']}")
            except Exception as e:
                logger.error(f"  Error checking GridFS: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error analyzing post: {str(e)}")

def check_gridfs_files(db_manager, post_id, shortcode):
    """Check for any GridFS files associated with this post"""
    logger.info("\nChecking GridFS files...")
    try:
        # Try different patterns
        patterns = [
            f".*{post_id}.*",  # Post ID pattern
            f".*{shortcode}.*",  # Shortcode pattern
            ".*midjourney.*",  # Any Midjourney files
            ".*variant.*"  # Any variant files
        ]
        
        for pattern in patterns:
            logger.info(f"\nSearching with pattern: {pattern}")
            files = db_manager.db.fs.files.find({
                "filename": {"$regex": pattern}
            }).limit(10)  # Limit to 10 files per pattern
            
            files_list = list(files)
            if files_list:
                logger.info(f"Found {len(files_list)} files:")
                for file in files_list:
                    logger.info(f"- Filename: {file.get('filename')}")
                    logger.info(f"  Size: {file.get('length', 0) / 1024:.1f} KB")
                    logger.info(f"  Upload date: {file.get('uploadDate')}")
            else:
                logger.info("No files found with this pattern")
            
    except Exception as e:
        logger.error(f"Error checking GridFS: {str(e)}")

def analyze_shortcodes(db_manager, shortcodes):
    """Analyze a list of shortcodes for multiple upscales per variation"""
    logger.info("\n=== Analyzing Multiple Shortcodes ===")
    
    for shortcode in shortcodes:
        logger.info(f"\n{'='*50}")
        logger.info(f"Analyzing shortcode: {shortcode}")
        logger.info(f"{'='*50}")
        
        try:
            # Find the post
            post = db_manager.db.posts.find_one({"shortcode": shortcode})
            if not post:
                logger.info(f"Post not found: {shortcode}")
                continue
            
            # Log post details
            logger.info("\nPost Details:")
            logger.info(f"- ID: {post['_id']}")
            logger.info(f"- Created: {post.get('created_at')}")
            logger.info(f"- Updated: {post.get('updated_at')}")
            logger.info(f"- Status: {post.get('instagram_status')}")
            
            # Check original images array
            original_images = post.get('images', [])
            logger.info(f"\nOriginal Images: {len(original_images)}")
            for idx, img in enumerate(original_images):
                logger.info(f"\nOriginal Image {idx + 1}:")
                logger.info(f"- Description: {img.get('description')[:100]}...")  # First 100 chars
                logger.info(f"- Midjourney Generated: {img.get('midjourney_generated', False)}")
                
            # Check image reference
            image_ref = post.get('image_ref')
            if not image_ref:
                logger.info("No image_ref found - No generations saved")
                continue
                
            # Find post_images document
            post_image = db_manager.db.post_images.find_one({"_id": image_ref})
            if not post_image:
                logger.info(f"No post_images document found for ref: {image_ref}")
                continue
                
            # Check images array in post_images
            images = post_image.get('images', [])
            if not images:
                logger.info("No images array in post_images document")
                continue
                
            logger.info(f"\nPost Images Document:")
            logger.info(f"- ID: {post_image['_id']}")
            logger.info(f"- Status: {post_image.get('status')}")
            logger.info(f"- Created: {post_image.get('created_at')}")
            logger.info(f"- Updated: {post_image.get('updated_at')}")
            
            # Track variations and their upscales
            variations = defaultdict(list)
            total_generations = 0
            
            # Check each image for generations
            for img_idx, img in enumerate(images):
                logger.info(f"\nImage {img_idx + 1}:")
                logger.info(f"- Type: {img.get('type')}")
                logger.info(f"- Status: {img.get('status')}")
                
                generations = img.get('midjourney_generations', [])
                total_generations += len(generations)
                
                if generations:
                    logger.info(f"Found {len(generations)} generations:")
                    for gen in generations:
                        variation = gen.get('variation')
                        if variation:
                            variations[variation].append(gen)
                            logger.info(f"\n  Generation:")
                            logger.info(f"  - Variation: {variation}")
                            logger.info(f"  - Created: {gen.get('created_at')}")
                            logger.info(f"  - Message ID: {gen.get('imagine_message_id')}")
                            
                            # Check GridFS file
                            if 'midjourney_image_id' in gen:
                                try:
                                    grid_file = db_manager.fs.get(gen['midjourney_image_id'])
                                    logger.info(f"  - File: {grid_file.filename}")
                                    logger.info(f"  - Size: {grid_file.length / 1024:.1f} KB")
                                except Exception as e:
                                    logger.error(f"  - GridFS error: {str(e)}")
                else:
                    logger.info("No generations found for this image")
            
            # Summary for this post
            logger.info(f"\nSummary for {shortcode}:")
            logger.info(f"- Total original images: {len(original_images)}")
            logger.info(f"- Total generations saved: {total_generations}")
            logger.info(f"- Unique variations: {len(variations)}")
            for variation, gens in variations.items():
                logger.info(f"  - {variation}: {len(gens)} upscales")
                
        except Exception as e:
            logger.error(f"Error analyzing {shortcode}: {str(e)}")

def main():
    # Use DatabaseManager instead of DatabaseAnalyzer
    db_manager = DatabaseManager()
    
    # List of shortcodes to analyze
    shortcodes = [
        "C0owhP0IU5-",
        "C0pKa2AosoI",
        "C0pafmjo9fd",
        "C0pKq53oWoi",
        "C0qpGEJIQNR",
        "C0r5l8jrffm",
        "C0qn3qMhYb6",
        "C0pl_x_II1n",
        "C0r7K6mrDoG",
        "C0r8U4YN3sl",
        "C0q5otVPd8D",
        "C0rOPLPvAjO",
        "C0reEUIv3HY",
        "C0rKcsVP_bo",
        "C0rkTjbIstl"
    ]
    
    # Analyze the shortcodes
    analyze_shortcodes(db_manager, shortcodes)

if __name__ == "__main__":
    main() 