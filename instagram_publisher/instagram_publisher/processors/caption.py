"""Caption generation using AI models"""
import base64
import os
import logging
from typing import Optional
from ..config import settings
import replicate

class CaptionGenerator:
    def __init__(self, publisher):
        self.publisher = publisher
        self.logger = logging.getLogger(__name__)

    def _get_fallback_caption(self, prompt: str) -> str:
        """Get a fallback caption if generation fails"""
        return f"AI Generated Art\n\nPrompt: {prompt}"

    async def generate_caption(self, image_path: str, prompt: str) -> str:
        """Generate caption using both Vision and LLM models"""
        try:
            # First, get image description using Vision model
            with open(image_path, "rb") as image_file:
                base64_string = base64.b64encode(image_file.read()).decode()

            vision_output = replicate.run(
                "hayooucom/vision-model:6afc892d5aa00e0e0883dec30f7a766fcf515c64090def9d173093ac343c2438",
                input={
                    "top_k": 1,
                    "top_p": 1,
                    "prompt": "Describe the composition, mood, and visual elements of this image in detail.",
                    "image_url": [],
                    "max_tokens": 45000,
                    "temperature": 0.1,
                    "image_base64": [base64_string],
                    "system_prompt": "You are a detail-oriented art critic with expertise in visual analysis.",
                    "max_new_tokens": 458,
                    "repetition_penalty": 1.1
                }
            )
            
            image_description = "".join(vision_output).strip()
            self.logger.info(f"Generated image description: {image_description[:100]}...")

            # Then, use Llama to generate the caption based on the description
            caption_output = replicate.run(
                "meta/meta-llama-3.1-405b-instruct",
                input={
                    "prompt": f"""Given this detailed image description: "{image_description}"

                    Create an Instagram caption with exactly two parts:

                    1. First part: Write a vague, intriguing description that captures the essence without revealing too much (max 15 words)
                    2. Second part: Add a deeper, philosophical reflection that connects to universal human experiences (max 20 words)

                    Requirements:
                    - Separate the two parts with a single line break
                    - Add exactly one relevant emoji at the start of each part
                    - Use evocative, emotional language that sparks curiosity
                    - Avoid technical terms or explicit AI references
                    - Make it feel authentic and personal
                    - Focus on emotions, metaphors, and abstract concepts

                    Original prompt for context: "{prompt}" """,
                    "temperature": 0.75,
                    "top_p": 0.95,
                    "max_tokens": 200,
                    "system_prompt": "You are an insightful artist who sees deeper meaning in visual art and connects it to human experiences."
                }
            )
            
            caption = "".join(caption_output).strip()
            
            # Add engagement text from settings and hashtags
            return f"{caption}\n\n{settings.ENGAGEMENT_TEXT}\n\n{self.publisher.generate_hashtags()}"

        except Exception as e:
            self.logger.error(f"Error generating caption: {e}")
            return self._get_fallback_caption(prompt)