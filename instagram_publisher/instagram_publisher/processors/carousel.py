"""Carousel processing operations"""
from typing import Optional, List, Dict
import asyncio
import httpx
from ..config import settings
import os
import aiofiles
from urllib.parse import quote, urlencode
import random

class CarouselProcessor:
    def __init__(self, publisher):
        self.publisher = publisher
        self.logger = publisher.logger
        self.access_token = publisher.access_token
        self.max_retries = 3
        self.retry_delay = 5

    async def create_carousel_item(self, image_url: str) -> Optional[str]:
        """Create a carousel item from an image URL"""
        try:
            url = f"https://graph.facebook.com/{self.publisher.instagram_config.api_version}/{self.publisher.instagram_config.account_id}/media"
            params = {
                "access_token": self.publisher.access_token,
                "image_url": image_url,
                "is_carousel_item": "true",
                "media_type": "IMAGE"
            }
            
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(url, params=params)
                data = response.json()
                
                if 'error' in data:
                    self.logger.error(f"Instagram API Error: {data['error'].get('message')}")
                    self.logger.error(f"Error Type: {data['error'].get('type')}")
                    self.logger.error(f"Error Code: {data['error'].get('code')}")
                    self.logger.error(f"Error Subcode: {data['error'].get('error_subcode')}")
                    self.logger.error(f"Full API Response: {data}")
                    return None
                    
                if 'id' not in data:
                    self.logger.error(f"Unexpected API response: {data}")
                    return None
                    
                return data['id']
                
        except Exception as e:
            self.logger.error(f"Error creating carousel item: {str(e)}")
            self.logger.exception(e)
            return None

    async def try_create_carousel_item_with_retries(self, image_url: str) -> Optional[str]:
        """Try to create a carousel item with retries"""
        for attempt in range(1, self.max_retries + 1):
            result = await self.create_carousel_item(image_url)
            if result:
                return result
            if attempt < self.max_retries:
                self.logger.info(f"Retrying in {self.retry_delay} seconds...")
                await asyncio.sleep(self.retry_delay)
        return None

    async def create_carousel_container(self, item_ids: List[str], caption: str) -> Optional[str]:
        """Create a carousel container from multiple item IDs"""
        if not item_ids:
            self.logger.error("No valid carousel items to create container")
            return None

        try:
            url = f"{settings.BASE_URL}/{self.publisher.instagram_config.account_id}/media"
            
            params = {
                'access_token': self.access_token,
                'media_type': 'CAROUSEL',
                'children': ','.join(item_ids),
                'caption': caption
            }

            self.logger.debug(f"Creating carousel container with {len(item_ids)} items")
            self.logger.debug(f"Container params: {params}")

            async with httpx.AsyncClient() as client:
                response = await client.post(url, params=params)
                data = response.json()

                if 'id' in data:
                    self.logger.info(f"Successfully created carousel container with ID: {data['id']}")
                    return data['id']
                else:
                    self.logger.error(f"Failed to create carousel container. Response: {data}")
                    return None

        except Exception as e:
            self.logger.error(f"Exception creating carousel container: {str(e)}", exc_info=True)
            return None

    async def publish_container(self, container_id: str) -> Optional[Dict]:
        """Publish the carousel container"""
        try:
            url = f"{settings.BASE_URL}/{self.publisher.instagram_config.account_id}/media_publish"
            params = {
                "access_token": self.access_token,
                "creation_id": container_id
            }
            
            self.logger.info(f"Publishing container with ID: {container_id}")
            self.logger.debug(f"Publish params: {params}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, params=params)
                self.logger.debug(f"Publish response status: {response.status_code}")
                self.logger.debug(f"Publish response: {response.text}")
                
                try:
                    data = response.json()
                except ValueError:
                    self.logger.error(f"Invalid JSON response: {response.text}")
                    return None
                
                if response.status_code != 200 or 'error' in data:
                    error_message = data.get('error', {}).get('message', response.text) if 'error' in data else response.text
                    self.logger.error(f"Error publishing container: {error_message}")
                    return None
                    
                self.logger.info(f"Successfully published container: {data}")
                return data
                
        except Exception as e:
            self.logger.error(f"Error publishing container: {str(e)}", exc_info=True)
            return None 

    async def test_image_url(self, image_url: str) -> bool:
        """Test if an image URL is accessible"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.head(image_url, timeout=10.0)
                self.logger.info(f"URL Test: {image_url}")
                self.logger.info(f"Status: {response.status_code}")
                self.logger.info(f"Headers: {dict(response.headers)}")
                return response.status_code == 200 and response.headers.get('content-type', '').startswith('image/')
        except Exception as e:
            self.logger.error(f"URL test failed: {str(e)}")
            return False 

    async def test_image_accessibility(self, image_path: str) -> bool:
        """Test if an image is accessible via URL"""
        filename = os.path.basename(image_path)
        encoded_filename = quote(filename)
        image_url = f"{settings.IMAGE_HOST}/{encoded_filename}"
        
        self.logger.info(f"Testing image accessibility: {image_url}")
        
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            try:
                # Try HEAD request first
                head_response = await client.head(image_url)
                self.logger.info(f"HEAD Status: {head_response.status_code}")
                self.logger.info(f"HEAD Headers: {dict(head_response.headers)}")
                
                # Try GET request to verify content
                get_response = await client.get(image_url)
                self.logger.info(f"GET Status: {get_response.status_code}")
                self.logger.info(f"GET Content-Type: {get_response.headers.get('content-type')}")
                self.logger.info(f"GET Content-Length: {get_response.headers.get('content-length')}")
                
                return (get_response.status_code == 200 and 
                       get_response.headers.get('content-type', '').startswith('image/'))
            except Exception as e:
                self.logger.error(f"Image accessibility test failed: {str(e)}")
                return False 