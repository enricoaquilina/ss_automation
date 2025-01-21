import asyncio
from instagram_publisher.core.publisher import InstagramCarouselPublisher
import logging

async def main():
    publisher = InstagramCarouselPublisher()
    try:
        # Attempt to publish
        post_id = await publisher.publish_next_carousel()
        if post_id:
            print(f"Successfully published carousel post: {post_id}")
        else:
            print("No post published")
            
    except Exception as e:
        logging.error(f"Error in main: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Fatal error: {e}")