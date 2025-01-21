import replicate
from typing import Optional

def format_prompt(description: str, max_length: int = 200) -> str:
    """Format a description into a Midjourney-compatible prompt
    
    Args:
        description: Raw text description
        max_length: Maximum prompt length
        
    Returns:
        Formatted prompt string
    """
    input_data = {
        "prompt": f"""Create a thought-provoking prompt (maximum {max_length} characters) that explores the harmonious fusion of nature and technology. Focus on:

        - Surreal and evocative front-facing scenes blending organic life with cybernetic elements, emphasizing full body shots or intimate portrait close-ups
        - Solarpunk aesthetics with sustainable tech integrated into nature, featuring lush gardens, living walls, and natural growth, focusing on full-body character compositions or detailed facial portraits
        - Mysterious cyborg or robotic beings immersed in natural environments, surrounded by organic elements and plant life, captured in full-body poses or extreme close-up portraits
        - Ethereal landscapes where digital and natural worlds converge, with fields of luminescent flora and crystalline formations, featuring prominent full-body figures or dramatic facial close-ups
        - Sacred geometry and biomechanical patterns inspired by natural structures, growth patterns, and organic forms integrated into character designs
        - Emotional resonance through natural lighting and atmospheric elements like morning mist, golden hour sunlight, or natural bioluminescence
        - Philosophical undertones about humanity's relationship with nature and technology, expressed through detailed character studies within thriving ecosystems
        - Elements that make viewers pause and contemplate, such as crystalline formations, glowing organic matter, and the seamless blend of synthetic and natural elements, utilizing either full-body or close-up portrait compositions

        IMPORTANT RULES:
        - Keep it under {max_length} characters
        - Create scenes focusing on full-body, half-body, or intimate facial portraits
        - Balance technological and natural elements with emphasis on organic life
        - Include mystical or transcendent qualities
        - Focus on mood and emotional impact through character presentation
        - Use vibrant, hopeful color schemes inspired by nature
        - Make it visually arresting for social media with strong character focus
        - Return ONLY the prompt, no other text

        Image description:
        -------------------------
        {description}
        -------------------------
        """,
        "top_p": 0.92,
        "temperature": 0.7,
        "system_prompt": "You are a Midjourney prompt engineering expert.",
        "max_new_tokens": max_length
    }

    try:
        output = replicate.run(
            "meta/meta-llama-3.1-405b-instruct",
            input=input_data
        )
        # Clean up the output and add default quality settings
        result = "".join(output).strip().replace('"', '').replace("'", '')
        # Add default quality settings if not present
        if "--q" not in result.lower():
            result += " --q 1"  # Default to high quality
        return result
    except Exception as e:
        print(f"Error formatting prompt: {str(e)}")
        return description  # Return original description if formatting fails

def add_provider_options(prompt: str, provider: str, options: Optional[dict] = None) -> str:
    """Add provider-specific options to a prompt
    
    Args:
        prompt: Base prompt string
        provider: Provider name (e.g., 'midjourney', 'flux', 'leonardo')
        options: Provider-specific options
        
    Returns:
        Modified prompt with provider options
    """
    if not options:
        return prompt
        
    if provider.lower() == 'midjourney':
        # Handle Midjourney-specific options
        for key, value in options.items():
            if key == 'niji':
                prompt += " --niji" if value else ""
            elif key == 'v':
                if value == 'niji':
                    prompt += " --niji"  # Special case for niji
                else:
                    prompt += f" --v {value}"
            elif key == 'ar':
                prompt += f" --ar {value}"
            elif key == 'q':
                prompt += f" --q {value}"
            elif key == 'seed':
                prompt += f" --seed {value}"
            elif key == 'style':
                prompt += f" --style {value}"
            elif key == 'chaos':
                prompt += f" --c {value}"
            elif key == 'stylize':
                prompt += f" --s {value}"
            elif isinstance(value, bool) and value:
                prompt += f" --{key}"
    
    return prompt 