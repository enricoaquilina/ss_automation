#!/bin/bash
# Check for environment files and provide information

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

echo -e "${BLUE}=== Checking Environment Files ===${NC}"

# Check for environment files in various locations
ENV_FILES=(
    ".env"
    "src/.env"
    ".env-files/.env"
)

ENV_FOUND=false

for env_file in "${ENV_FILES[@]}"; do
    if [ -f "$env_file" ]; then
        echo -e "${GREEN}✓ Found environment file: ${YELLOW}${env_file}${NC}"
        ENV_FOUND=true
        
        # Count how many variables are defined in the file
        VAR_COUNT=$(grep -v '^#' "$env_file" | grep -v '^$' | wc -l)
        echo -e "  ${BLUE}Contains ${VAR_COUNT} defined variables${NC}"
        
        # Check for critical variables
        if grep -q "DISCORD_USER_TOKEN" "$env_file"; then
            echo -e "  ${GREEN}✓ Contains DISCORD_USER_TOKEN${NC}"
        else
            echo -e "  ${RED}✗ Missing DISCORD_USER_TOKEN${NC}"
        fi
        
        if grep -q "DISCORD_BOT_TOKEN" "$env_file"; then
            echo -e "  ${GREEN}✓ Contains DISCORD_BOT_TOKEN${NC}"
        else
            echo -e "  ${RED}✗ Missing DISCORD_BOT_TOKEN${NC}"
        fi
        
        if grep -q "DISCORD_CHANNEL_ID" "$env_file"; then
            echo -e "  ${GREEN}✓ Contains DISCORD_CHANNEL_ID${NC}"
        else
            echo -e "  ${RED}✗ Missing DISCORD_CHANNEL_ID${NC}"
        fi
        
        if grep -q "DISCORD_GUILD_ID" "$env_file"; then
            echo -e "  ${GREEN}✓ Contains DISCORD_GUILD_ID${NC}"
        else
            echo -e "  ${RED}✗ Missing DISCORD_GUILD_ID${NC}"
        fi
    fi
done

# Check for the sample env file
if [ -f "env.sample" ]; then
    echo -e "\n${BLUE}Found env.sample file${NC}"
    echo -e "${YELLOW}You can create a .env file based on this template${NC}"
    echo -e "Required variables:"
    grep -v '^#' "env.sample" | grep -v '^$'
fi

if [ "$ENV_FOUND" = false ]; then
    echo -e "${RED}✗ No environment files found${NC}"
    echo -e "${YELLOW}You need to create one of the following files:${NC}"
    for env_file in "${ENV_FILES[@]}"; do
        echo -e "  - ${env_file}"
    done
    
    if [ -f "env.sample" ]; then
        echo -e "\n${YELLOW}Use this command to create an environment file:${NC}"
        echo -e "  cp env.sample .env"
        echo -e "  ${YELLOW}Then edit .env to add your Discord credentials${NC}"
    fi
fi

echo -e "\n${BLUE}=== Running in Discord ===${NC}"
echo -e "${YELLOW}When running live tests, the following will happen:${NC}"
echo -e "1. The bot will connect to Discord using your credentials"
echo -e "2. Images will be generated in the specified Discord channel"
echo -e "3. You will see the generations in the Midjourney UI"
echo -e "4. This will consume Midjourney credits"

echo -e "\n${BLUE}=== Available Test Commands ===${NC}"
echo -e "${YELLOW}• Run all tests in mock mode:${NC}"
echo -e "  ./tests/run_all_tests.sh 1"
echo -e "${YELLOW}• Run single test with prompt:${NC}"
echo -e "  ./run_real_single_test.sh \"your prompt here\""
echo -e "${YELLOW}• Run all live tests (uses credits):${NC}"
echo -e "  ./run_live_tests.sh" 