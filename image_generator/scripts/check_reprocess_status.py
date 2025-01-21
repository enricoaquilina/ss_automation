"""Script to check the status of reprocessed images"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from collections import defaultdict
from image_generator.core.database import get_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def analyze_generations(db) -> Dict[str, Any]:
    """Analyze generation status across all posts"""
    stats = {
        'total_posts': 0,
        'successful': 0,
        'failed': 0,
        'pending': 0,
        'variations': {
            'niji': 0,
            'v6.1': 0,
            'v6.0': 0
        },
        'successful_posts_details': [],
        'posts_ready_for_publishing': []
    }
    
    try:
        # Get all posts with image_ref
        posts = db.posts.find({'image_ref': {'$exists': True}})
        
        for post in posts:
            stats['total_posts'] += 1
            post_images = db.post_images.find_one({'_id': post['image_ref']})
            
            if not post_images:
                logging.warning(f"No post_images found for post {post['_id']}")
                stats['failed'] += 1
                continue
                
            # Check generations for this post
            all_variations_complete = True
            variations_found = defaultdict(list)  # Track variant indices for each model
            
            for img in post_images.get('images', []):
                generations = img.get('midjourney_generations', [])
                
                for gen in generations:
                    variation = gen.get('variation', '')
                    
                    # Extract model and variant index
                    if 'niji' in variation:
                        model = 'niji'
                        stats['variations']['niji'] += 1
                    elif 'v6.1' in variation:
                        model = 'v6.1'
                        stats['variations']['v6.1'] += 1
                    elif 'v6.0' in variation:
                        model = 'v6.0'
                        stats['variations']['v6.0'] += 1
                    else:
                        continue
                        
                    # Extract variant index (e.g., "niji_variant_0" -> 0)
                    try:
                        variant_idx = int(variation.split('_')[-1])
                        variations_found[model].append(variant_idx)
                    except (ValueError, IndexError):
                        logging.warning(f"Invalid variation format: {variation}")
                        
                    # Verify GridFS file exists
                    try:
                        if 'midjourney_image_id' in gen:
                            db.fs.files.find_one({'_id': gen['midjourney_image_id']})
                        else:
                            all_variations_complete = False
                    except Exception as e:
                        logging.error(f"Error checking GridFS file for post {post['_id']}: {str(e)}")
                        all_variations_complete = False
            
            # Check if all required variations are present
            required_variations = {'niji', 'v6.1', 'v6.0'}
            if set(variations_found.keys()) == required_variations and all_variations_complete:
                stats['successful'] += 1
                stats['posts_ready_for_publishing'].append(post['_id'])
                
                # Add detailed breakdown for this post
                post_detail = {
                    'post_id': post['_id'],
                    'variations': {
                        model: {
                            'count': len(indices),
                            'indices': sorted(indices)
                        }
                        for model, indices in variations_found.items()
                    }
                }
                stats['successful_posts_details'].append(post_detail)
                
            elif len(variations_found) > 0:
                stats['pending'] += 1
            else:
                stats['failed'] += 1
                
        return stats
        
    except Exception as e:
        logging.error(f"Error analyzing generations: {str(e)}")
        return stats

def print_variation_breakdown(variations_data: List[Dict[str, Any]]):
    """Print detailed breakdown of variations"""
    print("\nDetailed Variation Breakdown:")
    print("=" * 50)
    
    # Count posts by variation pattern
    pattern_counts = defaultdict(int)
    for post in variations_data:
        pattern = []
        for model in ['niji', 'v6.1', 'v6.0']:
            var_info = post['variations'].get(model, {'count': 0})
            pattern.append(f"{model}:{var_info['count']}")
        pattern_counts[', '.join(pattern)] += 1
    
    print("\nVariation Patterns:")
    for pattern, count in pattern_counts.items():
        print(f"{pattern}: {count} posts")
        
    # Print full details for each post
    print("\nPer-Post Breakdown:")
    print("-" * 50)
    for post in variations_data:
        print(f"\nPost ID: {post['post_id']}")
        for model in ['niji', 'v6.1', 'v6.0']:
            var_info = post['variations'].get(model, {'count': 0, 'indices': []})
            print(f"  {model}: {var_info['count']} variations - indices: {var_info['indices']}")

def main():
    """Main function to check reprocessing status"""
    try:
        db = get_database()
        
        logging.info("Analyzing generation status...")
        stats = analyze_generations(db)
        
        # Print summary
        print("\nReprocessing Status Summary:")
        print("=" * 50)
        print(f"Total Posts: {stats['total_posts']}")
        print(f"Successfully Reprocessed: {stats['successful']}")
        print(f"Pending Reprocessing: {stats['pending']}")
        print(f"Failed Reprocessing: {stats['failed']}")
        
        print("\nTotal Variation Counts:")
        print("-" * 30)
        for variation, count in stats['variations'].items():
            print(f"{variation}: {count}")
            
        # Print detailed breakdown
        print_variation_breakdown(stats['successful_posts_details'])
            
        # Save results to file
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f"reprocess_status_detailed_{timestamp}.log"
        
        with open(filename, 'w') as f:
            f.write("Detailed Reprocessing Status Report\n")
            f.write(f"Generated at: {datetime.now(timezone.utc)}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("Summary:\n")
            f.write(f"Total Posts: {stats['total_posts']}\n")
            f.write(f"Successfully Reprocessed: {stats['successful']}\n")
            f.write(f"Pending Reprocessing: {stats['pending']}\n")
            f.write(f"Failed Reprocessing: {stats['failed']}\n\n")
            
            f.write("Total Variation Counts:\n")
            for variation, count in stats['variations'].items():
                f.write(f"{variation}: {count}\n")
            
            f.write("\nDetailed Variation Breakdown:\n")
            f.write("=" * 50 + "\n")
            
            for post in stats['successful_posts_details']:
                f.write(f"\nPost ID: {post['post_id']}\n")
                for model in ['niji', 'v6.1', 'v6.0']:
                    var_info = post['variations'].get(model, {'count': 0, 'indices': []})
                    f.write(f"  {model}: {var_info['count']} variations - indices: {var_info['indices']}\n")
                
        logging.info(f"Detailed results saved to {filename}")
        
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main() 