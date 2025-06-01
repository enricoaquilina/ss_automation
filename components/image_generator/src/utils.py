"""
Utility functions and constants for the Discord-Midjourney client
"""

import time
import asyncio
import random
import logging
import os
from datetime import datetime
from typing import Callable, Any, Optional, Dict, Union, List, Tuple

# Configure logging
logger = logging.getLogger("midjourney_generator")

# Constants
MIDJOURNEY_APP_ID = "936929561302675456"  # Midjourney bot application ID
DISCORD_API_URL = "https://discord.com/api/v10"
GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"


async def save_image(url: str, file_path: str) -> bool:
    """
    Download and save an image from URL
    
    Args:
        url: URL of the image to download
        file_path: Path where the image should be saved
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not url:
        logger.error("No URL provided for download")
        return False
    
    try:
        # Create directory if it doesn't exist
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download the image
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(file_path, "wb") as f:
                        f.write(await resp.read())
                    logger.info(f"Saved image to {file_path}")
                    return True
                else:
                    logger.error(f"Failed to download image: {resp.status}")
                    return False
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return False


def save_json(data: Dict[str, Any], file_path: str) -> bool:
    """
    Save data to a JSON file
    
    Args:
        data: Data to save
        file_path: Path where the JSON should be saved
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save JSON
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved JSON to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON: {e}")
        return False


def validate_discord_url(url: str) -> bool:
    """
    Validate that a URL is a Discord attachment URL
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if valid Discord URL, False otherwise
    """
    if not url:
        return False
    
    # Check for Discord CDN domains
    if not (url.startswith("https://cdn.discordapp.com/") or 
            url.startswith("https://media.discordapp.net/")):
        return False
    
    # Check for attachments path and proper segment count
    parts = url.split("/")
    if len(parts) < 7 or "attachments" not in parts:
        return False
    
    # Check for image file extension
    if not parts[-1].lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return False
    
    return True


def extract_prompt_from_url(url: str) -> str:
    """
    Extract prompt information from Discord image URL
    
    Args:
        url: Discord image URL
        
    Returns:
        str: Extracted prompt text or empty string if not found
    """
    if not url:
        return ""
    
    # Get the filename from URL
    filename = url.split("/")[-1]
    
    # Extract prompt section (after username_ prefix, before _Upscale or UUID)
    match = re.search(r"[^_]+_(.+?)(?:_Upscale_\d+|_\w{6}|\.\w+$)", filename)
    if match:
        # Replace underscores with spaces
        return match.group(1).replace("_", " ")
    
    # Fallback: just remove username prefix and file extension
    parts = filename.split("_", 1)
    if len(parts) > 1:
        prompt_part = parts[1]
        # Remove file extension and any trailing UUID
        prompt_part = re.sub(r"(_\w{6})?\.\w+$", "", prompt_part)
        return prompt_part.replace("_", " ")
    
    return ""


def validate_url_matches_prompt(url: str, prompt: str) -> bool:
    """
    Validate that a URL contains elements from the prompt
    
    Args:
        url: Discord image URL
        prompt: Prompt text to match
        
    Returns:
        bool: True if URL matches prompt, False otherwise
    """
    if not url or not prompt:
        return False
    
    # Extract prompt words from URL
    url_prompt = extract_prompt_from_url(url)
    if not url_prompt:
        return False
    
    # Clean and tokenize both prompts
    url_prompt_words = set(url_prompt.lower().split())
    prompt_words = set(prompt.lower().split())
    
    # Count matching words
    matching_words = url_prompt_words.intersection(prompt_words)
    
    # Consider it a match if at least 2 words match or 30% of prompt words match
    min_matches = min(2, len(prompt_words))
    match_ratio = len(matching_words) / len(prompt_words) if prompt_words else 0
    
    return len(matching_words) >= min_matches or match_ratio >= 0.3


