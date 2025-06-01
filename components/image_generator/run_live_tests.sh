#!/bin/bash
# Run all live tests for the image_generator component with proper environment setup

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
echo -e "\n${BLUE}=== Midjourney Live Test Runner ===${NC}"
echo -e "${YELLOW}This script will run live tests that use real Midjourney API calls${NC}"

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

# Display initial warning and confirmation
echo -e "\n${RED}WARNING: This will use real Midjourney API calls and consume credits${NC}"
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Tests cancelled."
    exit 0
fi

# Set environment for live tests
export FULLY_MOCKED=false
export LIVE_TEST=true

# Run all tests
echo -e "\n${BLUE}=== Running Live Tests ===${NC}"
cd tests
./run_all_tests.sh 9 --no-confirm

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