"""Main Instagram Publisher class"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from ..processors.carousel import CarouselProcessor
from ..processors.image import ImageProcessor
from ..processors.caption import CaptionGenerator
from .token_manager import InstagramTokenManager
from .database import DatabaseManager
from ..config import settings
import logging
import random
import os
import asyncio
from datetime import datetime, timezone
import httpx
import replicate

@dataclass
class InstagramConfig:
    app_id: str
    app_secret: str
    long_token: str
    account_id: str
    api_version: str = "v21.0"

@dataclass
class PathConfig:
    base_path: Path
    instagram_images_dir: Path
    log_dir: Path

class InstagramCarouselPublisher:
    def __init__(self):
        # Setup logging first
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

        # Initialize configs
        self.instagram_config = InstagramConfig(
            app_id=os.getenv("INSTAGRAM_APP_ID"),
            app_secret=os.getenv("INSTAGRAM_APP_SECRET"),
            long_token=os.getenv("INSTAGRAM_LONG_TOKEN"),
            account_id=os.getenv("INSTAGRAM_ACCOUNT_ID")
        )
        self.path_config = PathConfig(
            base_path=settings.BASE_PATH,
            instagram_images_dir=settings.INSTAGRAM_IMAGES_DIR,
            log_dir=settings.LOG_DIR
        )
        self.access_token = os.getenv("INSTAGRAM_LONG_TOKEN")

        # Set paths from config
        self.instagram_images_dir = self.path_config.instagram_images_dir
        # Ensure directory exists
        os.makedirs(self.instagram_images_dir, exist_ok=True)
        
        # Initialize components
        self.db = DatabaseManager(self.logger)
        self.token_manager = InstagramTokenManager()
        self.carousel_processor = CarouselProcessor(self)
        self.image_processor = ImageProcessor(self)
        self.caption_generator = CaptionGenerator(self)

    async def ensure_valid_token(self) -> bool:
        """Ensures a valid access token is available"""
        try:
            self.access_token = await self.token_manager.get_valid_token()
            if not self.access_token:
                self.logger.error("Failed to obtain valid access token")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Token validation failed: {e}")
            return False

    async def verify_api_access(self) -> bool:
        """Verify Instagram API access and rate limits"""
        try:
            if not self.access_token:
                self.logger.error("No access token available")
                return False

            url = f"https://graph.facebook.com/{settings.API_VERSION}/{self.instagram_config.account_id}/content_publishing_limit"
            params = {"access_token": self.access_token}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                data = response.json()

                if 'error' in data:
                    self.logger.error(f"API Error: {data['error'].get('message')}")
                    return False

                quota_usage = data.get('data', [{}])[0].get('quota_usage', 0)
                if quota_usage >= 50:  # If we've used more than 50% of our quota
                    self.logger.warning(f"High API quota usage: {quota_usage}%")
                    return False

                return True

        except Exception as e:
            self.logger.error(f"API access verification failed: {e}")
            return False

    def generate_hashtags(self) -> str:
        """Generate random hashtags for posts"""
        try:
            # Always include #siliconsentiments first
            hashtags = ["#siliconsentiments"]
            
            # Select 14 random hashtags (15 total with siliconsentiments)
            available_tags = [tag for tag in settings.ALL_HASHTAGS if tag != "#siliconsentiments"]
            selected_tags = random.sample(available_tags, 14)
            hashtags.extend(selected_tags)

            return " ".join(hashtags)
        except Exception as e:
            self.logger.error(f"Error generating hashtags: {e}")
            return "#siliconsentiments"  # Fallback to just our main hashtag 

    async def find_unpublished_post(self) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Find an unpublished post with its associated images"""
        try:
            # Find post that hasn't been published and has image_ref
            post = await self.db.find_one('posts', {
                'image_ref': {'$exists': True},
                '$or': [
                    {'instagram_status': {'$ne': 'published'}},
                    {'instagram_status': {'$exists': False}}
                ]
            })
            
            if not post:
                self.logger.info("No unpublished posts found")
                return None, None

            # Get associated images document
            image_doc = await self.db.find_one('post_images', {'_id': post['image_ref']})
            if not image_doc:
                self.logger.error(f"No image document found for post {post['shortcode']}")
                return None, None

            # Verify we have images data
            if not image_doc.get('images'):
                self.logger.error(f"No images data found for post {post['shortcode']}")
                return None, None

            # Log what we found
            generations = image_doc['images'][0].get('midjourney_generations', [])
            self.logger.info(f"Found unpublished post: {post['shortcode']} with {len(generations)} generations")

            return post, image_doc

        except Exception as e:
            self.logger.error(f"Error finding unpublished post: {e}")
            self.logger.exception(e)
            return None, None

    async def get_unpublished_posts(self) -> List[Dict]:
        """Get a list of unpublished posts with their associated images"""
        try:
            # Find posts that haven't been published and have image_ref
            posts = await self.db.find('posts', {
                'image_ref': {'$exists': True},
                '$or': [
                    {'instagram_status': {'$ne': 'published'}},
                    {'instagram_status': {'$exists': False}}
                ]
            })
            
            if not posts:
                self.logger.info("No unpublished posts found")
                return []

            # Get associated images documents and filter valid ones
            valid_posts = []
            for post in posts:
                image_doc = await self.db.find_one('post_images', {'_id': post['image_ref']})
                if not image_doc or not image_doc.get('images'):
                    self.logger.warning(f"Invalid image document for post {post.get('shortcode')}")
                    continue

                # Check if post has enough generations
                generations = image_doc['images'][0].get('midjourney_generations', [])
                if len(generations) < 2:
                    self.logger.warning(f"Post {post.get('shortcode')} has insufficient generations ({len(generations)})")
                    continue

                # Store image_doc with post for later use
                post['image_doc'] = image_doc
                valid_posts.append(post)

            self.logger.info(f"Found {len(valid_posts)} valid unpublished posts")
            return valid_posts

        except Exception as e:
            self.logger.error(f"Error getting unpublished posts: {str(e)}", exc_info=True)
            return []

    async def verify_image_url(self, image_url: str) -> bool:
        """Verify that an image URL is accessible"""
        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                response = await client.head(image_url)
                if response.status_code == 200:
                    self.logger.info(f"Successfully verified image URL: {image_url}")
                    return True
                else:
                    self.logger.error(f"Failed to verify image URL: {image_url}, status code: {response.status_code}")
                    return False
        except Exception as e:
            self.logger.error(f"Error verifying image URL {image_url}: {e}")
            return False

    async def _process_carousel_post(self, post: Dict) -> Optional[str]:
        """Process a single carousel post"""
        try:
            if not await self.ensure_valid_token():
                self.logger.error("Failed to obtain valid token")
                return None

            if not await self.verify_api_access():
                self.logger.error("Failed to verify API access")
                return None

            image_doc = post.get('image_doc')
            if not image_doc:
                self.logger.error(f"No image document found for post {post.get('shortcode')}")
                return None

            # Get generations from the first image and ensure they're from the same post
            if not image_doc.get('images') or not image_doc['images'][0].get('midjourney_generations'):
                self.logger.error(f"No generations found for post {post.get('shortcode')}")
                return None

            # Get all generations for this specific post
            post_generations = image_doc['images'][0]['midjourney_generations']
            if not post_generations:
                self.logger.error(f"Empty generations list for post {post.get('shortcode')}")
                return None

            self.logger.info(f"Processing {len(post_generations)} variations for carousel from post {post.get('shortcode')}")

            # Process each variation
            item_ids = []
            failed_variations = []

            # Track which post we're processing to ensure no mixing
            current_post_id = str(post['_id'])
            
            for gen in post_generations[:10]:  # Take up to 10 generations
                try:
                    # Verify this generation belongs to the current post
                    if gen.get('post_id') and str(gen['post_id']) != current_post_id:
                        self.logger.error(f"Mismatched post ID in generation: expected {current_post_id}, got {gen.get('post_id')}")
                        continue

                    self.logger.info(self.debug_generation(gen))
                    if not gen.get('midjourney_image_id'):
                        self.logger.error(f"Missing midjourney_image_id for variation {gen.get('variation')}")
                        failed_variations.append(gen.get('variation'))
                        continue

                    filename = f"post_{post['shortcode']}_{gen['variation']}.jpg"
                    image_path = self.instagram_images_dir / filename

                    self.logger.info(f"Processing variation: {gen['variation']}")
                    
                    # Save image from GridFS
                    if await self.image_processor.save_image_from_gridfs(gen, str(image_path)):
                        # Verify file exists and has content
                        if not os.path.exists(image_path):
                            self.logger.error(f"File not found after save: {image_path}")
                            failed_variations.append(gen.get('variation'))
                            continue
                            
                        file_size = os.path.getsize(image_path)
                        if file_size == 0:
                            self.logger.error(f"Empty file created: {image_path}")
                            failed_variations.append(gen.get('variation'))
                            continue
                            
                        self.logger.info(f"File ready for upload: {image_path} ({file_size} bytes)")
                        
                        # Create carousel item with retries
                        # Use the DuckDNS domain for image URLs
                        image_url = f"https://siliconsents.duckdns.org/images/instagram/{filename}"
                        self.logger.info(f"Using image URL: {image_url}")
                        
                        # Verify the image URL is accessible
                        if not await self.verify_image_url(image_url):
                            self.logger.error(f"Image URL not accessible: {image_url}")
                            failed_variations.append(gen.get('variation'))
                            continue
                        
                        item_id = await self.carousel_processor.try_create_carousel_item_with_retries(image_url)
                        
                        if item_id:
                            item_ids.append(item_id)
                            await asyncio.sleep(2)  # Delay between items
                        else:
                            failed_variations.append(gen.get('variation'))
                    else:
                        self.logger.error(f"Failed to save image from GridFS: {filename}")
                        failed_variations.append(gen.get('variation'))
                        
                except Exception as e:
                    self.logger.error(f"Error processing variation {gen.get('variation')}: {str(e)}")
                    failed_variations.append(gen.get('variation'))
                    continue

            # Check if we have enough valid items
            if len(item_ids) < 2:
                self.logger.error(f"Insufficient valid items for carousel ({len(item_ids)} created, minimum of 2 required)")
                await self.mark_post_as_failed(post, f"Failed to create carousel items. Failed variations: {failed_variations}")
                return None

            # Generate caption using the first image
            first_gen = post_generations[0]
            first_image_path = self.instagram_images_dir / f"post_{post['shortcode']}_{first_gen['variation']}.jpg"
            
            if os.path.exists(first_image_path):
                caption = await self.caption_generator.generate_caption(
                    str(first_image_path),
                    first_gen.get('prompt', '')
                )
            else:
                caption = f"AI Generated Art\n\n{self.generate_hashtags()}"
            
            self.logger.info(f"Generated caption: {caption[:100]}...")

            # Create and publish container
            container_id = await self.carousel_processor.create_carousel_container(item_ids, caption)
            if not container_id:
                self.logger.error("Failed to create carousel container")
                await self.mark_post_as_failed(post, "Failed to create carousel container")
                return None

            await asyncio.sleep(1)
            result = await self.carousel_processor.publish_container(container_id)
            if not result:
                await self.mark_post_as_failed(post, "Failed to publish container")
                return None

            # Mark as published and cleanup
            await self.mark_post_as_published(post, result['id'])
            self.cleanup_images(post['shortcode'])
            self.logger.info(f"Successfully published carousel for post {post['shortcode']}")
            return result['id']

        except Exception as e:
            self.logger.error(f"Error processing carousel post: {str(e)}", exc_info=True)
            return None

    async def publish_next_carousel(self) -> Optional[str]:
        """Publish next carousel post"""
        try:
            # Get list of unpublished posts
            unpublished_posts = await self.get_unpublished_posts()
            if not unpublished_posts:
                self.logger.info("No unpublished posts found")
                return None

            # Try posts in random order until one succeeds
            random.shuffle(unpublished_posts)
            
            for post in unpublished_posts:
                try:
                    self.logger.info(f"Attempting to publish post: {post['_id']}")
                    result = await self._process_carousel_post(post)
                    if result:
                        return result
                    self.logger.warning(f"Failed to publish post {post['_id']}, trying next post...")
                except Exception as e:
                    self.logger.error(f"Error processing post {post['_id']}: {str(e)}", exc_info=True)
                    continue

            self.logger.error("All available posts failed to publish")
            return None

        except Exception as e:
            self.logger.error(f"Error in publish_next_carousel: {str(e)}", exc_info=True)
            return None

    async def mark_post_as_failed(self, post: dict, error_message: str):
        """Mark a post as failed with error details"""
        try:
            await self.db.update_one('posts', 
                {'_id': post['_id']},
                {
                    '$set': {
                        'instagram_status': 'failed',
                        'updated_at': datetime.now(timezone.utc),
                        'last_publish_attempt': datetime.now(timezone.utc)
                    },
                    '$inc': {'publish_attempts': 1},
                    '$push': {
                        'instagram_data.error_log': {
                            'timestamp': datetime.now(timezone.utc),
                            'error': error_message
                        }
                    }
                }
            )
            self.logger.info(f"Marked post {post.get('shortcode')} as failed: {error_message}")
        except Exception as e:
            self.logger.error(f"Error marking post as failed: {e}")

    async def mark_post_as_published(self, post: dict, post_id: str):
        """Mark a post as successfully published"""
        try:
            # Update post status
            await self.db.update_one('posts',
                {'_id': post['_id']},
                {
                    '$set': {
                        'instagram_status': 'published',
                        'instagram_post_id': post_id,
                        'instagram_publish_date': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc),
                        'last_publish_attempt': datetime.now(timezone.utc)
                    },
                    '$inc': {'publish_attempts': 1}
                }
            )
            
            # Update post_images status if image_ref exists
            if post.get('image_ref'):
                await self.db.update_one('post_images',
                    {'_id': post['image_ref']},
                    {
                        '$set': {
                            'status': 'published',
                            'updated_at': datetime.now(timezone.utc),
                            'images.0.status': 'published',
                            'images.0.updated_at': datetime.now(timezone.utc)
                        }
                    }
                )
            
            self.logger.info(f"Marked post {post.get('shortcode')} as published with ID: {post_id}")
        except Exception as e:
            self.logger.error(f"Error marking post as published: {e}")

    def _get_sorted_generations(self, image_doc: Dict) -> List[Dict]:
        """Sort generations by preferred model order"""
        try:
            # First check if we have the expected structure
            if not image_doc.get('images'):
                self.logger.error("No images field in image_doc")
                return []
            
            if not isinstance(image_doc['images'], list) or not image_doc['images']:
                self.logger.error("Images field is not a non-empty list")
                return []
            
            generations = image_doc['images'][0].get('midjourney_generations', [])
            if not generations:
                self.logger.error("No midjourney_generations found")
                return []

            # Log what we're working with
            self.logger.debug(f"Processing {len(generations)} generations")
            for gen in generations:
                self.logger.debug(f"Found generation: {gen.get('variation')}")
            
            # Group by model
            model_generations = {
                'v6.0': [],
                'v6.1': [],
                'niji': []
            }

            for gen in generations:
                model = gen.get('variation')
                if not model:
                    self.logger.warning(f"Generation missing variation field: {gen}")
                    continue
                
                if model in model_generations:
                    model_generations[model].append(gen)
                else:
                    self.logger.warning(f"Unknown model variation: {model}")

            # Verify we have all required models
            missing_models = [model for model, gens in model_generations.items() if not gens]
            if missing_models:
                self.logger.error(f"Missing generations for models: {missing_models}")
                return []

            # Take first generation from each model in preferred order
            result = []
            for model in ['v6.1', 'v6.0', 'niji']:  # Preferred order
                if model_generations[model]:
                    result.append(model_generations[model][0])
                    self.logger.debug(f"Added {model} generation to result")
                else:
                    self.logger.error(f"No generation found for {model}")
                    return []  # If any preferred model is missing, return empty list

            self.logger.info(f"Successfully sorted {len(result)} generations")
            return result

        except Exception as e:
            self.logger.error(f"Error sorting generations: {str(e)}")
            self.logger.exception("Full traceback:")
            return [] 

    def debug_generation(self, gen: dict) -> str:
        """Return a debug string for a generation"""
        try:
            if not gen:
                return "Generation: None"
            variation = gen.get('variation', 'unknown')
            image_id = gen.get('midjourney_image_id', 'no-id')
            prompt = gen.get('prompt', 'No prompt')[:50] if gen.get('prompt') else 'No prompt'
            return f"Generation: {variation} - ID: {image_id} - Prompt: {prompt}..."
        except Exception as e:
            self.logger.error(f"Error creating debug string: {e}")
            return "Error creating debug string" 

    async def generate_caption_from_image(self, gen: dict) -> str:
        """Generate a caption for the image"""
        try:
            prompt = gen.get('prompt', '')
            variation = gen.get('variation', '')
            
            # Generate a random temperature between 0.7 and 0.9 for more variation
            temperature = round(0.7 + random.random() * 0.2, 2)
            
            # Create a more varied system prompt based on the image variation
            system_prompts = [
                "You are a thoughtful art critic who sees deeper meaning in AI-generated art.",
                "You are an enthusiastic social media influencer who loves sharing AI art.",
                "You are a philosophical observer who connects AI art to human experiences.",
                "You are a creative writer who tells stories inspired by AI-generated images."
            ]
            
            system_prompt = random.choice(system_prompts)
            
            # Add variation-specific context to the prompt
            prompt_context = f"""Given this AI art prompt: "{prompt}" (Generated using {variation} model)

            Write a unique Instagram caption that:
            1. Describes the visual elements we see in this AI-generated artwork
            2. Adds a thoughtful reflection about its meaning or interpretation
            3. Includes 1-2 fitting emojis
            4. Uses natural, conversational language
            5. Is 2-3 sentences long
            6. Avoids generic or repetitive phrases
            
            Make it feel personal and authentic."""

            # Generate caption using Replicate's Llama model
            caption_output = replicate.run(
                "meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3",
                input={
                    "prompt": prompt_context,
                    "temperature": temperature,
                    "top_p": 0.95,
                    "max_tokens": 200,
                    "system_prompt": system_prompt
                }
            )
            
            caption = "".join(caption_output).strip()
            
            # Add engagement text from settings and hashtags
            # Add a line break between caption and engagement text for better readability
            return (caption + '\n\n' + settings.ENGAGEMENT_TEXT + '\n\n' + self.generate_hashtags()).replace('"', '')
            
        except Exception as e:
            self.logger.error(f"Error generating caption from image: {e}")
            return f"{prompt}\n\n{self.generate_hashtags()}"

    def cleanup_images(self, shortcode: str):
        """Clean up temporary image files"""
        try:
            pattern = f"{self.instagram_images_dir}/post_{shortcode}_*.jpg"
            for file in Path(self.instagram_images_dir).glob(f"post_{shortcode}_*.jpg"):
                try:
                    file.unlink()
                    self.logger.debug(f"Deleted temporary file: {file}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete file {file}: {e}")
        except Exception as e:
            self.logger.error(f"Error cleaning up images: {e}") 