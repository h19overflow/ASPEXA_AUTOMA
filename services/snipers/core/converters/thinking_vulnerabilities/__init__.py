"""Thinking Vulnerabilities Converters - CoT/Reasoning Model Bypass.

Purpose: Configure PyRIT converters that exploit reasoning model vulnerabilities
Role: Provide factory functions for converters targeting GPT-5/Gemini 2.5 thinking
Dependencies: PyRIT prompt_converter module

Research Sources:
  - MathPromptConverter: Forces CoT token allocation to math problems
  - CodeChameleonConverter: Exploits code execution vs reading distinction
  - AsciiSmugglerConverter: Unicode steganography post-safety-check injection
  - CatAttack (2025): Distraction triggers that confuse reasoning chains
"""
from .converter_factory import (
    get_thinking_vulnerability_converters,
    create_math_prompt_converter,
    create_code_chameleon_converter,
    create_ascii_smuggler_converter,
    create_cat_attack_converter,
    create_distract_then_encrypt_chain,
    THINKING_VULNERABILITY_METADATA,
)

__all__ = [
    "get_thinking_vulnerability_converters",
    "create_math_prompt_converter",
    "create_code_chameleon_converter",
    "create_ascii_smuggler_converter",
    "create_cat_attack_converter",
    "create_distract_then_encrypt_chain",
    "THINKING_VULNERABILITY_METADATA",
]
