#!/usr/bin/env python3
"""
Enhanced upscale handler module for reprocessing Midjourney images.

This module provides functions to work with Midjourney's Discord API
for handling button interactions for upscaling.
"""

import random
import string
import json
import requests
import logging

# Set up logging
logger = logging.getLogger(__name__)

def generate_session_id():
    """
    Generate a random session ID in the format Discord expects.
    
    Returns:
        str: A 32-character session ID starting with 'a' followed by 31 hex characters
    """
    # Start with 'a'
    chars = 'a'
    
    # Add 31 random hex digits
    chars += ''.join(random.choice(string.hexdigits.lower()) for _ in range(31))
    
    return chars

def force_button_click(message_id, custom_id, channel_id, token, session_id=None, guild_id=None):
    """
    Force a button click on a Discord message.
    
    Args:
        message_id (str): The ID of the message containing the button
        custom_id (str): The custom ID of the button to click
        channel_id (str): The ID of the channel containing the message
        token (str): Discord user token
        session_id (str, optional): Session ID to use (will generate if None)
        guild_id (str, optional): Guild ID (server ID)
    
    Returns:
        bool: True if the button click was successful, False otherwise
    """
    if not session_id:
        # Generate a new session ID if none was provided
        session_id = generate_session_id()
    
    url = "https://discord.com/api/v9/interactions"
    
    payload = {
        "type": 3,  # BUTTON click
        "channel_id": channel_id,
        "message_id": message_id,
        "application_id": "936929561302675456",  # Midjourney application ID
        "session_id": session_id,
        "data": {
            "component_type": 2,  # BUTTON
            "custom_id": custom_id
        }
    }
    
    # Add guild_id if provided
    if guild_id:
        payload["guild_id"] = guild_id
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 204:
            # Success (Discord returns 204 No Content for successful interactions)
            logger.info(f"Button click successful for message {message_id}")
            return True
        else:
            logger.error(f"Button click failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception during button click: {e}")
        return False 