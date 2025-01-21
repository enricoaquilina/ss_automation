# Image Generator

A Python package for generating images using various AI providers including Midjourney, Flux, and Leonardo.

## Features

- Support for multiple AI image generation providers
- Consistent interface across different providers
- Image compression and optimization
- MongoDB integration for storing generated images
- Retry mechanisms and error handling
- Prompt optimization and reformatting

## Installation

```bash
pip install -e .
```

## Configuration

Create a `.env` file in your project root with the following variables:

```env
# MongoDB
MONGODB_URI=mongodb://user:pass@localhost:27017/instagram_db?authSource=admin

# Midjourney (Discord)
DISCORD_CHANNEL_ID=your_channel_id
DISCORD_USER_TOKEN=your_user_token

# Other providers will be added here
```

## Usage

```python
from image_generator.providers.midjourney import MidjourneyClient
from image_generator.core.database import get_database

# Initialize clients
db = get_database()
client = MidjourneyClient()

# Generate images
result = client.generate("A beautiful sunset over mountains")

# Process and store results
# See scripts/generate.py for full example
```

## Scripts

- `scripts/generate.py`: Generate new images
- `scripts/reprocess.py`: Reprocess existing images with new variations

## Development

To add a new provider:

1. Create a new directory under `providers/`
2. Implement the provider interface (see `providers/base.py`)
3. Add provider-specific utilities and helpers
4. Update the main generation scripts to support the new provider 