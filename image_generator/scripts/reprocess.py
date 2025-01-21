#!/usr/bin/env python3

import os
import logging
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import time
import random
import re
import requests
import signal

from image_generator.core import (
    get_database,
    get_gridfs,
    save_generation_data,
    verify_generations,
    generate_images
)
from image_generator.providers.midjourney.client import MidjourneyClient
from image_generator.utils.prompt import format_prompt
from image_generator.utils.image import process_image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add file handler for debug logging
debug_handler = logging.FileHandler('reprocess_debug.log')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
))
logging.getLogger().addHandler(debug_handler)

class ProcessingTracker:
    """Track processing progress and results"""
    
    def __init__(self):
        self.processed_posts = []
        self.verification_results = {}
        self.load_state()
        
    def load_state(self):
        """Load processing state from database"""
        try:
            db = get_database()
            processed = db.posts.find({
                'reprocess_status': {'$in': ['completed', 'failed']},
                'reprocess_updated_at': {'$exists': True}
            }).sort('reprocess_updated_at', 1)
            
            for post in processed:
                self.processed_posts.append({
                    'post_id': post['_id'],
                    'shortcode': post['shortcode'],
                    'processed_at': post.get('reprocess_updated_at'),
                    'status': post.get('reprocess_status')
                })
                
            logging.info(f"Loaded {len(self.processed_posts)} previously processed posts")
            
        except Exception as e:
            logging.error(f"Error loading processing state: {str(e)}")
            
    def add_processed_post(self, post_id: str, shortcode: str):
        """Add a post to the processing tracker"""
        self.processed_posts.append({
            'post_id': post_id,
            'shortcode': shortcode,
            'processed_at': datetime.now(timezone.utc),
            'status': 'pending_verification'
        })
        
    def verify_processed_posts(self):
        """Verify posts processed in this run"""
        logging.info("\nVerifying processed posts...")
        unverified_posts = [p for p in self.processed_posts 
                           if p.get('status') == 'pending_verification']
                           
        if not unverified_posts:
            logging.info("No new posts to verify")
            return
            
        logging.info(f"Verifying {len(unverified_posts)} posts from this run")
        db = get_database()
        
        for post in unverified_posts:
            post_id = post['post_id']
            shortcode = post['shortcode']
            
            # Find post_images document
            post_doc = db.posts.find_one({'_id': post_id})
            if not post_doc or 'image_ref' not in post_doc:
                self.verification_results[shortcode] = {
                    'status': 'failed',
                    'reason': 'No image_ref found'
                }
                continue
                
            post_images = db.post_images.find_one({'_id': post_doc['image_ref']})
            if not post_images:
                self.verification_results[shortcode] = {
                    'status': 'failed',
                    'reason': 'No post_images document found'
                }
                continue
                
            # Check variations and upscales
            variations = {'v6.0': [], 'v6.1': [], 'niji': []}
            missing_files = []
            
            for img in post_images.get('images', []):
                for gen in img.get('midjourney_generations', []):
                    variation = gen.get('variation', '')
                    match = re.match(r'^(v6\.0|v6\.1|niji)_variant_([0-3])$', variation)
                    if match:
                        base_var = match.group(1)
                        variant_num = int(match.group(2))
                        variations[base_var].append(variant_num)
                        
                        # Check GridFS file
                        if 'midjourney_image_id' in gen:
                            try:
                                fs = get_gridfs()
                                fs.get(gen['midjourney_image_id'])
                            except:
                                missing_files.append(variation)
                                
            # Verify each variation has all upscales
            verification_result = {
                'status': 'success',
                'variations': {},
                'missing_files': missing_files
            }
            
            for var_name, variant_nums in variations.items():
                variant_nums.sort()
                verification_result['variations'][var_name] = {
                    'upscales': variant_nums,
                    'complete': variant_nums == [0,1,2,3]
                }
                if not verification_result['variations'][var_name]['complete']:
                    verification_result['status'] = 'incomplete'
                    
            if missing_files:
                verification_result['status'] = 'missing_files'
                
            self.verification_results[shortcode] = verification_result
            
            # Update post status based on verification
            status = verification_result['status']
            if status == 'success':
                db.posts.update_one(
                    {'_id': post_id},
                    {'$set': {
                        'reprocess_status': 'completed',
                        'reprocess_verified_at': datetime.now(timezone.utc)
                    }}
                )
            else:
                error = f"Verification failed: {status}"
                if 'reason' in verification_result:
                    error += f" - {verification_result['reason']}"
                db.posts.update_one(
                    {'_id': post_id},
                    {'$set': {
                        'reprocess_status': 'failed',
                        'reprocess_error': error,
                        'reprocess_verified_at': datetime.now(timezone.utc)
                    }}
                )
                
    def get_processing_stats(self) -> Dict[str, int]:
        """Get overall processing statistics"""
        try:
            db = get_database()
            total = db.posts.count_documents({'image_ref': {'$exists': True}})
            completed = db.posts.count_documents({
                'image_ref': {'$exists': True},
                'reprocess_status': 'completed',
                'reprocess_verified_at': {'$exists': True}
            })
            failed = db.posts.count_documents({
                'image_ref': {'$exists': True},
                'reprocess_status': 'failed'
            })
            in_progress = db.posts.count_documents({
                'image_ref': {'$exists': True},
                'reprocess_status': 'in_progress'
            })
            pending = total - (completed + failed + in_progress)
            
            return {
                'total': total,
                'completed': completed,
                'failed': failed,
                'in_progress': in_progress,
                'pending': pending
            }
        except Exception as e:
            logging.error(f"Error getting processing stats: {str(e)}")
            return None
            
    def print_verification_report(self):
        """Print verification report for this run"""
        stats = self.get_processing_stats()
        if not stats:
            return
            
        logging.info("\n=== Overall Progress ===")
        logging.info(f"Total posts: {stats['total']}")
        logging.info(f"Completed: {stats['completed']}")
        logging.info(f"Failed: {stats['failed']}")
        logging.info(f"In Progress: {stats['in_progress']}")
        logging.info(f"Pending: {stats['pending']}")
        
        if self.verification_results:
            logging.info("\n=== This Run's Results ===")
            success = sum(1 for r in self.verification_results.values() if r['status'] == 'success')
            incomplete = sum(1 for r in self.verification_results.values() if r['status'] == 'incomplete')
            failed = sum(1 for r in self.verification_results.values() if r['status'] not in ['success', 'incomplete'])
            
            logging.info(f"Posts processed this run: {len(self.verification_results)}")
            logging.info(f"Success: {success}")
            logging.info(f"Incomplete: {incomplete}")
            logging.info(f"Failed: {failed}")
            
            # Show details for non-successful posts
            for shortcode, result in self.verification_results.items():
                if result['status'] != 'success':
                    logging.info(f"\nPost {shortcode}:")
                    logging.info(f"Status: {result['status']}")
                    if result['status'] == 'incomplete':
                        for var_name, var_info in result['variations'].items():
                            if not var_info['complete']:
                                missing = set([0,1,2,3]) - set(var_info['upscales'])
                                logging.info(f"- {var_name} missing upscales: {sorted(missing)}")
                    if 'reason' in result:
                        logging.info(f"Reason: {result['reason']}")
                    if 'missing_files' in result and result['missing_files']:
                        logging.info(f"Missing files: {result['missing_files']}")

