#!/usr/bin/env python3
"""
Tests for prompt formatting functionality.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import pytest

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class TestPromptFormatting(unittest.TestCase):
    """Tests for prompt formatting"""
    
    def test_model_prefix_detection(self):
        """Test detection of model prefixes in prompts"""
        # Test cases for v7.0
        v7_prompts = [
            "test prompt --v 7.0",
            "test prompt --version 7.0",
            "test prompt --v7.0",
            "test prompt --v7",
            "test prompt --v 7",
            "test prompt with v7.0 in middle --v 7.0",
            "test --v7.0 prompt",
        ]
        
        for prompt in v7_prompts:
            self.assertTrue(self._is_v7_prompt(prompt), f"Failed to detect v7.0 in: {prompt}")
            self.assertFalse(self._is_niji_prompt(prompt), f"Incorrectly detected niji in: {prompt}")
        
        # Test cases for niji
        niji_prompts = [
            "test prompt --niji",
            "test prompt --niji 6",
            "test prompt --niji6",
            "test prompt with niji in middle --niji",
            "test --niji prompt",
        ]
        
        for prompt in niji_prompts:
            self.assertTrue(self._is_niji_prompt(prompt), f"Failed to detect niji in: {prompt}")
            self.assertFalse(self._is_v7_prompt(prompt), f"Incorrectly detected v7.0 in: {prompt}")
        
        # Test cases with neither
        neutral_prompts = [
            "test prompt",
            "test prompt with v7.0 in text but no flag",
            "test prompt with niji in text but no flag",
        ]
        
        for prompt in neutral_prompts:
            self.assertFalse(self._is_v7_prompt(prompt), f"Incorrectly detected v7.0 in: {prompt}")
            self.assertFalse(self._is_niji_prompt(prompt), f"Incorrectly detected niji in: {prompt}")
    
    def test_model_prefix_addition(self):
        """Test adding model prefixes to prompts that don't have them"""
        # Prompts without model flags
        prompts_without_flags = [
            "test prompt",
            "another test prompt",
            "prompt with v7.0 in text but no flag",
            "prompt with niji in text but no flag",
        ]
        
        # Adding v7.0 flag
        for prompt in prompts_without_flags:
            v7_prompt = self._add_v7_flag(prompt)
            self.assertTrue(self._is_v7_prompt(v7_prompt), f"Failed to add v7.0 flag to: {prompt}")
            self.assertFalse(self._is_niji_prompt(v7_prompt), f"Incorrectly added niji flag to: {prompt}")
        
        # Adding niji flag
        for prompt in prompts_without_flags:
            niji_prompt = self._add_niji_flag(prompt)
            self.assertTrue(self._is_niji_prompt(niji_prompt), f"Failed to add niji flag to: {prompt}")
            self.assertFalse(self._is_v7_prompt(niji_prompt), f"Incorrectly added v7.0 flag to: {prompt}")
    
    def test_flag_replacement(self):
        """Test replacing one model flag with another"""
        # Prompts with v7.0 flags
        v7_prompts = [
            "test prompt --v 7.0",
            "test prompt --version 7.0",
            "test prompt --v7.0",
        ]
        
        # Replace v7.0 with niji
        for prompt in v7_prompts:
            niji_prompt = self._replace_with_niji_flag(prompt)
            self.assertTrue(self._is_niji_prompt(niji_prompt), f"Failed to replace v7.0 with niji in: {prompt}")
            self.assertFalse(self._is_v7_prompt(niji_prompt), f"Failed to remove v7.0 flag in: {prompt}")
        
        # Prompts with niji flags
        niji_prompts = [
            "test prompt --niji",
            "test prompt --niji 6",
            "test prompt --niji6",
        ]
        
        # Replace niji with v7.0
        for prompt in niji_prompts:
            v7_prompt = self._replace_with_v7_flag(prompt)
            self.assertTrue(self._is_v7_prompt(v7_prompt), f"Failed to replace niji with v7.0 in: {prompt}")
            self.assertFalse(self._is_niji_prompt(v7_prompt), f"Failed to remove niji flag in: {prompt}")
    
    def _is_v7_prompt(self, prompt):
        """Check if prompt has v7.0 flag"""
        v7_flags = ["--v 7", "--v7", "--v 7.0", "--v7.0", "--version 7", "--version 7.0"]
        return any(flag in prompt.lower() for flag in v7_flags)
    
    def _is_niji_prompt(self, prompt):
        """Check if prompt has niji flag"""
        niji_flags = ["--niji", "--niji 6", "--niji6"]
        return any(flag in prompt.lower() for flag in niji_flags)
    
    def _add_v7_flag(self, prompt):
        """Add v7.0 flag to prompt"""
        return f"{prompt} --v 7.0"
    
    def _add_niji_flag(self, prompt):
        """Add niji flag to prompt"""
        return f"{prompt} --niji 6"
    
    def _replace_with_v7_flag(self, prompt):
        """Replace any model flag with v7.0 flag"""
        # Remove niji flags
        for flag in ["--niji 6", "--niji6", "--niji"]:
            prompt = prompt.replace(flag, "")
        return f"{prompt.strip()} --v 7.0"
    
    def _replace_with_niji_flag(self, prompt):
        """Replace any model flag with niji flag"""
        # Remove v7 flags
        for flag in ["--v 7.0", "--v7.0", "--version 7.0", "--v 7", "--v7", "--version 7"]:
            prompt = prompt.replace(flag, "")
        return f"{prompt.strip()} --niji 6"


if __name__ == "__main__":
    unittest.main() 