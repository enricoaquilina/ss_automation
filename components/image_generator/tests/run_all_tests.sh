#!/bin/bash
# Consolidated test runner for the image_generator component

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

# Create required directories
mkdir -p test_output
mkdir -p test_logs

# Check if check_env.sh exists and is executable
check_environment() {
    if [ -x "$SCRIPT_DIR/../check_env.sh" ]; then
        echo -e "\n${BLUE}=== Checking Environment Configuration ===${NC}"
        "$SCRIPT_DIR/../check_env.sh"
        return $?
    else
        echo -e "\n${YELLOW}Warning: check_env.sh not found or not executable.${NC}"
        echo -e "${YELLOW}Environment configuration will not be verified.${NC}"
        return 0
    fi
}

# Show menu if no arguments provided
if [ $# -eq 0 ]; then
    echo "=== Silicon Sentiments Image Generator Test Runner ==="
    echo "Choose test category to run:"
    echo "1) All tests"
    echo "2) Unit tests only"
    echo "3) Integration tests only"
    echo "4) Rate limiter tests"
    echo "5) Error handling tests"
    echo "6) Core functionality tests"
    echo "7) Upscale correlation tests"
    echo "8) Run with real API (uses Midjourney credits!)"
    echo "9) Auto mode (run mock tests, then live if successful)"
    echo "10) Exit"
    echo
    echo "Options:"
    echo "  --no-confirm  Skip confirmation prompts (use with caution!)"
    echo
    read -p "Enter your choice [1-10]: " choice
else
    choice=$1
fi

run_unit_tests() {
    echo -e "\n${BLUE}=== Running Unit Tests ===${NC}"
    
    echo -e "\n${YELLOW}• Error Classes Tests${NC}"
    python -m pytest unit/test_error_classes.py -v
    unit_result=$?
    if [ $unit_result -ne 0 ]; then
        return $unit_result
    fi
    
    echo -e "\n${YELLOW}• Rate Limiter Tests${NC}"
    python -m pytest unit/test_rate_limiter.py -v
    unit_result=$?
    if [ $unit_result -ne 0 ]; then
        return $unit_result
    fi
    
    echo -e "\n${YELLOW}• Simple Rate Limiter Tests${NC}"
    python -m pytest unit/test_simple_rate_limiter.py -v
    unit_result=$?
    if [ $unit_result -ne 0 ]; then
        return $unit_result
    fi
    
    echo -e "\n${YELLOW}• Mock Client Tests${NC}"
    python -m pytest unit/test_mock_client.py -v
    unit_result=$?
    if [ $unit_result -ne 0 ]; then
        return $unit_result
    fi
    
    echo -e "\n${YELLOW}• Other Unit Tests${NC}"
    python -m pytest unit/test_basic.py unit/test_datetime_handling.py unit/test_prompt_formatting.py -v
    unit_result=$?
    if [ $unit_result -ne 0 ]; then
        return $unit_result
    fi
    
    echo -e "\n${YELLOW}• Variant Matching Tests${NC}"
    python -m pytest unit/test_variant_matching.py -v
    unit_result=$?
    if [ $unit_result -ne 0 ]; then
        return $unit_result
    fi
    
    echo -e "\n${YELLOW}• Variation Handling Tests${NC}"
    python -m pytest unit/test_variation_name_handling.py -v
    unit_result=$?
    if [ $unit_result -ne 0 ]; then
        return $unit_result
    fi
    
    echo -e "\n${YELLOW}• Button Tests${NC}"
    python -m pytest unit/test_upscale_buttons.py unit/test_force_button_click.py -v
    unit_result=$?
    if [ $unit_result -ne 0 ]; then
        return $unit_result
    fi
    
    echo -e "\n${YELLOW}• Upscale Processing Tests${NC}"
    python -m pytest unit/test_upscale_processing.py -v
    return $?
}

run_integration_tests() {
    echo -e "\n${BLUE}=== Running Integration Tests ===${NC}"
    
    echo -e "\n${YELLOW}• Client Rate Limiting Tests${NC}"
    python -m pytest integration/test_client_rate_limiting.py -v
    int_result=$?
    if [ $int_result -ne 0 ]; then
        return $int_result
    fi
    
    echo -e "\n${YELLOW}• Error Handling Tests${NC}"
    python -m pytest integration/test_error_handling.py -v
    int_result=$?
    if [ $int_result -ne 0 ]; then
        return $int_result
    fi
    
    echo -e "\n${YELLOW}• Storage Tests${NC}"
    python -m pytest integration/test_storage.py integration/test_gridfs_storage.py -v
    int_result=$?
    if [ $int_result -ne 0 ]; then
        return $int_result
    fi
    
    echo -e "\n${YELLOW}• Slash Command Tests${NC}"
    python -m pytest integration/test_slash_commands.py -v
    int_result=$?
    if [ $int_result -ne 0 ]; then
        return $int_result
    fi
    
    echo -e "\n${YELLOW}• Variation Naming Tests${NC}"
    python -m pytest integration/test_variation_naming_integration.py -v
    int_result=$?
    if [ $int_result -ne 0 ]; then
        return $int_result
    fi
    
    echo -e "\n${YELLOW}• Imagine/Upscale Workflow Tests${NC}"
    python -m pytest integration/test_imagine_upscale_workflow.py -v
    int_result=$?
    if [ $int_result -ne 0 ]; then
        return $int_result
    fi
    
    echo -e "\n${YELLOW}• Upscale Correlation Tests${NC}"
    python -m pytest integration/test_upscale_correlation.py -v --asyncio-mode=strict
    int_result=$?
    if [ $int_result -ne 0 ]; then
        return $int_result
    fi
    
    echo -e "\n${YELLOW}• Content Moderation Tests${NC}"
    python -m pytest integration/test_midjourney_integration.py::test_content_moderation_handling -v --asyncio-mode=strict
    int_result=$?
    if [ $int_result -ne 0 ]; then
        return $int_result
    fi
    
    echo -e "\n${YELLOW}• Aspect Ratio Tests${NC}"
    python -m pytest integration/test_aspect_ratios.py -v
    int_result=$?
    if [ $int_result -ne 0 ]; then
        return $int_result
    fi
    
    echo -e "\n${YELLOW}• Discord Auth Tests${NC}"
    python -m pytest integration/test_discord_auth.py -v
    int_result=$?
    if [ $int_result -ne 0 ]; then
        return $int_result
    fi
    
    echo -e "\n${YELLOW}• Midjourney Workflow Tests${NC}"
    python -m pytest integration/test_midjourney_workflow.py -v
    return $?
}

run_mock_tests() {
    echo -e "\n${BLUE}=== Running Simple Mock Tests ===${NC}"
    export FULLY_MOCKED=true
    python -m pytest unit/test_mock_client.py -v
    mock_result=$?
    if [ $mock_result -ne 0 ]; then
        return $mock_result
    fi
    
    echo -e "\n${YELLOW}• Simple Coroutine Test${NC}"
    python simple_coroutine_test.py
    return $?
}

run_rate_limiter_tests() {
    echo -e "\n${BLUE}=== Running Rate Limiter Tests ===${NC}"
    python -m pytest unit/test_rate_limiter.py unit/test_simple_rate_limiter.py -v
    rate_result=$?
    if [ $rate_result -ne 0 ]; then
        return $rate_result
    fi
    
    python -m pytest integration/test_client_rate_limiting.py -v
    return $?
}

run_error_handling_tests() {
    echo -e "\n${BLUE}=== Running Error Handling Tests ===${NC}"
    python -m pytest unit/test_error_classes.py -v
    err_result=$?
    if [ $err_result -ne 0 ]; then
        return $err_result
    fi
    
    python -m pytest integration/test_error_handling.py -v
    return $?
}

run_correlation_tests() {
    echo -e "\n${BLUE}=== Running Upscale Correlation Tests ===${NC}"
    
    # Configure test mode
    if [ "$1" == "live" ]; then
        echo -e "${YELLOW}WARNING: Running in LIVE mode. This will use real Discord API calls and consume Midjourney credits!${NC}"
        
        # Check if --no-confirm flag is passed
        if [ "$2" != "--no-confirm" ]; then
            read -p "Are you sure you want to continue? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Test cancelled."
                return 1
            fi
        fi
        
        export FULLY_MOCKED=false
        export LIVE_TEST=true
    else
        export FULLY_MOCKED=true
        export LIVE_TEST=false
    fi
    
    # Run upscale correlation tests
    echo -e "\n${YELLOW}• Integration Upscale Correlation Tests${NC}"
    python -m pytest integration/test_upscale_correlation.py -v --asyncio-mode=strict
    corr_result=$?
    if [ $corr_result -ne 0 ]; then
        echo -e "${RED}✖ Upscale correlation tests failed${NC}"
        return $corr_result
    fi
    
    # Run content moderation test
    echo -e "\n${YELLOW}• Content Moderation Handling Test${NC}"
    python -m pytest integration/test_midjourney_integration.py::test_content_moderation_handling -v --asyncio-mode=strict
    corr_result=$?
    if [ $corr_result -ne 0 ]; then
        echo -e "${RED}✖ Content moderation tests failed${NC}"
        return $corr_result
    fi
    
    echo -e "${GREEN}✓ All correlation tests passed${NC}"
    return 0
}

run_live_api_tests() {
    # Check environment configuration first
    check_environment
    env_check=$?
    if [ $env_check -ne 0 ]; then
        echo -e "${RED}Environment configuration check failed. Please fix issues before running live tests.${NC}"
        return 1
    fi

    echo -e "\n${RED}WARNING: This will use real Midjourney API calls and consume credits${NC}"
    
    # Check if --no-confirm flag is passed
    if [ "$1" != "--no-confirm" ]; then
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Test cancelled."
        return 1
        fi
    fi
    
    # We've confirmed with the user now, so set environment variables
    export FULLY_MOCKED=false
    export LIVE_TEST=true
    
    echo -e "\n${BLUE}=== Running Live Workflow Tests ===${NC}"
    python -m pytest integration/test_midjourney_live_workflow.py -v --log-cli-level=INFO --log-file=test_logs/live_workflow_specific.log --log-file-level=DEBUG
    live_result=$?
    if [ $live_result -ne 0 ]; then
        echo -e "${RED}✖ Live workflow tests failed${NC}"
        return $live_result
    fi
    
    echo -e "\n${BLUE}=== Running Midjourney Integration Tests ===${NC}"
    python -m pytest integration/test_midjourney_integration.py -v
    live_result=$?
    if [ $live_result -ne 0 ]; then
        echo -e "${RED}✖ Midjourney integration tests failed${NC}"
        return $live_result
    fi
    
    echo -e "\n${BLUE}=== Running Live Upscale Correlation Tests ===${NC}"
    
    # Always pass --no-confirm flag here, as we've already confirmed with the user
    run_correlation_tests "live" "--no-confirm"
    return $?
}

run_auto_tests() {
    # First run mock tests
    echo -e "\n${BLUE}=== AUTO MODE: First running all tests in mock mode ===${NC}"
    export FULLY_MOCKED=true
    
    run_unit_tests
    unit_result=$?
    if [ $unit_result -ne 0 ]; then
        echo -e "${RED}✖ Unit tests failed in mock mode. Not proceeding to live tests.${NC}"
        return $unit_result
    fi
    
    run_integration_tests
    int_result=$?
    if [ $int_result -ne 0 ]; then
        echo -e "${RED}✖ Integration tests failed in mock mode. Not proceeding to live tests.${NC}"
        return $int_result
    fi
    
    run_mock_tests
    mock_result=$?
    if [ $mock_result -ne 0 ]; then
        echo -e "${RED}✖ Core mock tests failed. Not proceeding to live tests.${NC}"
        return $mock_result
    fi
    
    echo -e "\n${GREEN}✓ All mock tests passed!${NC}"
    
    # Now run live tests
    echo -e "\n${BLUE}=== AUTO MODE: All mock tests passed. Proceeding to live mode ===${NC}"
    
    # Check if --no-confirm flag is passed
    if [ "$1" == "--no-confirm" ]; then
        run_live_api_tests "--no-confirm"
    else
        run_live_api_tests
    fi
    return $?
}

case $choice in
    1|"all")
        echo -e "${BLUE}=== Running All Tests ===${NC}"
        export FULLY_MOCKED=true
        run_unit_tests
        unit_result=$?
        if [ $unit_result -eq 0 ]; then
        run_integration_tests
            int_result=$?
            if [ $int_result -eq 0 ]; then
        run_mock_tests
            fi
        fi
        ;;
    2|"unit")
        run_unit_tests
        ;;
    3|"integration")
        export FULLY_MOCKED=true
        run_integration_tests
        ;;
    4|"rate")
        run_rate_limiter_tests
        ;;
    5|"error")
        run_error_handling_tests
        ;;
    6|"core")
        run_mock_tests
        ;;
    7|"correlation")
        run_correlation_tests
        ;;
    8|"live")
        # Check for --no-confirm flag as second argument
        if [ "$2" == "--no-confirm" ]; then
            run_live_api_tests "--no-confirm"
        else
        run_live_api_tests
        fi
        ;;
    9|"auto")
        # Run in auto mode - mock tests first, then live if successful
        if [ "$2" == "--no-confirm" ]; then
            run_auto_tests "--no-confirm"
        else
            run_auto_tests
        fi
        ;;
    10|"exit")
        echo "Exiting test runner"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid option. Exiting.${NC}"
        exit 1
        ;;
esac

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