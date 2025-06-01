#!/bin/bash
# Script to run real tests with upscale correlation improvements

set -e  # Exit on error

# Determine script directory for relative paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Running Upscale Correlation Real Tests${NC}"
echo -e "${BLUE}================================================${NC}"

# Parse arguments
MOCK_MODE=true
SKIP_UPSCALE=false
PROMPT="test anime style cat wearing a space suit --niji"

while getopts ":lp:sv" opt; do
  case ${opt} in
    l )
      MOCK_MODE=false
      ;;
    p )
      PROMPT="$OPTARG"
      ;;
    s )
      SKIP_UPSCALE=true
      ;;
    v )
      VERBOSE=true
      ;;
    \? )
      echo "Usage: $0 [-l] [-p prompt] [-s] [-v]"
      echo "  -l  Run in live mode (real API calls)"
      echo "  -p  Specify prompt (default: \"$PROMPT\")"
      echo "  -s  Skip upscale step"
      echo "  -v  Verbose output"
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

# Create timestamp for this test run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="$ROOT_DIR/tests/test_output/$TIMESTAMP"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run the tests
cd "$ROOT_DIR"

echo -e "${YELLOW}Test prompt: ${NC}\"$PROMPT\""
echo -e "${YELLOW}Output directory: ${NC}$OUTPUT_DIR"

# Run unit tests first
echo -e "\n${BLUE}Running upscale correlation unit tests...${NC}"
"$SCRIPT_DIR/test_upscale_correlation.sh" -m
if [ $? -ne 0 ]; then
    echo -e "${RED}Unit tests failed! Aborting real test.${NC}"
    exit 1
fi

# Build the command
CMD="python run_real_test.py --prompt \"$PROMPT\" --output-dir \"$OUTPUT_DIR\" --no-confirm"

if [ "$SKIP_UPSCALE" = true ]; then
    CMD="$CMD --skip-upscale"
    echo -e "${YELLOW}Skipping upscale step${NC}"
fi

if [ "$VERBOSE" = true ]; then
    echo -e "${YELLOW}Command: ${NC}$CMD"
fi

# Run the real test
echo -e "\n${BLUE}Running real test with correlation improvements...${NC}"
eval $CMD

# Check if test passed
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ Real test PASSED!${NC}"
    
    # Check if upscale files were created (unless we skipped upscaling)
    if [ "$SKIP_UPSCALE" = false ]; then
        UPSCALE_COUNT=$(find "$OUTPUT_DIR" -name "*variant_*.png" | wc -l)
        if [ $UPSCALE_COUNT -gt 0 ]; then
            echo -e "${GREEN}Found $UPSCALE_COUNT upscale images${NC}"
        else
            echo -e "${RED}No upscale images found in output directory!${NC}"
            exit 1
        fi
        
        # Check for upscales metadata file
        if [ -f "$OUTPUT_DIR/upscales_$TIMESTAMP.json" ]; then
            echo -e "${GREEN}Upscales metadata file exists${NC}"
        else
            echo -e "${RED}No upscales metadata file found!${NC}"
            exit 1
        fi
    fi
    
    # List generated files
    echo -e "\n${BLUE}Generated files:${NC}"
    ls -la "$OUTPUT_DIR"
    
    exit 0
else
    echo -e "\n${RED}✗ Real test FAILED!${NC}"
    exit 1
fi 