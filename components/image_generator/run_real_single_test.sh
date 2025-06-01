#!/bin/bash
# Run a single test with the Midjourney API without second confirmation

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

# Parse command line arguments
PROMPT=""
OUTPUT_DIR="./test_output"
VARIANT=""
SKIP_UPSCALE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --prompt|-p)
      PROMPT="$2"
      shift 2
      ;;
    --output-dir|-o)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --variant|-v)
      VARIANT="--variant $2"
      shift 2
      ;;
    --skip-upscale|-s)
      SKIP_UPSCALE=true
      shift
      ;;
    *)
      # If no flag is provided, assume it's the prompt
      if [ -z "$PROMPT" ]; then
        PROMPT="$1"
      fi
      shift
      ;;
  esac
done

# Display warning and get confirmation
echo -e "\n${RED}WARNING: This will use real Midjourney API calls and consume credits${NC}"
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Test cancelled."
    exit 0
fi

# If no prompt was provided, ask for one
if [ -z "$PROMPT" ]; then
    read -p "Enter prompt for image generation: " PROMPT
    if [ -z "$PROMPT" ]; then
        echo "No prompt provided. Exiting."
        exit 1
    fi
fi

# Set up upscale flag
UPSCALE_FLAG=""
if [ "$SKIP_UPSCALE" = true ]; then
    UPSCALE_FLAG="--skip-upscale"
fi

# Run the real test with the provided prompt
echo -e "\n${BLUE}=== Running Real Test with Prompt: ${YELLOW}${PROMPT}${NC}"
echo -e "${BLUE}=== Output Directory: ${YELLOW}${OUTPUT_DIR}${NC}"

# Execute the test with no-confirm flag to skip the second confirmation
python run_real_test.py --prompt "$PROMPT" --output-dir "$OUTPUT_DIR" $VARIANT $UPSCALE_FLAG --no-confirm

# Print completion message
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo -e "\n${GREEN}Test completed successfully!${NC}"
else
    echo -e "\n${RED}Test failed with exit code $exit_code${NC}"
fi

exit $exit_code 