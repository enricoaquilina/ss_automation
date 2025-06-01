# API Reference

This document provides a comprehensive reference for the Discord-Midjourney image generator API, covering all public classes and methods.

## Table of Contents

- [MidjourneyClient](#midjourneyclient)
- [DiscordGateway](#discordgateway)
- [Storage Classes](#storage-classes)
- [Data Classes](#data-classes)
- [Helper Functions](#helper-functions)

## MidjourneyClient

The main client class that handles interactions with Midjourney through Discord.

### Constructor

```python
MidjourneyClient(
    user_token: str,
    bot_token: str,
    channel_id: str,
    guild_id: str
)
```

Parameters:
- `user_token` (str): Discord user token for sending commands and interactions
- `bot_token` (str): Discord bot token for monitoring messages and WebSocket events
- `channel_id` (str): ID of the Discord channel where Midjourney is active
- `guild_id` (str): ID of the Discord guild/server

### Methods

#### `async initialize() -> bool`

Initializes connections to Discord WebSocket gateways.

Returns:
- `bool`: True if initialization was successful, False otherwise

Example:
```python
client = MidjourneyClient(user_token, bot_token, channel_id, guild_id)
success = await client.initialize()
```

#### `async generate_image(prompt: str) -> GenerationResult`

Generates an image using Midjourney's `/imagine` command.

Parameters:
- `prompt` (str): The prompt to send to Midjourney

Returns:
- `GenerationResult`: Object containing the result of the generation

Example:
```python
result = await client.generate_image("sunset over mountains, watercolor style")
if result.success:
    print(f"Generated image: {result.image_url}")
```

#### `async upscale_all_variants(grid_message_id: str) -> List[UpscaleResult]`

Upscales all four variants from a grid with improved reliability.

Parameters:
- `grid_message_id` (str): The message ID of the grid to upscale

Returns:
- `List[UpscaleResult]`: List of upscale results for each variant

Example:
```python
upscale_results = await client.upscale_all_variants(grid_message_id)
for result in upscale_results:
    if result.success:
        print(f"Upscaled variant {result.variant}: {result.image_url}")
    else:
        print(f"Failed to upscale variant {result.variant}: {result.error}")
```

#### `async close()`

Closes all connections.

Example:
```python
await client.close()
```

## DiscordGateway

Handles Discord gateway connections and event handling.

### Constructor

```python
DiscordGateway(
    token: str,
    is_bot: bool = False,
    intents: int = 513
)
```

Parameters:
- `token` (str): Discord token (user or bot)
- `is_bot` (bool, optional): Whether the token is a bot token. Defaults to False.
- `intents` (int, optional): Gateway intents. Defaults to 513.

### Methods

#### `async connect() -> bool`

Connects to the Discord Gateway.

Returns:
- `bool`: True if connection was successful, False otherwise

#### `register_handler(handler)`

Registers a message handler function.

Parameters:
- `handler` (callable): Function that takes a gateway message and returns a boolean

#### `unregister_handler(handler)`

Unregisters a message handler function.

Parameters:
- `handler` (callable): Previously registered handler function

#### `async close()`

Closes the connection and cleans up tasks.

## Storage Classes

### FileSystemStorage

File system storage backend for Midjourney images.

#### Constructor

```python
FileSystemStorage(base_dir: str = "midjourney_output")
```

Parameters:
- `base_dir` (str): Base directory for storing images and metadata

#### Methods

##### `async save_grid(data: bytes, metadata: Dict[str, Any]) -> str`

Saves grid image data to filesystem.

Parameters:
- `data` (bytes): Binary image data
- `metadata` (Dict[str, Any]): Image metadata

Returns:
- `str`: Path to the saved image

##### `async save_upscale(data: bytes, metadata: Dict[str, Any]) -> str`

Saves upscale image data to filesystem.

Parameters:
- `data` (bytes): Binary image data
- `metadata` (Dict[str, Any]): Image metadata

Returns:
- `str`: Path to the saved image

### GridFSStorage

MongoDB GridFS storage backend for Midjourney images.

#### Constructor

```python
GridFSStorage(
    mongodb_uri: str = None, 
    db_name: str = "silicon_sentiments",
    post_id: Optional[str] = None
)
```

Parameters:
- `mongodb_uri` (str): MongoDB connection URI (optional if set in environment variables)
- `db_name` (str): MongoDB database name
- `post_id` (Optional[str]): Optional post ID to associate with images

## Data Classes

### GenerationResult

Holds the result of an image generation.

Attributes:
- `success` (bool): Whether the generation was successful
- `grid_message_id` (Optional[str]): The message ID of the grid, if successful
- `image_url` (Optional[str]): URL of the generated grid image, if successful
- `error` (Optional[str]): Error message, if generation failed

### UpscaleResult

Holds the result of an upscale operation.

Attributes:
- `success` (bool): Whether the upscale was successful
- `variant` (int): The variant number (1-4)
- `image_url` (Optional[str]): URL of the upscaled image, if successful
- `error` (Optional[str]): Error message, if upscale failed

## Helper Functions

### `async save_image(url: str, file_path: str)`

Downloads and saves an image from a URL.

Parameters:
- `url` (str): URL of the image to download
- `file_path` (str): Local path where image should be saved

Example:
```python
await save_image("https://cdn.discordapp.com/attachments/...", "output.png")
```

## Internal Methods

These methods are primarily for internal use but may be useful for advanced customization:

- `_send_imagine_command(prompt: str) -> bool`: Sends the /imagine command
- `_send_button_interaction(message_id: str, custom_id: str) -> bool`: Sends button interactions
- `_extract_button_custom_id(message_data: Dict, button_index: int) -> Optional[str]`: Extracts button custom IDs
- `_get_message_details(message_id: str) -> Optional[Dict]`: Gets message details from Discord API 