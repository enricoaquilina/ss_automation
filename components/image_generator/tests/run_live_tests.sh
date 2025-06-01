#!/bin/bash
# Run all live tests for the image_generator component without second confirmation

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Set up environment
export PYTHONPATH="$PYTHONPATH:$(pwd)/.."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Display initial warning
echo -e "\n${RED}WARNING: This will use real Midjourney API calls and consume credits${NC}"
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Tests cancelled."
    exit 0
fi

# Configure environment for live tests
export FULLY_MOCKED=false
export LIVE_TEST=true

# Run live tests
echo -e "\n${BLUE}=== Running Live Tests ===${NC}"

# Run midjourney live workflow tests
echo -e "\n${BLUE}=== Running Live Workflow Tests ===${NC}"
python -m pytest integration/test_midjourney_live_workflow.py -v

# Run midjourney integration tests
echo -e "\n${BLUE}=== Running Midjourney Integration Tests ===${NC}"
python -m pytest integration/test_midjourney_integration.py -v

# Run upscale correlation tests
echo -e "\n${BLUE}=== Running Live Upscale Correlation Tests ===${NC}"
python -m pytest integration/test_upscale_correlation.py -v --asyncio-mode=strict

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