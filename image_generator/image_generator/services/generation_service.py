"""Service for handling image generation logic"""

import logging
import random
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import time

from ..models import Generation, Image
from ..providers.base import ImageGenerationProvider
from ..providers.midjourney.client import MidjourneyClient
from ..utils.prompt import format_prompt
from ..utils.image import process_image
from .database_service import DatabaseService
from ..config import load_config

class GenerationService:
    """Service to manage the image generation process"""
    
    def __init__(self, 
                 database_service: DatabaseService,
                 provider: Optional[ImageGenerationProvider] = None):
        """Initialize generation service
        
        Args:
            database_service: Database service instance
            provider: Image generation provider (defaults to MidjourneyClient)
        """
        self.db = database_service
        
        # Load config for Midjourney credentials
        if not provider:
            config = load_config()
            provider = MidjourneyClient(
                channel_id=config.midjourney.channel_id,
                oauth_token=config.midjourney.oauth_token
            )
            
        self.provider = provider
        
        # Track processed upscales at class level
        self.processed_upscales = set()
        # Track current message IDs for each variation
        self.current_message_ids = {}
        # Track last processed variation
        self.last_processed_variation = None
        
    def generate_images(self, 
                       post_id: str, 
                       description: str,
                       variations: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Generate images for a post"""
        try:
            # Format the prompt for the image generation
            prompt = format_prompt(description)
            if not prompt:
                logging.error("Failed to format prompt")
                return False
                
            # Generate seed for consistency across variations
            seed = random.randint(0, 4294967295)
            logging.info(f"Using seed {seed} for all variations")
            
            # Clear tracking data
            self.processed_upscales.clear()
            self.current_message_ids.clear()
            self.last_processed_variation = None
            
            variations_to_process = [
                {'name': 'niji', 'options': {'niji': True, 'ar': '4:5', 'seed': seed}},
                {'name': 'v6.1', 'options': {'v': '6.1', 'ar': '4:5', 'seed': seed}},
                {'name': 'v6.0', 'options': {'v': '6.0', 'ar': '4:5', 'seed': seed}}
            ]
            
            for variation in variations_to_process:
                logging.info(f"\n=== Processing {variation['name']} variation ===")
                
                if not self._process_variation(post_id, prompt, variation['options']):
                    logging.error(f"Failed to process {variation['name']} variation")
                    return False
                    
                # Add delay between variations
                if variation != variations_to_process[-1]:
                    delay = random.uniform(45, 60)  # Increased delay
                    logging.info(f"Waiting {delay:.2f}s before next variation...")
                    time.sleep(delay)
                    
                # Clear upscale tracking but keep message IDs
                self.processed_upscales.clear()
                
            return True
            
        except Exception as e:
            logging.error(f"Error generating images: {str(e)}")
            return False
            
    def _process_variation(self,
                          post_id: str,
                          prompt: str,
                          variation_options: Dict[str, Any]) -> bool:
        """Process a single variation
        
        Args:
            post_id: ID of the post
            prompt: Formatted prompt
            variation_options: Options for this variation
            
        Returns:
            True if processing was successful
        """
        try:
            # Format variation name
            if variation_options.get('niji'):
                variation_name = 'niji'
                # Modify prompt for niji
                prompt = f"{prompt} --niji"
                # Remove niji from options since it's in prompt
                variation_options = {k:v for k,v in variation_options.items() if k != 'niji'}
            elif variation_options.get('v') == '6.0':
                variation_name = 'v6.0'
            else:
                variation_name = f"v{variation_options.get('v', '1')}"
            
            # Validate we're not processing the same variation twice
            if variation_name == self.last_processed_variation:
                logging.error(f"Attempting to process {variation_name} variation again")
                return False
                            
            # Generate initial image
            message = self.provider.generate(prompt, variation_options)
            if not message:
                logging.error("Failed to generate initial image")
                return False
                
            # Store the message ID for this variation
            generation_message_id = message['id']
            
            # Validate message ID is unique
            if generation_message_id in self.current_message_ids.values():
                logging.error(f"Duplicate message ID {generation_message_id} detected for {variation_name}")
                return False
                
            self.current_message_ids[variation_name] = generation_message_id
            logging.info(f"Generated initial image with message ID: {generation_message_id} for variation {variation_name}")
            
            # Update last processed variation
            self.last_processed_variation = variation_name
            
            # Wait for initial generation to complete and verify upscale buttons are available
            logging.info("Waiting for initial generation to complete...")
            time.sleep(30)  # Give time for the initial grid to generate
                
            # Process upscales sequentially
            for idx in range(1, 5):
                # Skip if this upscale was already processed
                upscale_key = f"{generation_message_id}_{idx}"
                if upscale_key in self.processed_upscales:
                    logging.info(f"Skipping upscale {idx} as it was already processed for message {generation_message_id}")
                    continue
                    
                logging.info(f"Processing upscale {idx} of 4 for message {generation_message_id} ({variation_name})")
                
                # Additional verification before each upscale
                if idx > 1:
                    logging.info("Waiting between upscales to ensure proper sequencing...")
                    time.sleep(20)  # Increased wait time between upscales
                
                # Verify we're using the correct message ID before upscaling
                if generation_message_id != self.current_message_ids.get(variation_name):
                    logging.error(f"Message ID mismatch for {variation_name}. Expected {self.current_message_ids.get(variation_name)}, got {generation_message_id}")
                    return False
                
                generation = self._process_upscale(
                    generation_message_id,
                    prompt,
                    variation_name,
                    idx,
                    idx-1
                )
                
                if not generation:
                    logging.error(f"Failed to process upscale {idx} for message {generation_message_id}")
                    return False
                    
                # Mark this upscale as processed
                self.processed_upscales.add(upscale_key)
                logging.info(f"Marked upscale {idx} as processed for message {generation_message_id}")
                
                # Save and verify generation
                if not self.db.save_generation(post_id, generation):
                    logging.error(f"Failed to save generation {idx}")
                    return False
                    
                if not self.db.verify_generation(post_id, generation):
                    logging.error(f"Failed to verify generation {idx}")
                    return False
                
            logging.info(f"Successfully processed all upscales for {variation_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error processing variation: {str(e)}")
            return False
            
    def _process_upscale(self,
                        message_id: str,
                        prompt: str,
                        variation_name: str,
                        upscale_index: int,
                        variant_idx: int) -> Optional[Generation]:
        """Process a single upscale operation"""
        try:
            logging.info(f"Starting upscale {upscale_index} for {variation_name}")
            logging.debug(f"Message ID: {message_id}, Variant Index: {variant_idx}")
            
            # Add delay before upscale to avoid rate limits
            time.sleep(5)
            
            max_retries = 3
            retry_delay = 10
            
            for attempt in range(max_retries):
                try:
                    # Request upscale
                    logging.info(f"Sending upscale request (attempt {attempt + 1}/{max_retries})...")
                    upscale = self.provider.upscale(message_id, upscale_index)
                    
                    if upscale and upscale.get('url'):
                        url = upscale['url']
                        logging.info("Successfully got upscale URL")
                        break
                    else:
                        raise Exception("No URL in upscale response")
                        
                except Exception as e:
                    logging.error(f"Upscale attempt {attempt + 1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        logging.info(f"Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                    else:
                        raise
            
            if not url:
                raise Exception("Failed to get upscale URL after all retries")
            
            # Process image
            logging.info("Processing upscaled image...")
            image_data = process_image(url)
            if not image_data:
                raise Exception("Failed to process upscaled image")
            
            # Save to GridFS
            filename = f"midjourney_{variation_name}_variant_{variant_idx}.jpg"
            logging.info(f"Saving to GridFS as {filename}")
            image_id = self.db.fs.put(image_data, filename=filename)
            
            logging.info(f"Successfully processed upscale {upscale_index} for {variation_name}")
            return Generation(
                variation=f"{variation_name}_variant_{variant_idx}",
                prompt=prompt,
                upscaled_photo_url=url,
                imagine_message_id=message_id,
                midjourney_image_id=image_id,
                metadata={
                    "original_filename": filename,
                    "file_size": len(image_data),
                    "content_type": "image/jpeg"
                }
            )
            
        except Exception as e:
            logging.error(f"Error processing upscale: {str(e)}")
            logging.exception(e)
            return None