"""
Replicate model definitions and configurations.

This module defines the available models on Replicate and their specific
configurations for optimal image generation results.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum


class ModelCategory(Enum):
    """Categories of available models"""
    GENERAL = "general"
    ARTISTIC = "artistic"
    PHOTOREALISTIC = "photorealistic"
    ANIME = "anime"
    ARCHITECTURE = "architecture"


@dataclass
class ReplicateModel:
    """Configuration for a Replicate model"""
    name: str
    model_id: str
    category: ModelCategory
    description: str
    default_params: Dict[str, Any]
    cost_per_run: float  # USD
    avg_runtime: int  # seconds
    max_prompt_length: int = 1000
    supports_negative_prompt: bool = True
    supports_image_input: bool = False
    
    def get_full_model_path(self) -> str:
        """Get the full model path for Replicate API"""
        return self.model_id


# Available models optimized for SiliconSentiments Art aesthetic
AVAILABLE_MODELS = {
    "flux_dev": ReplicateModel(
        name="Flux Dev",
        model_id="black-forest-labs/flux-dev",
        category=ModelCategory.GENERAL,
        description="High-quality general purpose model with excellent prompt following",
        default_params={
            "width": 1024,
            "height": 1024,
            "num_outputs": 1,
            "guidance_scale": 3.5,
            "num_inference_steps": 28,
            "seed": None  # Random
        },
        cost_per_run=0.055,
        avg_runtime=60
    ),
    
    "flux_schnell": ReplicateModel(
        name="Flux Schnell",
        model_id="black-forest-labs/flux-schnell",
        category=ModelCategory.GENERAL,
        description="Fast version of Flux for quick iterations",
        default_params={
            "width": 1024,
            "height": 1024,
            "num_outputs": 1,
            "num_inference_steps": 4
        },
        cost_per_run=0.003,
        avg_runtime=10
    ),
    
    "sdxl": ReplicateModel(
        name="Stable Diffusion XL",
        model_id="stability-ai/sdxl:7762fd07cf82c948538e41f63f77d685e02b063e37e496e96eefd46c929f9bdc",
        category=ModelCategory.ARTISTIC,
        description="Excellent for artistic and creative content",
        default_params={
            "width": 1024,
            "height": 1024,
            "num_outputs": 1,
            "guidance_scale": 7.5,
            "num_inference_steps": 50,
            "scheduler": "DPMSolverMultistep",
            "refine": "expert_ensemble_refiner",
            "high_noise_frac": 0.8
        },
        cost_per_run=0.0095,
        avg_runtime=30
    ),
    
    "playground_v2": ReplicateModel(
        name="Playground v2",
        model_id="playgroundai/playground-v2-1024px-aesthetic:42fe626e41cc811eaf02c94b892774839268ce1994ea778eba97103fe1ef51b8",
        category=ModelCategory.ARTISTIC,
        description="Aesthetic-focused model great for artistic content",
        default_params={
            "width": 1024,
            "height": 1024,
            "num_outputs": 1,
            "guidance_scale": 7,
            "num_inference_steps": 50,
            "scheduler": "DPMSolverMultistep"
        },
        cost_per_run=0.014,
        avg_runtime=25
    ),
    
    "juggernaut_xl": ReplicateModel(
        name="Juggernaut XL",
        model_id="lucataco/juggernaut-xl-v9:bea09cf018e513cef0841719559eff2e6e7adf92cd516b99c84ddc8a01d17bb7",
        category=ModelCategory.PHOTOREALISTIC,
        description="Photorealistic model with great detail",
        default_params={
            "width": 1024,
            "height": 1024,
            "num_outputs": 1,
            "guidance_scale": 8,
            "num_inference_steps": 25,
            "scheduler": "DPM_SDE"
        },
        cost_per_run=0.0095,
        avg_runtime=20
    ),
    
    "real_vis_xl": ReplicateModel(
        name="RealVisXL",
        model_id="lucataco/realvisxl-v3:a18eacad298f207e6addc8e20eac51afa3c1bd88ffdd7f8a19b7d096d2f2cd0e",
        category=ModelCategory.PHOTOREALISTIC,
        description="Ultra-realistic image generation",
        default_params={
            "width": 1024,
            "height": 1024,
            "num_outputs": 1,
            "guidance_scale": 7,
            "num_inference_steps": 20,
            "scheduler": "DPM++"
        },
        cost_per_run=0.0095,
        avg_runtime=18
    )
}

# SiliconSentiments brand-optimized model preferences
BRAND_PREFERRED_MODELS = [
    "flux_dev",      # Primary: Best quality
    "sdxl",          # Secondary: Artistic
    "playground_v2", # Tertiary: Aesthetic
    "flux_schnell"   # Fast iteration
]

# Model selection based on prompt type
PROMPT_TYPE_MODELS = {
    "abstract": ["flux_dev", "sdxl", "playground_v2"],
    "artistic": ["playground_v2", "sdxl", "flux_dev"],
    "realistic": ["real_vis_xl", "juggernaut_xl", "flux_dev"],
    "digital_art": ["flux_dev", "sdxl", "playground_v2"],
    "concept_art": ["sdxl", "flux_dev", "playground_v2"],
    "portrait": ["juggernaut_xl", "real_vis_xl", "flux_dev"],
    "landscape": ["flux_dev", "sdxl", "real_vis_xl"],
    "sci_fi": ["flux_dev", "sdxl", "juggernaut_xl"],
    "fantasy": ["sdxl", "playground_v2", "flux_dev"]
}


def get_model_by_name(name: str) -> Optional[ReplicateModel]:
    """Get a model by its name"""
    return AVAILABLE_MODELS.get(name)


def get_models_by_category(category: ModelCategory) -> List[ReplicateModel]:
    """Get all models in a specific category"""
    return [model for model in AVAILABLE_MODELS.values() if model.category == category]


def suggest_model_for_prompt(prompt: str) -> str:
    """
    Suggest the best model based on prompt content
    
    Args:
        prompt: The text prompt
        
    Returns:
        str: Recommended model name
    """
    prompt_lower = prompt.lower()
    
    # Check for specific keywords
    if any(word in prompt_lower for word in ["portrait", "face", "person", "human"]):
        return "juggernaut_xl"
    elif any(word in prompt_lower for word in ["realistic", "photo", "photograph"]):
        return "real_vis_xl"
    elif any(word in prompt_lower for word in ["abstract", "surreal", "experimental"]):
        return "flux_dev"
    elif any(word in prompt_lower for word in ["artistic", "painting", "art style"]):
        return "playground_v2"
    elif any(word in prompt_lower for word in ["anime", "manga", "cartoon"]):
        return "sdxl"
    
    # Default to Flux Dev for general use
    return "flux_dev"


def get_cost_estimate(model_name: str, num_generations: int = 1) -> float:
    """
    Get cost estimate for generations
    
    Args:
        model_name: Name of the model
        num_generations: Number of generations
        
    Returns:
        float: Estimated cost in USD
    """
    model = get_model_by_name(model_name)
    if not model:
        return 0.0
    
    return model.cost_per_run * num_generations


def get_runtime_estimate(model_name: str) -> int:
    """
    Get runtime estimate for a model
    
    Args:
        model_name: Name of the model
        
    Returns:
        int: Estimated runtime in seconds
    """
    model = get_model_by_name(model_name)
    if not model:
        return 60  # Default estimate
    
    return model.avg_runtime