"""Prompt engineering utilities for MegaAgent Pro.

This module provides:
- Chain-of-Thought (CoT) prompting templates
- Prompt enhancement utilities
- Template selection logic
"""

from __future__ import annotations

from .chain_of_thought import (CoTTemplate, apply_cot, enhance_prompt_with_cot,
                               get_cot_prompt, select_cot_template)

__all__ = [
    "CoTTemplate",
    "apply_cot",
    "enhance_prompt_with_cot",
    "get_cot_prompt",
    "select_cot_template",
]
