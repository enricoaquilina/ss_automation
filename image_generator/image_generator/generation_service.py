import logging
import time

class GenerationService:
    def __init__(self, client: MidjourneyClient):
        """Initialize the generation service
        
        CRITICAL: This service manages the generation state and message tracking
        across multiple variations.
        """
        self.client = client
        # Initialize dict for tracking processed messages per variation
        self._processed_messages = {}

    def _process_variation(self, prompt: str, variation: str, seed: int):
        """Process a single variation
        
        CRITICAL: This method handles the generation and upscaling sequence.
        Each variation must have its own unique message ID and state.
        
        Key behaviors:
        1. Resets client state completely before each variation
        2. Resets message tracking for each variation
        3. Waits before starting new variations
        4. Tracks message IDs per variation
        
        Supported variations:
        - niji: Uses --niji parameter
        - v6.1: Uses --v 6.1 parameter
        - v6.0: Uses --v 6.0 parameter
        
        IMPORTANT: When adding new variations:
        1. Add the variation type here in the documentation
        2. Add corresponding handling in the options dictionary below
        3. Add corresponding handling in MidjourneyClient.generate()
        
        DO NOT modify the state management or timing without testing:
        - Multiple variations in sequence
        - Error recovery between variations
        - Message ID handling
        """
        try:
            # Reset client state completely
            self.client.reset_state()
            
            # Reset tracking for this variation
            self._processed_messages[variation] = set()  # Clear previous messages
            
            # Generate the image
            options = {
                'seed': seed,
                'ar': '4:5',
                'q': 1
            }
            
            if variation == 'niji':
                options['niji'] = True
            elif variation == 'v6.1':
                options['v'] = '6.1'
            elif variation == 'v6.0':
                options['v'] = '6.0'
            
            # Wait before starting new variation
            logging.info("Waiting before starting new variation...")
            time.sleep(10)
            
            result = self.client.generate(prompt, options)
            message_id = result['id']
            
            logging.info(f"Generated initial image with message ID: {message_id} for variation {variation}")
            
            # Track this message ID for this specific variation
            self._processed_messages[variation].add(message_id)
            
            # Wait for initial generation to complete
            logging.info("Waiting for initial generation to complete...")
            time.sleep(30)  # Give Discord time to fully process
            
            # Process upscales
            for i in range(4):
                upscale_index = i + 1
                logging.info(f"Processing upscale {upscale_index} of 4 for message {message_id} ({variation})")
                
                try:
                    self._process_upscale(message_id, upscale_index, variation)
                except Exception as e:
                    logging.error(f"Failed to process upscale {upscale_index}: {str(e)}")
                    raise
                
            logging.info(f"Successfully processed all upscales for {variation}")
            
        except Exception as e:
            logging.error(f"Error processing variation: {str(e)}")
            raise 