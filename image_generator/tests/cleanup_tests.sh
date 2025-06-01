#!/bin/bash
# Cleanup script to remove old test runners and backup files

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Cleanup Script: This script will remove old test runners and backup files${NC}"
echo "The following files will be removed:"

# List files to be removed
old_runners=(
    "run_new_tests.sh"
    "run_tests.sh"
    "../run_coroutine_test.sh"
    "../run_tests_with_env.sh"
    "simple_rate_limiter_test.py.bak"
    "test_rate_limiter_simple.py"
    "simple_mock_test.py"
)

for file in "${old_runners[@]}"; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done

# Prompt for confirmation
read -p "Do you want to proceed? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operation cancelled."
    exit 0
fi

# Remove old test runners
for file in "${old_runners[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        echo -e "${GREEN}Removed: $file${NC}"
    fi
done

echo -e "${GREEN}Cleanup complete!${NC}"
echo "The consolidated test runner 'run_all_tests.sh' replaces all removed scripts."