def detect_variant_from_url(url: str) -> Optional[int]:
    """
    Detect which upscale variant a URL represents
    
    Args:
        url: Discord image URL
        
    Returns:
        Optional[int]: Variant number (1-4) or None if not an upscale URL
    """
    if not url:
        return None
    
    # Look for explicit Upscale_N pattern
    match = re.search(r"_Upscale_(\d)_", url)
    if match:
        return int(match.group(1))
    
    # Try other patterns like "variant_1" or "upscale_1"
    for pattern in [r"variant_(\d)", r"upscale_(\d)", r"_v(\d)_", r"_u(\d)_"]:
        match = re.search(pattern, url.lower())
        if match:
            return int(match.group(1))
    
    return None


def comprehensive_url_validation(url: str, prompt: str, target_variant: Optional[int] = None) -> bool:
    """
    Comprehensive validation combining multiple checks
    
    Args:
        url: Discord image URL
        prompt: Prompt text to match
        target_variant: Expected variant number (1-4) if applicable
        
    Returns:
        bool: True if URL passes all checks, False otherwise
    """
    # Basic format validation
    if not validate_discord_url(url):
        return False
    
    # Prompt content validation
    if not validate_url_matches_prompt(url, prompt):
        return False
    
    # Variant validation (if applicable)
    if target_variant is not None:
        detected_variant = detect_variant_from_url(url)
        if detected_variant != target_variant:
            return False
    
    return True


def create_result_directory() -> str:
    """
    Create a timestamped directory for results
    
    Returns:
        str: Path to the created directory
    """
    # Create results directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"midjourney_results/{timestamp}"
    os.makedirs(results_dir, exist_ok=True)
    return results_dir


