import logging
import time
import requests
from typing import Optional, Dict, Any, List
from tqdm import tqdm
import re

from ..base import ImageGenerationProvider

class MidjourneyClient(ImageGenerationProvider):
    """Client for interacting with Midjourney through Discord"""
    
    # Base Discord API constants
    API_URL = "https://discord.com/api/v10"
    APPLICATION_ID = "936929561302675456"
    BOT_ID = "936929561302675456"
    DATA_ID = "938956540159881230"
    SESSION_ID = "9c4055428e13bcbf2248a6b36084c5f3"
    
    def __init__(self, 
                 channel_id: str,
                 oauth_token: str):
        """Initialize the client
        
        Important: This initialization sets up critical tracking mechanisms:
        1. Message cache for current session only
        2. Generation lock to prevent overlapping operations
        3. Timestamp of client start to ignore old messages
        
        The session_start_time is stored as Unix timestamp (seconds since 1970)
        to match Discord's snowflake timestamp after conversion.
        """
        # Initialize basic attributes
        self.channel_id = channel_id
        self.oauth_token = oauth_token
        
        # Initialize rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0
        
        # Initialize tracking attributes
        self.current_generation_id = None
        self.last_prompt = None
        self._generation_lock = False
        
        # Add session start timestamp and clear cache
        self.session_start_time = time.time()  # Unix timestamp in seconds
        self._message_cache = {}
        
        try:
            # Initialize client
            self.client = self._init_client()
            
            # Get guild ID first
            self.guild_id = self._get_guild_id()
            logging.info(f"Using guild ID: {self.guild_id}")
            
            # Get user ID
            self.user_id = self._get_user_id()
            logging.info(f"Using user ID: {self.user_id}")
            
            # Get command data with fallback
            self.command_data = self._get_imagine_command() or {
                'name': 'imagine',
                'version': '1166847114203123795',  # Known working version
                'id': self.DATA_ID
            }
            self.data_version = self.command_data.get('version')
            logging.info(f"Using command version: {self.data_version}")
            
        except Exception as e:
            logging.error(f"Error initializing client: {str(e)}")
            logging.exception(e)
            # Set fallback values
            self.guild_id = "1125101061015875654"  # Known working guild ID
            self.user_id = "936929561302675456"    # Midjourney bot ID
            self.data_version = "1166847114203123795"  # Known working version

    def _init_client(self) -> requests.Session:
        """Initialize Discord API client"""
        client = requests.Session()
        
        # Add required Discord headers
        client.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Origin': 'https://discord.com',
            'X-Discord-Locale': 'en-US',
            'X-Debug-Options': 'bugReporterEnabled',
            'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
        })
        return client
        
    def _get_guild_id(self) -> str:
        """Get Discord guild ID"""
        try:
            # First try getting channel info
            response = self.client.get(
                f'{self.API_URL}/channels/{self.channel_id}',
                headers={
                    'Authorization': self.oauth_token,
                    'Content-Type': 'application/json'
                }
            )
            
            if not response.ok:
                logging.error(f"Failed to get channel info: {response.status_code} - {response.text}")
                return self._get_guild_id_from_channel()
                
            data = response.json()
            guild_id = data.get('guild_id')
            
            if not guild_id:
                logging.error("No guild_id in channel response")
                return self._get_guild_id_from_channel()
                
            logging.info(f"Successfully got guild ID: {guild_id}")
            return guild_id
            
        except Exception as e:
            logging.error(f"Error getting guild ID: {str(e)}")
            logging.exception(e)
            return self._get_guild_id_from_channel()

    def _get_guild_id_from_channel(self) -> str:
        """Alternate method to get guild ID from channel messages"""
        try:
            # Get recent messages from the channel
            response = self.client.get(
                f'{self.API_URL}/channels/{self.channel_id}/messages?limit=1',
                headers={
                    'Authorization': self.oauth_token,
                    'Content-Type': 'application/json'
                }
            )
            
            if not response.ok:
                logging.error(f"Failed to get channel messages: {response.status_code} - {response.text}")
                return "1109819100011962439"  # Known working guild ID
                
            messages = response.json()
            if messages and len(messages) > 0:
                guild_id = messages[0].get('guild_id')
                if guild_id:
                    logging.info(f"Got guild ID from messages: {guild_id}")
                    return guild_id
                    
            logging.warning("Could not get guild ID from messages, using fallback")
            return "1109819100011962439"  # Known working guild ID
            
        except Exception as e:
            logging.error(f"Error in alternate guild ID method: {str(e)}")
            logging.exception(e)
            return "1109819100011962439"  # Known working guild ID

    def _get_user_id(self) -> str:
        """Get Discord user ID"""
        try:
            response = self.client.get(
                f'{self.API_URL}/users/@me',
                headers={
                    'Authorization': self.oauth_token,
                    'Content-Type': 'application/json'
                }
            )
            
            if not response.ok:
                logging.error(f"Failed to get user info: {response.status_code} - {response.text}")
                # Use hardcoded fallback
                return "936929561302675456"  # Midjourney bot ID as fallback
                
            data = response.json()
            user_id = data.get('id')
            
            if not user_id:
                logging.error("No user ID in response")
                return "936929561302675456"  # Midjourney bot ID as fallback
                
            logging.info(f"Successfully got user ID: {user_id}")
            return user_id
            
        except Exception as e:
            logging.error(f"Error getting user ID: {str(e)}")
            logging.exception(e)
            return "936929561302675456"  # Midjourney bot ID as fallback

    def generate(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate an image from a prompt
        
        Args:
            prompt: The base prompt to generate from
            options: Optional dictionary of generation options
            
        Supported options:
            - seed: Random seed for reproducibility
            - ar: Aspect ratio (e.g. "4:5")
            - q: Quality setting
            - niji: Boolean flag for niji model
            - v: Version string, supported values:
                - "6.0": Uses --v 6.0 parameter
                - "6.1": Uses --v 6.1 parameter
                
        IMPORTANT: When adding new versions:
        1. Add the version here in the documentation
        2. Add corresponding handling in the options_str construction below
        3. Add corresponding handling in GenerationService._process_variation()
        
        Returns:
            Dict containing:
            - id: Message ID
            - images: List of image URLs
            - metadata: Full message data
        """
        try:
            # Wait if there's an ongoing generation
            while self._generation_lock:
                logging.info("Waiting for previous generation to complete...")
                time.sleep(5)

            self._generation_lock = True
            
            try:
                # Clear previous generation state
                self.current_generation_id = None
                self._message_cache = {}
                
                # Format options string
                options_str = ""
                if options:
                    # Handle seed
                    if 'seed' in options:
                        options_str += f" --seed {options['seed']}"
                    
                    # Handle aspect ratio
                    if 'ar' in options:
                        options_str += f" --ar {options['ar']}"
                        
                    # Handle quality
                    if 'q' in options:
                        options_str += f" --q {options['q']}"
                        
                    # Handle niji variation
                    if options.get('niji'):
                        options_str += " --niji"
                    # Handle v6.1 variation
                    elif options.get('v') == '6.1':
                        options_str += " --v 6.1"
                    # Handle v6.0 variation
                    elif options.get('v') == '6.0':
                        options_str += " --v 6.0"
                        
                # Format final prompt
                final_prompt = f"{prompt}{options_str}"
                logging.info(f"Sending generation prompt: {final_prompt}")
                
                # Send the generation request
                message = self._send_message(final_prompt)
                if not message:
                    raise Exception("Failed to generate image")
                    
                # Cache the message and set as current
                self.current_generation_id = message['id']
                self._message_cache[message['id']] = message
                
                return {
                    'id': message['id'],
                    'images': [{'url': attachment['url']} for attachment in message.get('attachments', [])],
                    'metadata': message
                }

            finally:
                self._generation_lock = False

        except Exception as e:
            self._generation_lock = False
            logging.error(f"Error generating image: {str(e)}")
            raise
            
    def _get_imagine_command(self) -> Optional[Dict]:
        """Get latest imagine command data"""
        try:
            # Try getting commands directly from application endpoint
            response = self.client.get(
                f"{self.API_URL}/applications/{self.APPLICATION_ID}/commands",
                params={"with_localizations": False},
                headers={
                    'Authorization': self.oauth_token,
                    'Content-Type': 'application/json'
                }
            )
            
            if response.status_code == 404:
                logging.error("Application not found or bot doesn't have access")
                return self._get_fallback_command()
            elif response.status_code == 403:
                logging.error("Bot lacks permissions to access commands")
                return self._get_fallback_command()
            elif not response.ok:
                logging.error(f"Failed to get commands: {response.status_code} - {response.text}")
                return self._get_fallback_command()
            
            commands = response.json()
            
            # Find the imagine command
            for cmd in commands:
                if cmd.get('name') == 'imagine':
                    version = cmd.get('version', '1166847114203123795')
                    cmd_id = cmd.get('id', self.DATA_ID)
                    logging.info(f"Found imagine command version: {version}, id: {cmd_id}")
                    return {
                        'name': 'imagine',
                        'version': version,
                        'id': cmd_id
                    }
            
            logging.warning("No imagine command found, using fallback")
            return self._get_fallback_command()
            
        except Exception as e:
            logging.error(f"Error getting imagine command: {str(e)}")
            logging.exception(e)
            return self._get_fallback_command()

    def _get_fallback_command(self) -> Dict:
        """Get fallback command data"""
        return {
            'name': 'imagine',
            'version': '1166847114203123795',  # Known working version
            'id': self.DATA_ID
        }

    def _send_message(self, prompt: str) -> Optional[Dict]:
        """Send a message to Discord to generate an image"""
        try:
            # Get fresh command data before sending
            command_data = self._get_imagine_command()
            if command_data:
                self.data_version = command_data.get('version')
            
            payload = {
                "type": 2,
                "application_id": self.APPLICATION_ID,
                "guild_id": self.guild_id,
                "channel_id": self.channel_id,
                "session_id": self.SESSION_ID,
                "data": {
                    "version": self.data_version,
                    "id": self.DATA_ID,
                    "name": "imagine",
                    "type": 1,
                    "options": [{
                        "type": 3,
                        "name": "prompt",
                        "value": prompt
                    }],
                    "attachments": []
                }
            }
            
            max_retries = 3
            retry_delay = 5
            command_sent = False
            
            for attempt in range(max_retries):
                try:
                    if command_sent:
                        logging.warning("Command already sent, skipping retry")
                        break
                        
                    headers = {
                        'Authorization': self.oauth_token,
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Origin': 'https://discord.com',
                        'Referer': f'https://discord.com/channels/{self.guild_id}/{self.channel_id}',
                        'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
                    }
                    
                    response = self.client.post(
                        f"{self.API_URL}/interactions",
                        json=payload,
                        headers=headers
                    )
                    
                    if response.status_code == 204:
                        logging.info("Successfully sent generation command")
                        command_sent = True
                        # Add small delay to allow Discord to process
                        time.sleep(2)
                        message = self._wait_for_generation(prompt)
                        if message:
                            self.current_generation_id = message['id']
                            return message
                        logging.error("Failed to get generation result after successful command")
                        continue
                        
                    logging.error(f"Failed to send generation command. Status: {response.status_code}")
                    logging.error(f"Response content: {response.text}")
                    if attempt < max_retries - 1:
                        logging.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    return None
                    
                except Exception as e:
                    logging.error(f"Error sending message: {str(e)}")
                    if attempt < max_retries - 1 and not command_sent:
                        logging.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    logging.exception(e)
                    return None
                    
        except Exception as e:
            logging.error(f"Error sending message: {str(e)}")
            logging.exception(e)
            return None
            
    def _wait_for_generation(self, prompt: str, timeout: int = 120) -> Optional[Dict]:
        """Wait for a generation to complete and buttons to appear
        
        CRITICAL: This method implements the two-phase wait process that ensures
        both image and buttons are available before proceeding. DO NOT modify the
        button detection or message matching logic.
        
        Wait process:
        1. First waits for message with matching prompt and image
        2. Then waits for upscale buttons to appear
        3. Only proceeds when both conditions are met
        
        Button requirements:
        - Must have U1-U4 buttons
        - Buttons must have valid custom_ids
        - Message must be from current session
        
        Args:
            prompt: The generation prompt to match
            timeout: Maximum wait time in seconds
            
        Returns:
            Complete message data with buttons if successful, None otherwise
        """
        try:
            start_time = time.time()
            progress_bar = None
            last_progress = None
            message_with_image = None
            
            while time.time() - start_time < timeout:
                try:
                    messages = self._get_recent_messages()
                    
                    # Check each message
                    for message in messages:
                        # Skip messages not from Midjourney
                        if str(message.get('author', {}).get('id')) != self.BOT_ID:
                            continue
                            
                        # Skip messages from before this session
                        message_timestamp = int(int(message['id']) >> 22) / 1000 + 1420070400000
                        if message_timestamp < self.session_start_time:
                            continue
                            
                        content = message.get('content', '').strip()
                        
                        # Check if this is a progress message for our prompt
                        if content.startswith(prompt[:50]):
                            # Check for progress percentage
                            progress_match = re.search(r'\((\d+)%\)', content)
                            if progress_match:
                                progress = int(progress_match.group(1))
                                if progress != last_progress:
                                    last_progress = progress
                                    logging.info(f"Generation progress: {progress}%")
                                    
                                    if progress_bar is None:
                                        progress_bar = tqdm(total=100, desc="Generating")
                                    progress_bar.n = progress
                                    progress_bar.refresh()
                                    
                        # Check if this message has the image
                        if message.get('attachments'):
                            message_with_image = message
                            logging.info("Found message with image, waiting for buttons...")
                            
                        # If we have a message with image, check for buttons
                        if (message_with_image and 
                            message['id'] == message_with_image['id'] and 
                            message.get('components')):
                            
                            # Verify upscale buttons exist
                            buttons = self._get_upscale_buttons(message)
                            if buttons:
                                if progress_bar:
                                    progress_bar.n = 100
                                    progress_bar.refresh()
                                    progress_bar.close()
                                logging.info("Generation completed successfully with image and buttons")
                                
                                # Cache the complete message
                                if not hasattr(self, '_message_cache'):
                                    self._message_cache = {}
                                self._message_cache[message['id']] = message
                                
                                # Log button details for debugging
                                logging.debug(f"Found {len(buttons)} upscale buttons:")
                                for btn in buttons:
                                    logging.debug(f"Button {btn['label']} with ID {btn['custom_id']}")
                                
                                return message
                            
                    time.sleep(2)
                    
                except Exception as e:
                    logging.error(f"Error checking generation progress: {str(e)}")
                    time.sleep(2)
                    
            if progress_bar:
                progress_bar.close()
            logging.error("Generation timed out or buttons did not appear")
            return None
            
        except Exception as e:
            if progress_bar:
                progress_bar.close()
            logging.error(f"Error waiting for generation: {str(e)}")
            return None
            
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a message by ID
        
        Args:
            message_id: Message ID to retrieve
            
        Returns:
            Message data if found, None otherwise
        """
        try:
            response = self.client.get(
                f"{self.API_URL}/channels/{self.channel_id}/messages/{message_id}"
            )
            
            if response.status_code == 200:
                return response.json()
                
            logging.error(f"Failed to get message {message_id}: {response.status_code}")
            return None
            
        except Exception as e:
            logging.error(f"Error getting message: {str(e)}")
            return None
            
    def get_variations(self, generation_id: str, count: int = 4) -> List[Dict[str, Any]]:
        """Get variations of a generated image
        
        Args:
            generation_id: ID of the original generation
            count: Number of variations to generate
            
        Returns:
            List of variation data dictionaries
        """
        # For Midjourney, variations are part of the initial generation
        # This method is included for compatibility with other providers
        message = self._get_message(generation_id)
        if not message or not message.get('attachments'):
            return []
            
        # Return the initial variations as a list
        return [{
            'id': f"{generation_id}_v{i+1}",
            'url': message['attachments'][0]['url'],
            'metadata': {
                'variation_index': i+1,
                'message_id': generation_id
            }
        } for i in range(min(count, 4))]
        
    def upscale(self, generation_id: str, variation_index: int) -> Dict[str, Any]:
        """Upscale a specific variation of a generated image
        
        This method handles the upscaling process by:
        1. Finding the original message (from cache or history)
        2. Locating the appropriate upscale button
        3. Sending the upscale request with proper headers
        4. Waiting for and retrieving the upscaled result
        
        Important: This method relies on proper message caching from
        the generation phase. The generation_id must match the current
        generation to prevent mixing up different generations.
        
        Args:
            generation_id: ID of the original generation message
            variation_index: Index of the variation to upscale (1-4)
            
        Returns:
            Dictionary containing:
            - id: ID of the upscaled message
            - url: URL of the upscaled image
            - metadata: Full message data from Discord
            
        Raises:
            Exception: If any part of the upscale process fails
        """
        try:
            # Verify this upscale belongs to current generation
            if self.current_generation_id and generation_id != self.current_generation_id:
                raise Exception(f"Cannot upscale message {generation_id} while generation {self.current_generation_id} is in progress")

            logging.info(f"Starting upscale process for message {generation_id}, index {variation_index}")
            
            # Get message from cache or history
            message = self._get_cached_message(generation_id)
            if not message:
                message = self._find_message_in_history(generation_id)
                
            if not message:
                raise Exception(f"Could not find message {generation_id}")
            
            # Get available upscale buttons
            buttons = self._get_upscale_buttons(message)
            if not buttons:
                raise Exception("No upscale buttons found")
            
            # Find matching button for index
            button = None
            for b in buttons:
                if b['label'] == f'U{variation_index}':
                    button = b
                    break
                
            if not button:
                raise Exception(f"No button found for U{variation_index}")
            
            logging.info(f"Found upscale button {button['label']} with ID {button['custom_id']}")
            
            # Send upscale request with proper headers
            headers = {
                'Authorization': self.oauth_token,
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Origin': 'https://discord.com',
                'Referer': f'https://discord.com/channels/{self.guild_id}/{self.channel_id}',
                'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
            }
            
            payload = {
                "type": 3,  # INTERACTION_MESSAGE_COMPONENT
                "application_id": self.APPLICATION_ID,
                "guild_id": self.guild_id,
                "channel_id": self.channel_id,
                "session_id": self.SESSION_ID,
                "message_id": generation_id,
                "message_flags": 0,
                "data": {
                    "component_type": 2,  # BUTTON
                    "custom_id": button['custom_id']
                },
                "nonce": str(int(time.time() * 1000))  # Add nonce for request uniqueness
            }
            
            response = self.client.post(
                f"{self.API_URL}/interactions",
                json=payload,
                headers=headers
            )
            
            if response.status_code != 204:
                error_text = response.text if response.text else "No error details"
                logging.error(f"Upscale request failed with status {response.status_code}: {error_text}")
                raise Exception(f"Failed to send upscale request: {response.status_code}")
            
            logging.info("Upscale request sent successfully")
            
            # Wait for upscale result with proper headers
            result = self._wait_for_upscale(generation_id, timeout=60)
            if not result:
                raise Exception("Failed to get upscale result")
            
            return {
                'id': result['id'],
                'url': result['attachments'][0]['url'] if result.get('attachments') else None,
                'metadata': result
            }
            
        except Exception as e:
            logging.error(f"Error upscaling image: {str(e)}")
            logging.exception(e)
            raise
            
    def _get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a Discord message by ID"""
        try:
            response = self.client.get(
                f"{self.API_URL}/channels/{self.channel_id}/messages/{message_id}"
            )
            
            if response.status_code == 200:
                return response.json()
                
            logging.error(f"Failed to get message {message_id}: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            logging.error(f"Error getting message: {str(e)}")
            return None
            
    def _get_upscale_buttons(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get available upscale buttons from a message
        
        This method extracts upscale buttons (U1-U4) from a Discord message.
        The buttons must be present for upscaling to work. The method is
        critical for the upscale sequencing process.
        
        Important: Do not modify the button detection logic as it affects
        the entire upscale workflow.
        
        Args:
            message: Discord message data containing components
            
        Returns:
            List of button data with:
            - custom_id: Button's Discord component ID
            - label: Button label (U1, U2, etc.)
        """
        buttons = []
        
        if not message.get('components'):
            return []
            
        for row in message['components']:
            for component in row.get('components', []):
                if component.get('type') == 2:  # Button type
                    label = component.get('label', '')
                    if label.startswith('U') and label[1:].isdigit():
                        buttons.append({
                            'custom_id': component['custom_id'],
                            'label': label
                        })
                        
        return buttons
        
    def _send_button_click(self, message_id: str, button_id: str) -> Optional[Dict]:
        """Send a button click to Discord
        
        Args:
            message_id: ID of the message containing the button
            button_id: ID of the button to click
            
        Returns:
            Response data if successful, None otherwise
        """
        try:
            response = self.client.post(
                f"{self.API_URL}/interactions",
                json={
                    "type": 3,
                    "application_id": self.APPLICATION_ID,
                    "guild_id": self.guild_id,
                    "channel_id": self.channel_id,
                    "session_id": self.SESSION_ID,
                    "message_id": message_id,
                    "data": {
                        "component_type": 2,
                        "custom_id": button_id
                    }
                }
            )
            
            if response.status_code == 204:
                logging.info(f"Button click sent successfully")
                return {'success': True}
                
            logging.error(f"Failed to send button click: {response.status_code}")
            return None
            
        except Exception as e:
            logging.error(f"Error sending button click: {str(e)}")
            return None
            
    def _wait_for_upscale(self, message_id: str, timeout: int = 60) -> Optional[Dict]:
        """Wait for an upscale operation to complete
        
        This method polls the Discord channel for new messages until it finds
        the upscaled result or times out. It specifically looks for messages that:
        1. Come from the Midjourney bot
        2. Have attachments (images)
        3. Reference the original message
        
        Args:
            message_id: ID of the original message being upscaled
            timeout: Maximum time to wait in seconds (default: 60)
            
        Returns:
            The message containing the upscaled image if found, None otherwise
        """
        try:
            start_time = time.time()
            logging.info(f"Waiting for upscale completion (timeout: {timeout}s)...")
            
            headers = {
                'Authorization': self.oauth_token,
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Origin': 'https://discord.com',
                'Referer': f'https://discord.com/channels/{self.guild_id}/{self.channel_id}',
                'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
            }
            
            while time.time() - start_time < timeout:
                try:
                    response = self.client.get(
                        f"{self.API_URL}/channels/{self.channel_id}/messages?limit=10",
                        headers=headers
                    )
                    
                    if not response.ok:
                        logging.error(f"Failed to get messages: {response.status_code} - {response.text}")
                        time.sleep(2)
                        continue
                        
                    messages = response.json()
                    
                    # Check each message
                    for message in messages:
                        # Skip messages not from Midjourney
                        if str(message.get('author', {}).get('id')) != self.BOT_ID:
                            continue
                            
                        # Check if this is an upscale result
                        if (message.get('attachments') and 
                            message.get('referenced_message', {}).get('id') == message_id):
                            logging.info("Found upscaled image")
                            return message
                            
                    time.sleep(2)
                    
                except Exception as e:
                    logging.error(f"Error checking upscale progress: {str(e)}")
                    time.sleep(2)
                    
            logging.error(f"Upscale timed out after {timeout} seconds")
            return None
            
        except Exception as e:
            logging.error(f"Error waiting for upscale: {str(e)}")
            return None
            
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an HTTP request with rate limiting and retries"""
        try:
            # Ensure minimum time between requests
            time_since_last = time.time() - self.last_request_time
            if time_since_last < self.min_request_interval:
                time.sleep(self.min_request_interval - time_since_last)
            
            # Add headers if not present
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            
            # Add authorization and common headers
            headers = {
                'Authorization': self.oauth_token,
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Origin': 'https://discord.com',
                'X-Discord-Locale': 'en-US',
                'X-Debug-Options': 'bugReporterEnabled'
            }
            
            # Only add Referer if we have guild_id
            if hasattr(self, 'guild_id'):
                headers['Referer'] = f'https://discord.com/channels/{self.guild_id}/{self.channel_id}'
            else:
                headers['Referer'] = 'https://discord.com/channels/@me'
            
            kwargs['headers'].update(headers)
            
            # Make request with retries
            max_retries = 3
            retry_delay = 1
            
            for attempt in range(max_retries):
                try:
                    response = self.client.request(method, url, **kwargs)
                    
                    # Update last request time
                    self.last_request_time = time.time()
                    
                    # Handle rate limits
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', retry_delay))
                        logging.warning(f"Rate limited, waiting {retry_after} seconds")
                        time.sleep(retry_after)
                        continue
                    
                    return response
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logging.warning(f"Request failed, retrying in {retry_delay} seconds: {str(e)}")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise
                    
            return response
            
        except Exception as e:
            logging.error(f"Error in _make_request: {str(e)}")
            raise

    def _get_cached_message(self, message_id: str) -> Optional[Dict]:
        """Get message from cache if available
        
        This method retrieves a previously cached Discord message. Messages are cached
        during the generation process to avoid unnecessary API calls and potential
        authorization issues.
        
        Args:
            message_id: The Discord message ID to retrieve
            
        Returns:
            The cached message dictionary if found, None otherwise
        """
        if hasattr(self, '_message_cache') and message_id in self._message_cache:
            return self._message_cache[message_id]
        return None

    def _find_message_in_history(self, message_id: str) -> Optional[Dict]:
        """Find a message by scanning recent channel history
        
        This method serves as a fallback when a message is not found in cache.
        It scans the recent channel history (up to 50 messages) to find a specific message.
        
        Args:
            message_id: The Discord message ID to find
            
        Returns:
            The message dictionary if found, None otherwise
        """
        try:
            response = self.client.get(
                f"{self.API_URL}/channels/{self.channel_id}/messages?limit=50",
                headers={
                    'Authorization': self.oauth_token,
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Origin': 'https://discord.com',
                    'Referer': f'https://discord.com/channels/{self.guild_id}/{self.channel_id}',
                    'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
                }
            )
            
            if not response.ok:
                logging.error(f"Failed to get channel history: {response.status_code}")
                return None
            
            messages = response.json()
            for message in messages:
                if message.get('id') == message_id:
                    return message
                
            return None
            
        except Exception as e:
            logging.error(f"Error finding message in history: {str(e)}")
            return None

    def _get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """Get recent messages with proper filtering
        
        CRITICAL: This method implements message filtering logic that prevents
        mixing of different generations and upscales. DO NOT modify the timestamp
        or message matching logic without thorough testing.
        
        Key behaviors:
        1. Only returns messages from current session
        2. For current generation: Returns only the matching message
        3. For new generation: Returns only the most recent message
        4. Breaks after finding relevant message to prevent duplicates
        
        Returns:
            List containing single filtered message that matches criteria
        """
        try:
            response = self.client.get(
                f"{self.API_URL}/channels/{self.channel_id}/messages?limit={limit}",
                headers={
                    'Authorization': self.oauth_token,
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Origin': 'https://discord.com',
                    'Referer': f'https://discord.com/channels/{self.guild_id}/{self.channel_id}'
                }
            )
            
            if not response.ok:
                return []
            
            messages = response.json()
            
            # Filter messages
            filtered_messages = []
            for message in messages:
                # Skip non-Midjourney messages
                if str(message.get('author', {}).get('id')) != self.BOT_ID:
                    continue
                    
                # Calculate message timestamp from snowflake ID
                try:
                    message_id = int(message['id'])
                    timestamp_ms = ((message_id >> 22) + 1420070400000) / 1000
                    
                    # Skip messages from before this session
                    if timestamp_ms < self.session_start_time:
                        logging.debug(f"Skipping old message: {message['id']} from {timestamp_ms} (session started at {self.session_start_time})")
                        continue
                    
                    # Only include messages that match our current generation
                    if self.current_generation_id:
                        if message['id'] == self.current_generation_id:
                            filtered_messages.append(message)
                            break  # Stop after finding our message
                    else:
                        # If no current generation, only get the most recent message
                        filtered_messages = [message]
                        break
                    
                except (ValueError, TypeError) as e:
                    logging.error(f"Error parsing message ID {message.get('id')}: {str(e)}")
                    continue
            
            return filtered_messages
            
        except Exception as e:
            logging.error(f"Error getting recent messages: {str(e)}")
            return []

    def reset_state(self):
        """Reset all client state between generations
        
        CRITICAL: This method ensures clean state between different variations
        by clearing:
        1. current_generation_id - Prevents message ID conflicts
        2. _message_cache - Prevents cached messages from affecting new generations
        3. _generation_lock - Ensures no deadlocks between variations
        
        This method MUST be called:
        - Before starting each new variation
        - After any generation errors
        - When switching between different posts
        
        DO NOT modify this method without thorough testing of:
        - Multiple variations (niji, v6.1)
        - Error recovery
        - Concurrent generations
        """
        self.current_generation_id = None
        self._message_cache = {}
        self._generation_lock = False