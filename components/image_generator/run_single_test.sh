#!/bin/bash
# Run a single Midjourney test with a specific prompt

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Display header
echo -e "\n${BLUE}=== Midjourney Single Test Runner ===${NC}"

# Define safe test prompts that are less likely to trigger moderation
SAFE_PROMPTS=(
    "beautiful cosmic space dolphin, digital art style"
    "colorful abstract landscape with mountains, watercolor style"
    "futuristic city skyline with flying cars, cyberpunk style"
    "magical forest with glowing mushrooms, fantasy art style"
    "serene ocean sunset with sailboats, impressionist painting style"
)

# Check if a prompt was provided
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}No prompt provided. Please select from these safe options:${NC}"
    for i in "${!SAFE_PROMPTS[@]}"; do
        echo -e "  ${i}: ${SAFE_PROMPTS[$i]}"
    done
    
    read -p "Enter your choice [0-$((${#SAFE_PROMPTS[@]}-1))]: " choice
    if [[ ! "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -ge "${#SAFE_PROMPTS[@]}" ]; then
        echo -e "${RED}Invalid choice. Using default prompt.${NC}"
        PROMPT="${SAFE_PROMPTS[0]}"
    else
        PROMPT="${SAFE_PROMPTS[$choice]}"
    fi
else
    # Use the provided prompt
    PROMPT="$1"
    echo -e "${YELLOW}Using provided prompt: ${PROMPT}${NC}"
fi

# Check for available .env files
ENV_FILES=(
    ".env"
    "src/.env"
    ".env-files/.env"
    "../.env"  # Check parent directory too
)

ENV_FOUND=false

for env_file in "${ENV_FILES[@]}"; do
    if [ -f "$env_file" ]; then
        echo -e "${GREEN}✓ Found environment file: ${YELLOW}${env_file}${NC}"
        
        # Export all variables from .env file
        export $(grep -v '^#' "$env_file" | xargs)
        ENV_FOUND=true
        break
    fi
done

if [ "$ENV_FOUND" = false ]; then
    echo -e "${RED}✗ No environment files found${NC}"
    echo -e "${YELLOW}Please create an .env file with Discord credentials${NC}"
    echo -e "${YELLOW}You can run ./run_discord_tests.sh to create a template${NC}"
    exit 1
fi

# Validate Discord token
echo -e "\n${BLUE}=== Validating Discord Token ===${NC}"
cd tests
python -m integration.test_discord_auth

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Discord token validation failed.${NC}"
    echo -e "${YELLOW}Please check your token in the .env file and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Discord token validated successfully!${NC}"

# Display warning and confirmation
echo -e "\n${RED}WARNING: This will use a real Midjourney API call and consume credits${NC}"
echo -e "${BLUE}Prompt: ${YELLOW}${PROMPT}${NC}"
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Test cancelled."
    exit 0
fi

# Set environment for live test
export FULLY_MOCKED=false
export LIVE_TEST=true
export TEST_PROMPT="$PROMPT"

# Create a timestamp for output directory
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
export TEST_OUTPUT_DIR="test_output/${TIMESTAMP}"
mkdir -p "$TEST_OUTPUT_DIR"

echo -e "\n${BLUE}=== Running Single Midjourney Test ===${NC}"
echo -e "${YELLOW}Prompt: ${PROMPT}${NC}"
echo -e "${YELLOW}Output directory: ${TEST_OUTPUT_DIR}${NC}"

# Create the test script
TEST_SCRIPT="$TEST_OUTPUT_DIR/single_test.py"

cat > "$TEST_SCRIPT" << EOF
#!/usr/bin/env python3
"""
Single Midjourney test with custom prompt
Generated on: ${TIMESTAMP}
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join("${TEST_OUTPUT_DIR}", "test.log"))
    ]
)
logger = logging.getLogger("single_test")

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.abspath(os.path.join(current_dir, ".."))
src_dir = os.path.abspath(os.path.join(tests_dir, "..", "src"))

for path in [tests_dir, src_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import necessary components
try:
    from src.client import MidjourneyClient
    logger.info("Successfully imported MidjourneyClient")
except ImportError as e:
    logger.error(f"Failed to import MidjourneyClient: {e}")
    try:
        import importlib.util
        client_path = os.path.join(src_dir, "client.py")
        spec = importlib.util.spec_from_file_location("client", client_path)
        client_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client_module)
        MidjourneyClient = client_module.MidjourneyClient
        logger.info("Imported MidjourneyClient using importlib")
    except Exception as e2:
        logger.error(f"Alternative import also failed: {e2}")
        sys.exit(1)

async def run_test():
    """Run the test"""
    # Get credentials from environment
    user_token = os.environ.get("DISCORD_USER_TOKEN")
    bot_token = os.environ.get("DISCORD_BOT_TOKEN", user_token)
    channel_id = os.environ.get("DISCORD_CHANNEL_ID")
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    prompt = os.environ.get("TEST_PROMPT", "${PROMPT}")
    
    logger.info(f"Running test with prompt: {prompt}")
    
    # Initialize client
    client = MidjourneyClient(
        user_token=user_token,
        bot_token=bot_token,
        channel_id=channel_id,
        guild_id=guild_id
    )
    
    try:
        # Initialize the client
        logger.info("Initializing client...")
        init_success = await client.initialize()
        if not init_success:
            logger.error("Failed to initialize client")
            return False
            
        logger.info("Client initialized successfully")
        
        # Generate image
        logger.info(f"Generating image with prompt: {prompt}")
        result = await client.generate_image(prompt)
        
        if not result.success:
            logger.error(f"Generation failed: {result.error}")
            return False
            
        logger.info(f"Generation successful! Grid message ID: {result.grid_message_id}")
        logger.info(f"Image URL: {result.image_url}")
        
        # Wait for grid image to be processed
        logger.info("Waiting 30 seconds for grid image processing...")
        await asyncio.sleep(30)
        
        # Get upscales
        logger.info("Upscaling all variants...")
        upscale_results = await client.upscale_all_variants(result.grid_message_id)
        
        # Log upscale results
        for upscale in upscale_results:
            if upscale.success:
                logger.info(f"Upscale variant {upscale.variant} successful: {upscale.image_url}")
            else:
                logger.error(f"Upscale variant {upscale.variant} failed: {upscale.error}")
        
        # Save results to file
        with open(os.path.join("${TEST_OUTPUT_DIR}", "results.txt"), "w") as f:
            f.write(f"Prompt: {prompt}\\n")
            f.write(f"Grid message ID: {result.grid_message_id}\\n")
            f.write(f"Grid image URL: {result.image_url}\\n\\n")
            f.write("Upscale Results:\\n")
            for upscale in upscale_results:
                f.write(f"Variant {upscale.variant}: {'Success' if upscale.success else 'Failed'}\\n")
                if upscale.success:
                    f.write(f"  URL: {upscale.image_url}\\n")
                else:
                    f.write(f"  Error: {upscale.error}\\n")
        
        logger.info(f"Results saved to ${TEST_OUTPUT_DIR}/results.txt")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        return False
    finally:
        # Close the client
        logger.info("Closing client...")
        await client.close()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    success = loop.run_until_complete(run_test())
    sys.exit(0 if success else 1)
EOF

# Make the test script executable
chmod +x "$TEST_SCRIPT"

# Run the test
echo -e "\n${BLUE}=== Executing Test ===${NC}"
python "$TEST_SCRIPT"

# Check if test was successful
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ Test completed successfully!${NC}"
    echo -e "${YELLOW}Results saved to: ${TEST_OUTPUT_DIR}/results.txt${NC}"
else
    echo -e "\n${RED}✗ Test failed. Check logs for details.${NC}"
    echo -e "${YELLOW}Logs saved to: ${TEST_OUTPUT_DIR}/test.log${NC}"
fi 