class RateLimiter:
    """
    Rate limiter for Discord API calls with exponential backoff for retries
    
    Implements:
    - Minimum 350ms delay between API calls as recommended by Discord
    - Exponential backoff for retries with jitter
    - Tracking of rate limit headers to adjust timing
    """
    
    def __init__(self, base_delay: float = 0.35):
        """
        Initialize the rate limiter
        
        Args:
            base_delay: Base delay between API calls in seconds (default: 350ms)
        """
        self.base_delay = base_delay
        self.last_request_time = 0
        self.rate_limit_remaining = {}  # endpoint -> remaining requests
        self.rate_limit_reset = {}      # endpoint -> reset time
        
    async def wait(self, endpoint: str = None):
        """
        Wait for the appropriate time before making an API call
        
        Args:
            endpoint: Optional endpoint string to track specific rate limits
        """
        # Check if we need to wait for a specific endpoint's rate limit
        if endpoint and endpoint in self.rate_limit_reset:
            reset_time = self.rate_limit_reset[endpoint]
            remaining = self.rate_limit_remaining.get(endpoint, 1)
            
            if remaining <= 0:
                # We've hit the rate limit for this endpoint
                current_time = time.time()
                if current_time < reset_time:
                    wait_time = reset_time - current_time + 0.1  # Add 100ms buffer
                    logger.warning(f"Rate limit reached for {endpoint}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
        
        # Always enforce the base delay between all requests
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.base_delay:
            wait_time = self.base_delay - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        
    def update_rate_limits(self, endpoint: str, headers: Dict[str, str]):
        """
        Update rate limit information from API response headers
        
        Args:
            endpoint: The API endpoint that was called
            headers: Response headers containing rate limit information
        """
        if 'X-RateLimit-Remaining' in headers:
            self.rate_limit_remaining[endpoint] = int(headers['X-RateLimit-Remaining'])
            
        if 'X-RateLimit-Reset' in headers:
            self.rate_limit_reset[endpoint] = float(headers['X-RateLimit-Reset'])
            
    async def with_retry(self, func: Callable, *args, max_retries: int = 5, 
                        retry_status_codes: list = [429, 500, 502, 503, 504], **kwargs) -> Any:
        """
        Execute a function with exponential backoff retry logic
        
        Args:
            func: The async function to call
            *args: Arguments to pass to the function
            max_retries: Maximum number of retries before giving up
            retry_status_codes: HTTP status codes that should trigger a retry
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            The last exception encountered if all retries fail
        """
        retry_count = 0
        last_exception = None
        
        while retry_count <= max_retries:
            try:
                # Wait for appropriate rate limit
                await self.wait()
                
                # Call the function
                result = await func(*args, **kwargs)
                
                # Check if result is a response with status code
                if hasattr(result, 'status_code') and result.status_code in retry_status_codes:
                    # Handle rate limit specifically
                    if result.status_code == 429:
                        retry_after = int(result.headers.get('Retry-After', 1))
                        logger.warning(f"Rate limited (429), waiting {retry_after}s before retry")
                        await asyncio.sleep(retry_after)
                        retry_count += 1
                        continue
                    # Handle other retry-able status codes
                    retry_count += 1
                    backoff = (2 ** retry_count) + random.uniform(0, 0.5)
                    logger.warning(f"Received status code {result.status_code}, retry {retry_count}/{max_retries}. Waiting {backoff:.2f}s")
                    await asyncio.sleep(backoff)
                    continue
                
                # If we made it here, the call succeeded
                return result
                
            except Exception as e:
                last_exception = e
                retry_count += 1
                
                if retry_count > max_retries:
                    logger.error(f"Max retries ({max_retries}) exceeded")
                    break
                
                # Calculate backoff with jitter
                backoff = (2 ** retry_count) + random.uniform(0, 0.5)
                logger.warning(f"Retry {retry_count}/{max_retries} after error: {str(e)}. Waiting {backoff:.2f}s")
                await asyncio.sleep(backoff)
        
        # If we've exhausted retries, raise the last exception
        raise last_exception if last_exception else Exception("Unknown error in retry logic")

# Error handling classes for different Midjourney response scenarios
class MidjourneyError(Exception):
    """Base class for Midjourney errors"""
    pass

class ModerationError(MidjourneyError):
    """Base class for all moderation-related errors"""
    pass

class PreModerationError(ModerationError):
    """Error when prompt is pre-moderated (never appears in channel)"""
    pass

class PostModerationError(ModerationError):
    """Error when prompt is post-moderated (appears but gets stopped)"""
    def __init__(self, message_id=None, content=None):
        self.message_id = message_id
        self.content = content
        super().__init__(f"Generation stopped by Midjourney moderation. Message: {content}")

class EphemeralModerationError(ModerationError):
    """Error when prompt triggers soft moderation (message deleted after completion)"""
    pass
    
class InvalidRequestError(MidjourneyError):
    """Error when the request is invalid or has format issues"""
    pass
    
class QueueFullError(MidjourneyError):
    """Error when Midjourney queue is full"""
    pass
    
class JobQueuedError(MidjourneyError):
    """Error when job is queued due to account limitations"""
    def __init__(self, message_id=None):
        self.message_id = message_id
        super().__init__(f"Job queued, waiting in line. Message ID: {message_id}")

# Helper functions for response handling
def is_pre_moderation(before_id: str, current_messages: list, wait_time: float) -> bool:
    """
    Check if a prompt was pre-moderated (never appears in channel)
    
    Args:
        before_id: ID of the message before sending the prompt
        current_messages: Current messages in the channel
        wait_time: How long we've been waiting in seconds
        
    Returns:
        True if pre-moderation is detected, False otherwise
    """
    # If waited more than 30 seconds and still seeing the same first message
    if wait_time > 30 and current_messages and current_messages[0]['id'] == before_id:
        return True
    return False

def is_post_moderation(message: Dict[str, Any]) -> bool:
    """
    Check if a message indicates post-moderation (generation stopped)
    
    Args:
        message: Message data from Discord API
        
    Returns:
        True if post-moderation is detected, False otherwise
    """
    if message and 'content' in message:
        return message['content'].endswith('(Stopped)')
    return False

def is_ephemeral_moderation(message_id: str, current_messages: list) -> bool:
    """
    Check if a message was deleted after processing (ephemeral moderation)
    
    Args:
        message_id: The original message ID that was being tracked
        current_messages: Current messages in the channel
        
    Returns:
        True if the message is no longer found, False otherwise
    """
    if message_id:
        return not any(msg['id'] == message_id for msg in current_messages)
    return False 