#!/usr/bin/env python3
"""
Test Configuration

Central configuration for all Midjourney tests, including:
- Model versions
- Aspect ratios
- Test prompts
- Timing parameters
"""

# Model version options
MODEL_VERSIONS = {
    "v6": "--v 6",
    "v6.1": "--v 6.1",
    "v7": "--v 7.0",
    "niji6": "--niji 6"
}

# Aspect ratio options
ASPECT_RATIOS = {
    "square": "--ar 1:1",
    "portrait": "--ar 4:5",     # Instagram optimal
    "landscape": "--ar 16:9",   # Widescreen
    "wide": "--ar 21:9",        # Ultrawide
    "pinterest": "--ar 2:3"     # Pinterest optimal
}

# Standard test prompts - categorized for different test purposes
BASE_PROMPTS = {
    # Simple prompts for basic functionality tests
    "simple": [
        "a cat playing a piano, digital art style",
        "sunset over mountains, watercolor style",
        "futuristic cityscape with flying cars, cyberpunk style"
    ],
    
    # Complex prompts with detailed parameters for stress testing
    "complex": [
        "intricate fantasy castle with detailed architecture, dragons flying overhead, mountains in background, dramatic lighting, highly detailed",
        "underwater city with bioluminescent creatures, coral reefs, ancient ruins, and swimming merfolk, photorealistic style",
        "steampunk laboratory with complex machinery, brass pipes, gears, and a mad scientist working on experiments, volumetric lighting"
    ],
    
    # Artistic style variety for testing different model capabilities
    "artistic": [
        "portrait of a woman in the style of Alphonse Mucha, art nouveau style",
        "landscape in the style of Van Gogh, with swirling clouds and cypress trees",
        "still life with fruits in the style of Caravaggio, dramatic chiaroscuro lighting"
    ],
    
    # Edge cases that might challenge the system
    "edge_cases": [
        "completely empty white space with a single tiny red dot",
        "extremely detailed and intricate mandala with hundreds of patterns within patterns",
        "abstract concept of time passing, minimalist style"
    ]
}

# Timing parameters (in seconds)
TIMING = {
    "generation_timeout": 600,      # Maximum time to wait for image generation (10 mins)
    "upscale_timeout": 300,         # Maximum time to wait for upscale (5 mins)
    "poll_interval_short": 3,       # Short polling interval 
    "poll_interval_long": 20,       # Longer polling interval
    "delay_between_tests": 60,      # Delay between test runs to avoid rate limits
    "reconnect_delay": 5            # Delay before attempting reconnection
}

# Error simulation parameters
ERROR_SIMULATION = {
    "timeout_duration": 30,          # Simulate timeout for this duration
    "network_failure_duration": 10,  # Simulate network failure for this duration
    "invalid_token_prefix": "INVALID_"  # Prefix to create invalid tokens
}

# Test batch sizes
BATCH_SIZES = {
    "small": 2,
    "medium": 5,
    "large": 10
}

# Combine parameters to form complete test cases
def get_test_cases(category="simple", count=3, model="v6", aspect_ratio=None):
    """
    Generate test cases with the specified parameters
    
    Args:
        category: The prompt category to use
        count: Number of prompts to return
        model: Model version to use
        aspect_ratio: Aspect ratio to use (or None for default)
    
    Returns:
        List of test case dictionaries
    """
    prompts = BASE_PROMPTS.get(category, BASE_PROMPTS["simple"])
    selected_prompts = prompts[:min(count, len(prompts))]
    
    test_cases = []
    for prompt in selected_prompts:
        test_case = {
            "base_prompt": prompt,
            "model_version": MODEL_VERSIONS[model],
            "aspect_ratio": ASPECT_RATIOS.get(aspect_ratio, "") if aspect_ratio else "",
        }
        
        # Build the full prompt with parameters
        full_prompt = prompt
        if aspect_ratio:
            full_prompt += f" {ASPECT_RATIOS[aspect_ratio]}"
        full_prompt += f" {MODEL_VERSIONS[model]}"
        
        test_case["full_prompt"] = full_prompt
        test_cases.append(test_case)
    
    return test_cases 