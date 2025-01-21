#!/usr/bin/env python3

import logging
import argparse

from image_generator.core import generate_images

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    parser = argparse.ArgumentParser(description='Generate images for a post')
    parser.add_argument('post_id', help='MongoDB post ID')
    parser.add_argument('description', help='Text description to generate from')
    parser.add_argument('--provider', default='midjourney', help='Provider to use')
    args = parser.parse_args()
    
    success = generate_images(args.post_id, args.description, args.provider)
    if not success:
        exit(1)

if __name__ == "__main__":
    main() 