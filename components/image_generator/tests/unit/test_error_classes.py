#!/usr/bin/env python3
"""
Tests for the specialized Midjourney error classes
"""

import os
import sys
import pytest

# Add src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from utils import (
    MidjourneyError,
    PreModerationError,
    PostModerationError,
    EphemeralModerationError,
    InvalidRequestError,
    QueueFullError,
    JobQueuedError
)


class TestMidjourneyErrors:
    """Tests for the specialized Midjourney error classes"""
    
    def test_base_error(self):
        """Test the base MidjourneyError class"""
        error = MidjourneyError("Base error message")
        assert str(error) == "Base error message"
        assert isinstance(error, Exception)
    
    def test_pre_moderation_error(self):
        """Test the PreModerationError class"""
        error = PreModerationError("Pre-moderation error")
        assert str(error) == "Pre-moderation error"
        assert isinstance(error, MidjourneyError)
    
    def test_post_moderation_error(self):
        """Test the PostModerationError class with message ID and content"""
        message_id = "12345678901234"
        content = "Test prompt (Stopped)"
        error = PostModerationError(message_id=message_id, content=content)
        
        # We don't check for message_id in the string representation, just that it's stored
        assert hasattr(error, "message_id")
        assert hasattr(error, "content")
        assert error.message_id == message_id
        assert error.content == content
        assert content in str(error)
        assert isinstance(error, MidjourneyError)
    
    def test_ephemeral_moderation_error(self):
        """Test the EphemeralModerationError class"""
        error = EphemeralModerationError("Ephemeral moderation error")
        assert str(error) == "Ephemeral moderation error"
        assert isinstance(error, MidjourneyError)
    
    def test_invalid_request_error(self):
        """Test the InvalidRequestError class"""
        error = InvalidRequestError("Invalid request error")
        assert str(error) == "Invalid request error"
        assert isinstance(error, MidjourneyError)
    
    def test_queue_full_error(self):
        """Test the QueueFullError class"""
        error = QueueFullError("Queue full error")
        assert str(error) == "Queue full error"
        assert isinstance(error, MidjourneyError)
    
    def test_job_queued_error(self):
        """Test the JobQueuedError class with message ID"""
        message_id = "12345678901234"
        error = JobQueuedError(message_id=message_id)
        
        # For JobQueuedError, we're verifying the message_id is in the string representation
        assert hasattr(error, "message_id")
        assert error.message_id == message_id
        assert message_id in str(error)
        assert isinstance(error, MidjourneyError)
    
    def test_error_hierarchy(self):
        """Test that all error classes are properly derived from MidjourneyError"""
        assert issubclass(PreModerationError, MidjourneyError)
        assert issubclass(PostModerationError, MidjourneyError)
        assert issubclass(EphemeralModerationError, MidjourneyError)
        assert issubclass(InvalidRequestError, MidjourneyError)
        assert issubclass(QueueFullError, MidjourneyError)
        assert issubclass(JobQueuedError, MidjourneyError)


if __name__ == "__main__":
    pytest.main(["-v"]) 