def get_posts_to_reprocess(batch_size: int = 10, skip: int = 0, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Get posts that need reprocessing
    
    Args:
        batch_size: Number of posts to process at once
        skip: Number of posts to skip
        query: Additional query conditions
        
    Returns:
        List of posts to reprocess
    """
    db = get_database()
    
    # Find posts with image_ref that need reprocessing
    query = {
        'image_ref': {'$exists': True},
        'status': {'$ne': 'pending_publish'},
        '$or': [
            {'reprocess_status': {'$exists': False}},
            {'reprocess_status': 'pending'},
            {'reprocess_status': 'failed'},
            {'reprocess_status': 'in_progress'}
        ]
    }
    
    if query:
        query.update(query)
    
    logging.info(f"Finding posts with query: {query}")
    posts = list(db.posts.find(query).skip(skip).limit(batch_size))
    logging.info(f"Found {len(posts)} posts matching initial criteria")
    
    # Filter posts that need reprocessing
    needs_reprocessing_posts = []
    for post in posts:
        if needs_reprocessing(post['_id']) or post.get('reprocess_status') in ['failed', 'in_progress']:
            logging.info(f"Post {post['shortcode']} needs reprocessing")
            needs_reprocessing_posts.append(post)
        else:
            logging.info(f"Post {post['shortcode']} already has all upscales")
            
    logging.info(f"After filtering, {len(needs_reprocessing_posts)} posts need reprocessing")
    return needs_reprocessing_posts

def needs_reprocessing(post_id: str) -> bool:
    """Check if a post needs reprocessing
    
    Args:
        post_id: MongoDB post ID
        
    Returns:
        True if post needs reprocessing
    """
    db = get_database()
    fs = get_gridfs()
    
    try:
        # Find post_images document
        post = db.posts.find_one({'_id': post_id})
        if not post or 'image_ref' not in post:
            logging.info(f"Post {post_id} has no image_ref")
            return True
            
        post_images = db.post_images.find_one({'_id': post['image_ref']})
        if not post_images:
            logging.info(f"Post {post_id} has no generations at all")
            return True
            
        # Check each image's generations
        for img in post_images.get('images', []):
            generations = img.get('midjourney_generations', [])
            
            # Group generations by variation
            variations = {
                'v6.0': [],
                'v6.1': [],
                'niji': []
            }
            
            # Check each generation's format and group them
            for gen in generations:
                variation = gen.get('variation', '')
                match = re.match(r'^(v6\.0|v6\.1|niji)_variant_([0-3])$', variation)
                if not match:
                    logging.info(f"Post {post_id} has incorrect variation format: {variation}")
                    return True
                    
                base_var = match.group(1)
                variant_num = int(match.group(2))
                
                if base_var in variations:
                    variations[base_var].append(variant_num)
                    
            # Verify each variation has all 4 upscales (0,1,2,3)
            for var_name, variant_nums in variations.items():
                if not variant_nums:
                    logging.info(f"Post {post_id} missing variation {var_name}")
                    return True
                    
                variant_nums.sort()
                if variant_nums != [0,1,2,3]:
                    logging.info(f"Post {post_id} variation {var_name} has incorrect variants: {variant_nums}")
                    return True
                    
                # Verify GridFS files exist
                for variant_num in variant_nums:
                    variation = f"{var_name}_variant_{variant_num}"
                    gen = next((g for g in generations if g.get('variation') == variation), None)
                    if not gen or 'midjourney_image_id' not in gen:
                        logging.info(f"Post {post_id} missing GridFS reference for {variation}")
                        return True
                    try:
                        fs.get(gen['midjourney_image_id'])
                    except:
                        logging.info(f"Post {post_id} missing GridFS file for {variation}")
                        return True
                        
        return False
        
    except Exception as e:
        logging.error(f"Error checking post {post_id}: {str(e)}")
        return True

async def generate_midjourney(prompt: str, mj_client) -> List[Dict[str, Any]]:
    """Generate images for all variations with proper sequencing"""
    variations = [
        {"v": "6.0"},
        {"v": "6.1"},
        {"v": "niji"}
    ]

    all_results = []
    
    for i, options in enumerate(variations, 1):
        variation_name = f"v{options['v']}" if options['v'] != 'niji' else 'niji'
        logging.info(f"\n=== Starting variation {i}/{len(variations)}: {variation_name} ===")
        
        try:
            # Generate full prompt
            full_prompt = prompt.replace(" --ar 4:5", "")  # Remove any existing aspect ratio
            
            # Handle different variation types
            if options['v'] == 'niji':
                full_prompt = f"{full_prompt} --q 1 --niji --seed {seed} --ar 4:5"
            else:
                # Ensure version parameter is added for both v6.0 and v6.1
                full_prompt = f"{full_prompt} --q 1 --seed {seed} --ar 4:5 --v {options['v']}"
            
            logging.info(f"Final prompt: {full_prompt}")

            # Initial generation with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Send imagine command
                    logging.info(f"Sending imagine command (attempt {attempt + 1}/{max_retries})...")
                    message = mj_client.generate(full_prompt)
                    message_id = message.get('imagine_message_id')
                    
                    if not message_id:
                        if attempt < max_retries - 1:
                            logging.warning("Failed to get message ID, retrying in 10s...")
                            time.sleep(10)
                            continue
                        logging.error(f"Failed to get message ID for {variation_name} after {max_retries} attempts")
                        break

                    logging.info(f"Got message ID: {message_id}")
                    
                    # Wait for initial generation with progress updates
                    initial_wait = 90  # Increased initial wait time
                    logging.info(f"Waiting {initial_wait}s for initial generation...")
                    
                    # Check generation status every 10 seconds
                    for _ in range(initial_wait // 10):
                        if mj_client.verify_message(message_id):
                            logging.info("Generation completed successfully")
                            break
                        logging.info("Generation in progress...")
                        time.sleep(10)
                    
                    if not mj_client.verify_message(message_id):
                        if attempt < max_retries - 1:
                            logging.warning("Generation not complete, retrying...")
                            continue
                        logging.error("Generation failed after all retries")
                        break
                        
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logging.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
                        time.sleep(10)
                    else:
                        raise

            # Process all upscales for this variation
            variation_results = []
            for idx in range(1, 5):  # Process all 4 upscales
                try:
                    logging.info(f"Processing upscale {idx}/4 for {variation_name}")
                    
                    # Verify message with retries
                    max_verify_retries = 3
                    message_verified = False
                    
                    for verify_attempt in range(max_verify_retries):
                        if mj_client.verify_message(message_id):
                            message_verified = True
                            break
                        if verify_attempt < max_verify_retries - 1:
                            logging.info(f"Message verification attempt {verify_attempt + 1} failed, retrying in 10s...")
                            time.sleep(10)
                            
                    if not message_verified:
                        logging.error(f"Cannot verify message {message_id} for upscale {idx}")
                        continue

                    # Request upscale with retries
                    upscale_success = False
                    for upscale_attempt in range(max_retries):
                        try:
                            logging.info(f"Requesting upscale {idx} (attempt {upscale_attempt + 1})")
                            upscale_response = mj_client.upscale(
                                message_id=message_id, 
                                index=idx,
                                upscale_type='standard'
                            )
                            
                            if upscale_response and upscale_response.status_code == 204:
                                upscale_success = True
                                break
                                
                            if upscale_attempt < max_retries - 1:
                                logging.warning(f"Upscale request failed, retrying in 10s...")
                                time.sleep(10)
                                
                        except Exception as e:
                            if upscale_attempt < max_retries - 1:
                                logging.warning(f"Upscale attempt {upscale_attempt + 1} failed: {str(e)}")
                                time.sleep(10)
                            else:
                                raise
                                
                    if not upscale_success:
                        logging.error(f"Failed to request upscale {idx} after all retries")
                        continue

                    # Wait longer for upscale with status checks
                    upscale_wait = 90  # Increased wait time
                    logging.info(f"Waiting up to {upscale_wait}s for upscale to complete...")
                    
                    upscale_url = None
                    for _ in range(upscale_wait // 10):
                        upscale_url = mj_client.get_upscaled_url(message_id, idx, force=True)
                        if upscale_url:
                            break
                        logging.info("Upscale in progress...")
                        time.sleep(10)
                        
                    if not upscale_url:
                        logging.error(f"Failed to get upscale URL for U{idx}")
                        continue

                    # Process and store the image with improved error handling
                    try:
                        # Download with retries
                        image_response = None
                        for download_attempt in range(3):
                            try:
                                image_response = requests.get(upscale_url, timeout=30)
                                if image_response.status_code == 200:
                                    break
                            except Exception as e:
                                if download_attempt < 2:
                                    logging.warning(f"Download attempt {download_attempt + 1} failed: {str(e)}")
                                    time.sleep(10)
                                else:
                                    raise
                                    
                        if not image_response or image_response.status_code != 200:
                            logging.error(f"Failed to download image for U{idx}")
                            continue
                            
                        # Process image
                        processed_image = process_image(image_response.content)
                        if not processed_image:
                            logging.error(f"Failed to process image for U{idx}")
                            continue
                            
                        filename = f"midjourney_{variation_name}_variant_{idx-1}.jpg"
                        
                        # Store in GridFS
                        fs = get_gridfs()
                        image_id = fs.put(processed_image, filename=filename)
                        
                        result = {
                            "variation": f"{variation_name}_variant_{idx-1}",
                            "midjourney_image_id": image_id,
                            "message_id": message_id,
                            "created_at": datetime.now(timezone.utc)
                        }
                        variation_results.append(result)
                        logging.info(f"Successfully processed U{idx}")
                        
                    except Exception as e:
                        logging.error(f"Error processing image for U{idx}: {str(e)}")
                        continue
                        
                    # Add longer delay between upscales
                    if idx < 4:
                        sleep_time = random.uniform(30, 35)
                        logging.info(f"Waiting {sleep_time:.2f}s before next upscale...")
                        time.sleep(sleep_time)
                        
                except Exception as e:
                    logging.error(f"Error processing U{idx}: {str(e)}")
                    continue
            
            # Verify all upscales completed for this variation
            if len(variation_results) == 4:
                all_results.extend(variation_results)
                logging.info(f"Successfully completed all upscales for {variation_name}")
            else:
                logging.error(f"Incomplete upscales for {variation_name}: got {len(variation_results)}/4")
            
            # Add longer delay between variations
            if i < len(variations):
                sleep_time = random.uniform(60, 75)  # Increased delay between variations
                logging.info(f"\n=== Waiting {sleep_time:.2f}s before next variation ===")
                time.sleep(sleep_time)
            
        except Exception as e:
            logging.error(f"Error processing variation {variation_name}: {str(e)}")
            continue

    return all_results if all_results else None

def main():
    parser = argparse.ArgumentParser(description='Reprocess posts with missing or incomplete generations')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of posts to process at once')
    parser.add_argument('--skip', type=int, default=0, help='Number of posts to skip')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--retry-failed', action='store_true', help='Retry failed posts')
    args = parser.parse_args()
    
    tracker = ProcessingTracker()
    stats = tracker.get_processing_stats()
    
    if not stats:
        logging.error("Failed to get processing stats")
        exit(1)
        
    logging.info(f"Starting reprocessing: {stats['completed']} completed, {stats['failed']} failed, {stats['total']} total posts")
    
    # Add signal handler for graceful shutdown
    def signal_handler(signum, frame):
        logging.info("\nReceived shutdown signal, completing current post...")
        tracker.print_verification_report()
        exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    
    while stats['completed'] + stats['failed'] < stats['total']:
        try:
            # Get next batch of posts
            query = {'reprocess_status': 'failed'} if args.retry_failed else None
            posts = get_posts_to_reprocess(args.batch_size, stats['completed'] + stats['failed'], query)
            if not posts:
                break
                
            logging.info(f"Processing batch of {len(posts)} posts")
            
            for post in posts:
                try:
                    shortcode = post.get('shortcode')
                    logging.info(f"\n=== Processing post: {shortcode} ===")
                    
                    if not args.dry_run:
                        # Mark as in progress with timeout
                        db = get_database()
                        db.posts.update_one(
                            {'_id': post['_id']},
                            {'$set': {
                                'reprocess_status': 'in_progress',
                                'reprocess_updated_at': datetime.now(timezone.utc),
                                'reprocess_timeout': datetime.now(timezone.utc) + timedelta(minutes=30)
                            }}
                        )
                        
                        # Get post description
                        description = None
                        post_images = db.post_images.find_one({'_id': post['image_ref']})
                        if post_images and post_images.get('images'):
                            description = post_images['images'][0].get('description')
                        if not description and 'caption' in post:
                            description = post['caption']
                            
                        if not description:
                            raise Exception("No description found")
                            
                        # Generate images with timeout
                        success = False
                        try:
                            success = generate_images(post['_id'], description)
                        except Exception as e:
                            logging.error(f"Generation error: {str(e)}")
                            
                        # Track the processed post
                        tracker.add_processed_post(post['_id'], shortcode)
                        
                        if success:
                            stats['completed'] += 1
                            logging.info(f"Successfully processed post {shortcode}")
                        else:
                            stats['failed'] += 1
                            logging.error(f"Failed to process post {shortcode}")
                    else:
                        logging.info(f"[DRY RUN] Would process post: {shortcode}")
                        stats['completed'] += 1
                        
                    logging.info(f"Progress: {stats['completed']}/{stats['total']} completed, {stats['failed']} failed")
                    
                    # Add delay between posts
                    if stats['completed'] + stats['failed'] < stats['total']:
                        delay = random.uniform(20, 30)
                        logging.info(f"Waiting {delay:.2f} seconds before next post...")
                        if not args.dry_run:
                            time.sleep(delay)
                            
                except Exception as e:
                    logging.error(f"Error processing post {shortcode}: {str(e)}")
                    if not args.dry_run:
                        db = get_database()
                        db.posts.update_one(
                            {'_id': post['_id']},
                            {'$set': {
                                'reprocess_status': 'failed',
                                'reprocess_error': str(e),
                                'reprocess_updated_at': datetime.now(timezone.utc)
                            }}
                        )
                    stats['failed'] += 1
                    continue
                    
            # Log batch completion
            logging.info(f"\nBatch complete. Overall progress: {stats['completed']}/{stats['total']} completed, {stats['failed']} failed")
            
        except Exception as e:
            logging.error(f"Error processing batch: {str(e)}")
            continue
            
    # Verify all processed posts
    if not args.dry_run:
        tracker.verify_processed_posts()
        tracker.print_verification_report()
        
    logging.info("Reprocessing complete!")
    logging.info(f"Final status: {stats['completed']}/{stats['total']} completed, {stats['failed']} failed")

if __name__ == "__main__":
    main() 