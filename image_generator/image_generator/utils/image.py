from io import BytesIO
from PIL import Image
import requests
from typing import Union, Optional

def compress_image(image_data: Union[bytes, BytesIO], quality: int = 85) -> bytes:
    """Compress an image using PIL
    
    Args:
        image_data: Raw image data or BytesIO object
        quality: JPEG compression quality (1-100)
        
    Returns:
        Compressed image data as bytes
    """
    if isinstance(image_data, bytes):
        image_data = BytesIO(image_data)
        
    image = Image.open(image_data)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()

def download_image(url: str, timeout: int = 30) -> Optional[bytes]:
    """Download an image from a URL
    
    Args:
        url: Image URL to download
        timeout: Request timeout in seconds
        
    Returns:
        Raw image data as bytes or None if download failed
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error downloading image from {url}: {str(e)}")
        return None

def upscale_image(image_data: Union[bytes, BytesIO], target_size: tuple = (1024, 1024), resample=Image.Resampling.LANCZOS) -> bytes:
    """Upscale an image to a target size using high-quality resampling
    
    Args:
        image_data: Raw image data or BytesIO object
        target_size: Desired (width, height) tuple
        resample: PIL resampling filter (default: Lanczos for best quality)
        
    Returns:
        Upscaled image data as bytes
    """
    if isinstance(image_data, bytes):
        image_data = BytesIO(image_data)
        
    image = Image.open(image_data)
    
    # Only upscale if image is smaller than target size
    current_size = image.size
    if current_size[0] < target_size[0] or current_size[1] < target_size[1]:
        # Calculate aspect ratio preserving dimensions
        ratio = min(target_size[0] / current_size[0], target_size[1] / current_size[1])
        new_size = tuple(int(dim * ratio) for dim in current_size)
        image = image.resize(new_size, resample=resample)
    
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)  # Use high quality for upscaled images
    return buffer.getvalue()

def process_image(url: str, quality: int = 85, upscale: bool = False, target_size: tuple = None) -> Optional[bytes]:
    """Download and process an image in one step
    
    Args:
        url: Image URL to process
        quality: JPEG compression quality
        upscale: Whether to upscale the image
        target_size: Target size for upscaling (width, height)
        
    Returns:
        Processed image data as bytes or None if processing failed
    """
    image_data = download_image(url)
    if not image_data:
        return None
        
    if upscale and target_size:
        image_data = upscale_image(image_data, target_size)
        
    return compress_image(image_data, quality) 