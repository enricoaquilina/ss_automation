#!/bin/bash
# Script to run upscale correlation tests

set -e  # Exit on error

# Determine script directory for relative paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Running Upscale Correlation Tests${NC}"
echo -e "${BLUE}================================================${NC}"

# Parse arguments
MOCK_MODE=true
VERBOSE=""

while getopts ":lvm" opt; do
  case ${opt} in
    l )
      MOCK_MODE=false
      ;;
    v )
      VERBOSE="-v"
      ;;
    m )
      MOCK_MODE=true
      ;;
    \? )
      echo "Usage: $0 [-l] [-v] [-m]"
      echo "  -l  Run in live mode (real API calls)"
      echo "  -v  Verbose output"
      echo "  -m  Run in mock mode (default)"
      exit 1
      ;;
  esac
done

# Set test environment variables
if [ "$MOCK_MODE" = true ]; then
    echo -e "${GREEN}Running in MOCK mode (no real API calls)${NC}"
    export MOCK_MIDJOURNEY=1
else
    echo -e "${RED}Running in LIVE mode (will make real API calls)${NC}"
    export MOCK_MIDJOURNEY=0
fi

# Create output directory if it doesn't exist
mkdir -p "$ROOT_DIR/tests/test_output"

# Run the tests
cd "$ROOT_DIR"

echo "Running upscale correlation tests..."
python -m pytest "$SCRIPT_DIR/test_upscale_correlation.py" $VERBOSE

# Check if test passed
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Upscale correlation tests PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ Upscale correlation tests FAILED!${NC}"
    exit 1
fi 