# Discord-Midjourney Image Generator Documentation

This documentation covers the Discord-Midjourney image generator component, which provides a robust interface to generate and upscale images using Discord and Midjourney.

## Documentation Structure

- **[API Reference](api/README.md)**: Detailed class and method documentation
- **[Testing Guide](testing/README.md)**: How to run tests and test the component
- **[Troubleshooting](troubleshooting/README.md)**: Common issues and solutions

## Key Features

- **Hybrid Token Approach**: Uses user token for commands and interactions, bot token for WebSocket events
- **Reliable Image Detection**: Multiple fallback strategies ensure detection of generated images
- **Complete Workflow**: From prompt submission to upscaling all variants
- **Error Handling**: Comprehensive error detection and recovery
- **Model Support**: Uses Midjourney v7.0 and niji 6 by default

## Quick Start

```python
import asyncio
from components.image_generator.src import MidjourneyClient, FileSystemStorage

async def generate_and_upscale():
    client = MidjourneyClient(
        user_token="YOUR_USER_TOKEN",
        bot_token="YOUR_BOT_TOKEN",
        channel_id="YOUR_CHANNEL_ID",
        guild_id="YOUR_GUILD_ID"
    )
    
    # Initialize client
    await client.initialize()
    
    # Generate image
    generation = await client.generate_image("beautiful sunset over mountains, watercolor style")
    
    if generation.success:
        # Upscale all variants
        upscales = await client.upscale_all_variants(generation.grid_message_id)
        
        # Print results
        for result in upscales:
            print(f"Variant {result.variant}: {'Success' if result.success else 'Failed'}")
    
    # Close client
    await client.close()

# Run the example
asyncio.run(generate_and_upscale())
```

## Environment Setup

Create a `.env` file in one of the following locations:
- `./.env` (in the root directory)
- `./components/image_generator/.env`
- `./components/image_generator/src/.env`

With the following variables:

```
DISCORD_CHANNEL_ID=your_channel_id
DISCORD_GUILD_ID=your_guild_id
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_USER_TOKEN=your_user_token
MONGODB_URI=your_mongodb_uri  # Only needed if using GridFS storage
```

## Command Line Usage

The simplest way to use the component is through the `generate.py` script:

```bash
python components/image_generator/generate.py --prompt "beautiful sunset over mountains, watercolor style"
```

See the main [README.md](../README.md) in the component root directory for more detailed usage instructions. 