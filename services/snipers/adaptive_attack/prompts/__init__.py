"""
Adaptive Attack Prompts.

Purpose: LLM system prompts for adaptation strategy generation
Role: Define prompts for the red team strategist and chain discovery agents
"""

from services.snipers.adaptive_attack.prompts.adaptation_prompt import (
    ADAPTATION_SYSTEM_PROMPT,
    build_adaptation_user_prompt,
)
from services.snipers.adaptive_attack.prompts.chain_discovery_prompt import (
    CHAIN_DISCOVERY_SYSTEM_PROMPT,
    build_chain_discovery_user_prompt,
)

__all__ = [
    "ADAPTATION_SYSTEM_PROMPT",
    "build_adaptation_user_prompt",
    "CHAIN_DISCOVERY_SYSTEM_PROMPT",
    "build_chain_discovery_user_prompt",
]
