#!/usr/bin/env python3
"""
Tests for datetime handling utilities.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import time
from datetime import datetime
import uuid
import threading

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class TestTimeHandling(unittest.TestCase):
    """Unit tests for time handling functions"""
    
    def test_epoch_time_conversion(self):
        """Test converting epoch time to datetime and back"""
        # Current epoch time
        epoch_now = time.time()
        
        # Convert to datetime
        dt_now = datetime.fromtimestamp(epoch_now)
        
        # Convert back to epoch time
        epoch_again = dt_now.timestamp()
        
        # They should be very close (allowing for microsecond differences)
        self.assertAlmostEqual(epoch_now, epoch_again, places=3)
    
    def test_time_elapsed_calculation(self):
        """Test calculating elapsed time"""
        # Record start time
        start_time = time.time()
        
        # Sleep briefly
        time.sleep(0.1)
        
        # Calculate elapsed time
        elapsed = time.time() - start_time
        
        # Elapsed time should be at least 0.1 seconds
        self.assertGreaterEqual(elapsed, 0.1)
        
        # But not too much more (allowing for machine variations)
        self.assertLess(elapsed, 0.5)
    
    def test_datetime_comparison(self):
        """Test comparing datetime objects"""
        # Create two datetime objects 1 second apart
        time1 = datetime.now()
        time.sleep(1)
        time2 = datetime.now()
        
        # time2 should be later than time1
        self.assertGreater(time2, time1)
        
        # The difference should be at least 1 second
        diff = time2 - time1
        self.assertGreaterEqual(diff.total_seconds(), 1.0)
    
    def test_iso_formatting(self):
        """Test ISO formatting of datetime objects"""
        # Create a datetime object
        dt = datetime.now()
        
        # Format as ISO 8601
        iso_str = dt.isoformat()
        
        # Parse back to datetime
        dt2 = datetime.fromisoformat(iso_str)
        
        # They should be the same
        self.assertEqual(dt, dt2)
    
    def test_datetime_as_filename(self):
        """Test formatting datetime for use in filenames"""
        # Create a datetime object
        dt = datetime.now()
        
        # Format as YYYYMMDD_HHMMSS
        filename_date = dt.strftime("%Y%m%d_%H%M%S")
        
        # Check the format is correct (basic validation)
        self.assertEqual(len(filename_date), 15)
        self.assertTrue(filename_date[8] == '_')
        
        # All characters should be digits except the underscore
        for i, char in enumerate(filename_date):
            if i != 8:  # Skip the underscore
                self.assertTrue(char.isdigit())

if __name__ == "__main__":
    unittest.main() 