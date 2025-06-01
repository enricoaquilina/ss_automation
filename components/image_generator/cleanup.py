#!/usr/bin/env python3
"""
Cleanup Script for Image Generator Component

This script cleans up old result directories and organizes test results
to prevent disk space usage issues.

Usage:
    python cleanup.py [--days DAYS] [--keep KEEP] [--test-results] [--dry-run]
"""

import os
import sys
import argparse
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("cleanup")

def clean_midjourney_results(days: int = 7, keep: int = 5, dry_run: bool = False):
    """
    Clean up old Midjourney result directories
    
    Args:
        days: Delete directories older than this many days
        keep: Minimum number of directories to keep regardless of age
        dry_run: If True, only print what would be deleted without actually deleting
    """
    results_dir = "midjourney_results"
    if not os.path.exists(results_dir):
        logger.info(f"No '{results_dir}' directory found, nothing to clean")
        return
    
    # Get all subdirectories
    subdirs = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
    
    # Filter and sort directories by modification time
    dir_times = []
    for d in subdirs:
        path = os.path.join(results_dir, d)
        mtime = os.path.getmtime(path)
        dir_times.append((path, mtime, d))
    
    # Sort by modification time (newest first)
    dir_times.sort(key=lambda x: x[1], reverse=True)
    
    # Keep at least 'keep' number of directories regardless of age
    to_keep = dir_times[:keep]
    to_check = dir_times[keep:]
    
    # Check age for remaining directories
    cutoff_time = datetime.now() - timedelta(days=days)
    cutoff_timestamp = cutoff_time.timestamp()
    
    to_delete = [d for d in to_check if d[1] < cutoff_timestamp]
    
    # Log summary
    logger.info(f"Found {len(dir_times)} result directories")
    logger.info(f"Keeping {len(to_keep)} most recent directories")
    logger.info(f"Keeping directories modified in the last {days} days")
    logger.info(f"Will delete {len(to_delete)} directories")
    
    # Delete old directories
    for path, mtime, name in to_delete:
        mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        if dry_run:
            logger.info(f"Would delete: {path} (modified: {mod_time})")
        else:
            try:
                shutil.rmtree(path)
                logger.info(f"Deleted: {path} (modified: {mod_time})")
            except Exception as e:
                logger.error(f"Error deleting {path}: {e}")

def clean_test_results(days: int = 7, keep: int = 5, dry_run: bool = False):
    """
    Clean up old test result directories
    
    Args:
        days: Delete directories older than this many days
        keep: Minimum number of directories to keep regardless of age
        dry_run: If True, only print what would be deleted without actually deleting
    """
    results_dir = "test_results"
    if not os.path.exists(results_dir):
        logger.info(f"No '{results_dir}' directory found, nothing to clean")
        return
    
    # Get all subdirectories
    subdirs = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
    
    # Group directories by test type
    test_types = {}
    for d in subdirs:
        # Extract test type from directory name (e.g., "aspect_ratio_20250509_110658" -> "aspect_ratio")
        parts = d.split('_')
        if len(parts) >= 2:
            test_type = '_'.join(parts[:-2]) if parts[-2].isdigit() else '_'.join(parts[:-1])
            path = os.path.join(results_dir, d)
            mtime = os.path.getmtime(path)
            
            if test_type not in test_types:
                test_types[test_type] = []
            test_types[test_type].append((path, mtime, d))
    
    total_deleted = 0
    
    # Process each test type separately
    for test_type, dirs in test_types.items():
        # Sort by modification time (newest first)
        dirs.sort(key=lambda x: x[1], reverse=True)
        
        # Keep at least 'keep' number of directories regardless of age
        to_keep = dirs[:keep]
        to_check = dirs[keep:]
        
        # Check age for remaining directories
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_timestamp = cutoff_time.timestamp()
        
        to_delete = [d for d in to_check if d[1] < cutoff_timestamp]
        
        # Log summary
        logger.info(f"Test type '{test_type}': Found {len(dirs)} directories")
        logger.info(f"Test type '{test_type}': Keeping {len(to_keep)} most recent directories")
        logger.info(f"Test type '{test_type}': Will delete {len(to_delete)} directories")
        
        # Delete old directories
        for path, mtime, name in to_delete:
            mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            if dry_run:
                logger.info(f"Would delete: {path} (modified: {mod_time})")
            else:
                try:
                    shutil.rmtree(path)
                    logger.info(f"Deleted: {path} (modified: {mod_time})")
                    total_deleted += 1
                except Exception as e:
                    logger.error(f"Error deleting {path}: {e}")
    
    logger.info(f"Deleted {total_deleted} test result directories in total")

def create_archive_directory(dry_run: bool = False):
    """
    Create an archive directory and move older results there
    
    Args:
        dry_run: If True, only print what would be moved without actually moving
    """
    archive_dir = "archive"
    if not os.path.exists(archive_dir) and not dry_run:
        os.makedirs(archive_dir)
        logger.info(f"Created archive directory: {archive_dir}")
    
    # Create subdirectories for different types of results
    subdirs = ["midjourney_results", "test_results"]
    for subdir in subdirs:
        archive_subdir = os.path.join(archive_dir, subdir)
        if not os.path.exists(archive_subdir) and not dry_run:
            os.makedirs(archive_subdir)
            logger.info(f"Created archive subdirectory: {archive_subdir}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Clean up old result directories")
    parser.add_argument("--days", type=int, default=7, help="Delete directories older than this many days")
    parser.add_argument("--keep", type=int, default=5, help="Minimum number of directories to keep regardless of age")
    parser.add_argument("--test-results", action="store_true", help="Clean test_results directory instead of midjourney_results")
    parser.add_argument("--all", action="store_true", help="Clean both midjourney_results and test_results directories")
    parser.add_argument("--create-archive", action="store_true", help="Create archive directories for organizing results")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually delete anything, just print what would be deleted")
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("Running in dry-run mode - no files will be deleted")
    
    if args.create_archive:
        create_archive_directory(dry_run=args.dry_run)
    
    if args.all or not args.test_results:
        logger.info("Cleaning midjourney_results directory")
        clean_midjourney_results(days=args.days, keep=args.keep, dry_run=args.dry_run)
    
    if args.all or args.test_results:
        logger.info("Cleaning test_results directory")
        clean_test_results(days=args.days, keep=args.keep, dry_run=args.dry_run)
    
    logger.info("Cleanup completed")

if __name__ == "__main__":
    main() 