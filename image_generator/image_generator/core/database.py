import os
from typing import Optional, Dict, Any
from pymongo import MongoClient
import gridfs
from datetime import datetime, timezone
from dotenv import load_dotenv
import logging

load_dotenv()

def get_database():
    """Get MongoDB database connection
    
    Returns:
        MongoDB database instance
    """
    uri = os.getenv('MONGODB_URI')
    if not uri:
        raise ValueError("MONGODB_URI environment variable is not set")
    
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000, authSource='admin')
        client.admin.command('ping')
        return client['instagram_db']
    except Exception as e:
        print(f"DB Connection error: {str(e)}")
        raise

def get_gridfs():
    """Get GridFS instance
    
    Returns:
        GridFS instance
    """
    db = get_database()
    return gridfs.GridFS(db)

def save_generation_data(db: Any, post_id: str, generation_data: Dict[str, Any]) -> bool:
    """Save generation data to database
    
    Args:
        db: MongoDB database instance
        post_id: ID of the post to update
        generation_data: List of generation data to save
        
    Returns:
        True if save was successful, False otherwise
    """
    try:
        # Get post_images document
        post = db.posts.find_one({'_id': post_id})
        if not post or 'image_ref' not in post:
            logging.error(f"Post {post_id} not found or has no image_ref")
            return False
            
        post_images = db.post_images.find_one({'_id': post['image_ref']})
        if not post_images:
            logging.error(f"Post_images document not found for {post_id}")
            return False
            
        # Ensure we have a list of generations
        if not isinstance(generation_data, list):
            generation_data = [generation_data]
            
        # Update or append generation data
        for img in post_images.get('images', []):
            generations = img.get('midjourney_generations', [])
            
            # Process each new generation
            for gen in generation_data:
                variation = gen.get('variation')
                if not variation:
                    continue
                    
                # Check if this variation already exists
                existing_idx = next((i for i, g in enumerate(generations) 
                                   if g.get('variation') == variation), None)
                                   
                if existing_idx is not None:
                    # Update existing generation
                    generations[existing_idx] = gen
                else:
                    # Append new generation
                    generations.append(gen)
                    
            img['midjourney_generations'] = generations
            img['updated_at'] = datetime.now(timezone.utc)
            
        # Save changes
        result = db.post_images.update_one(
            {'_id': post['image_ref']},
            {'$set': {
                'images': post_images['images'],
                'updated_at': datetime.now(timezone.utc)
            }}
        )
        
        if result.modified_count == 0:
            logging.error("No documents were modified")
            return False
            
        logging.info(f"Successfully saved {len(generation_data)} generations")
        return True
        
    except Exception as e:
        logging.error(f"Error saving generation data: {str(e)}")
        return False

def verify_generations(db: Any, post_id: str, generations: list) -> bool:
    """Verify that generations were properly saved"""
    try:
        # Get post document first
        post = db.posts.find_one({'_id': post_id})
        if not post or 'image_ref' not in post:
            logging.error(f"Post {post_id} not found or has no image_ref")
            return False
            
        # Get post_images document using image_ref
        post_images = db.post_images.find_one({'_id': post['image_ref']})
        if not post_images:
            logging.error(f"Post_images document not found for image_ref: {post['image_ref']}")
            return False
            
        # Get all saved generations
        saved_generations = []
        for img in post_images.get('images', []):
            saved_generations.extend(img.get('midjourney_generations', []))
            
        logging.info(f"Found {len(saved_generations)} saved generations")
        
        # Verify each expected generation exists
        for gen in generations:
            variation = gen.get('variation')
            if not variation:
                logging.error("Generation missing variation field")
                continue
                
            # Find matching saved generation
            saved_gen = next((g for g in saved_generations 
                            if g.get('variation') == variation), None)
                            
            if not saved_gen:
                logging.error(f"Missing saved generation for variation: {variation}")
                return False
                
            # Verify GridFS file exists
            if 'midjourney_image_id' in saved_gen:
                try:
                    fs = get_gridfs()
                    fs.get(saved_gen['midjourney_image_id'])
                    logging.debug(f"Verified GridFS file for variation: {variation}")
                except Exception as e:
                    logging.error(f"Failed to get GridFS file for variation {variation}: {str(e)}")
                    return False
            else:
                logging.error(f"Missing midjourney_image_id for variation: {variation}")
                return False
                
        logging.info("All generations verified successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error verifying generations: {str(e)}")
        return False