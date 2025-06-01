#!/bin/bash
# Run Discord integration tests with proper environment setup

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

echo -e "${BLUE}=== Discord Integration Test Runner ===${NC}"

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
        
        # Display token status (first/last 5 chars)
        if [ -n "$DISCORD_USER_TOKEN" ]; then
            TOKEN_LENGTH=${#DISCORD_USER_TOKEN}
            TOKEN_START=${DISCORD_USER_TOKEN:0:5}
            TOKEN_END=${DISCORD_USER_TOKEN: -5}
            echo -e "${GREEN}✓ DISCORD_USER_TOKEN found ${NC}(${TOKEN_LENGTH} chars: ${TOKEN_START}...${TOKEN_END})"
        else
            echo -e "${RED}✗ DISCORD_USER_TOKEN not found in ${env_file}${NC}"
        fi
        
        # Check other critical variables
        if [ -n "$DISCORD_CHANNEL_ID" ]; then
            echo -e "${GREEN}✓ DISCORD_CHANNEL_ID found: ${YELLOW}${DISCORD_CHANNEL_ID}${NC}"
        else
            echo -e "${RED}✗ DISCORD_CHANNEL_ID not found in ${env_file}${NC}"
        fi
        
        if [ -n "$DISCORD_GUILD_ID" ]; then
            echo -e "${GREEN}✓ DISCORD_GUILD_ID found: ${YELLOW}${DISCORD_GUILD_ID}${NC}"
        else
            echo -e "${RED}✗ DISCORD_GUILD_ID not found in ${env_file}${NC}"
        fi
        
        break
    fi
done

if [ "$ENV_FOUND" = false ]; then
    echo -e "${RED}✗ No environment files found${NC}"
    echo -e "${YELLOW}Creating a default .env file template...${NC}"
    
    cat > .env << EOF
# Discord credentials
DISCORD_CHANNEL_ID=your_channel_id
DISCORD_GUILD_ID=your_guild_id
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_USER_TOKEN=your_user_token

# MongoDB connection (only needed if using GridFS storage)
MONGODB_URI=mongodb://username:password@hostname:port/database?authSource=admin

# Logging settings
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Test settings (only needed for tests)
TEST_PROMPT="beautiful cosmic space dolphin, digital art style"
TEST_POST_ID=your_test_post_id
EOF
    
    echo -e "${YELLOW}Created .env template. Please edit it with your credentials.${NC}"
    exit 1
fi

# Validate Discord token by running the auth test
echo -e "\n${BLUE}=== Validating Discord Token ===${NC}"
cd tests
python -m integration.test_discord_auth

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Discord token validation failed.${NC}"
    echo -e "${YELLOW}Please check your token in the .env file and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Discord token validated successfully!${NC}"

# Ask if user wants to run actual tests
echo -e "\n${BLUE}=== Discord Integration Tests ===${NC}"
echo -e "${YELLOW}The following tests will be run:${NC}"
echo -e "1. Discord Authentication Test"
echo -e "2. Upscale Correlation Test"
echo -e "3. Midjourney Live Workflow Test (uses credits)"

read -p "Do you want to run these tests? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Tests cancelled.${NC}"
    exit 0
fi

# Set environment for live tests
export FULLY_MOCKED=false
export LIVE_TEST=true

# Run the tests
echo -e "\n${BLUE}=== Running Discord Integration Tests ===${NC}"

echo -e "\n${YELLOW}• Discord Authentication Test${NC}"
python -m pytest integration/test_discord_auth.py -v

echo -e "\n${YELLOW}• Upscale Correlation Test${NC}"
python -m pytest integration/test_upscale_correlation.py -v --asyncio-mode=strict

echo -e "\n${YELLOW}• Midjourney Live Workflow Test${NC}"
python -m pytest integration/test_midjourney_live_workflow.py -v

# Print test summary
echo -e "\n${BLUE}=== Test Run Complete ===${NC}"

# Return status of the last command
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}All tests passed successfully!${NC}"
else
    echo -e "${RED}Some tests failed. Please check the output above for details.${NC}"
fi

exit $exit_code 