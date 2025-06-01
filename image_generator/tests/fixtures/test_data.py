#!/usr/bin/env python3
"""
Common test data for image_generator tests.

This module contains sample data that can be reused across test files
to ensure consistency in test data and reduce duplication.
"""

from bson import ObjectId

# Sample post IDs for testing
SAMPLE_POST_ID = "66b88b70b2979f6117b347f2"

# Sample GridFS metadata for testing
SAMPLE_GRIDFS_METADATA = {
    "variation": "v6.0",
    "variant_idx": 1,
    "post_id": SAMPLE_POST_ID,
    "filename": "v6.0_variant_1_test.jpg",
    "content_type": "image/jpeg",
    "generation_metadata": {
        "prompt": "test prompt",
        "model": "v6.0",
        "timestamp": 1675948800000,  # Example timestamp
        "component_ids": ["12345", "67890"]
    }
}

# Sample post image document for testing
SAMPLE_POST_IMAGE_DOCUMENT = {
    "_id": ObjectId("5f50c31e9c4e1f3de6054fa2"),
    "post_id": SAMPLE_POST_ID,
    "original_prompt": "test prompt",
    "variation": "v6.0",
    "image_ids": {
        "v6.0": [ObjectId("5f50c31e9c4e1f3de6054fa1")]
    },
    "metadata": {
        "generation_time": 1675948800000,
        "completion_time": 1675949000000
    }
}

# Sample image data for testing
SAMPLE_IMAGE_DATA = b"sample image data for testing purposes"

# Sample upscale results in different formats
SAMPLE_UPSCALE_RESULT_FORMAT1 = {
    # Format 1: id and url keys, but also include message_id and image_url for compatibility
    "id": "upscaled_message_id_123",
    "url": "https://example.com/upscaled_image_1.jpg",
    "message_id": "upscaled_message_id_123",  # Added for compatibility
    "image_url": "https://example.com/upscaled_image_1.jpg",  # Added for compatibility
    "button_idx": 1,
    "original_message_id": "original_message_id_123",
    "upscale_time": 1675950000000
}

SAMPLE_UPSCALE_RESULT_FORMAT2 = {
    # Format 2: message_id and image_url keys
    "message_id": "upscaled_message_id_456",
    "image_url": "https://example.com/upscaled_image_2.jpg",
    "button_idx": 2,
    "original_message_id": "original_message_id_456",
    "upscale_time": 1675950200000
}

SAMPLE_UPSCALE_RESULT_BOTH_FORMATS = {
    # Format 3: both sets of keys
    "id": "upscaled_message_id_789",
    "url": "https://example.com/upscaled_image_3.jpg",
    "message_id": "upscaled_message_id_789",
    "image_url": "https://example.com/upscaled_image_3.jpg",
    "button_idx": 3,
    "original_message_id": "original_message_id_789",
    "upscale_time": 1675950400000
}

# Sample buttons for testing
SAMPLE_UPSCALE_BUTTONS = {
    "traditional": [
        {"custom_id": "MJ::JOB::upsample::1::abc123", "label": "U1"},
        {"custom_id": "MJ::JOB::upsample::2::abc123", "label": "U2"},
        {"custom_id": "MJ::JOB::upsample::3::abc123", "label": "U3"},
        {"custom_id": "MJ::JOB::upsample::4::abc123", "label": "U4"}
    ],
    "numbered": [
        {"custom_id": "MJ::JOB::upsample::1::def456", "label": "1"},
        {"custom_id": "MJ::JOB::upsample::2::def456", "label": "2"},
        {"custom_id": "MJ::JOB::upsample::3::def456", "label": "3"},
        {"custom_id": "MJ::JOB::upsample::4::def456", "label": "4"}
    ],
    "new_style": [
        {"custom_id": "MJ::JOB::upsample::1::ghi789", "label": "Upscale (Subtle)"},
        {"custom_id": "MJ::JOB::upsample::2::ghi789", "label": "Upscale (Creative)"}
    ],
    "mixed": [
        {"custom_id": "MJ::JOB::upsample::1::jkl012", "label": "U1"},
        {"custom_id": "MJ::JOB::upsample::2::jkl012", "label": "2"},
        {"custom_id": "MJ::JOB::upsample::3::jkl012", "label": "Upscale (Subtle)"},
        {"custom_id": "MJ::JOB::upsample::4::jkl012", "label": "4"}
    ]
}

# Sample variations
SAMPLE_VARIATIONS = ["v6.0", "v6.1", "niji"] 