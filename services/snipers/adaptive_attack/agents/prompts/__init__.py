"""
Adaptive Attack Prompts.

Purpose: LLM system prompts for adaptation strategy generation
Role: Define prompts for the red team strategist, chain discovery, and failure analysis agents
"""

from services.snipers.adaptive_attack.agents.prompts.adaptation_prompt import (
    ADAPTATION_SYSTEM_PROMPT,
    build_adaptation_user_prompt,
)
from services.snipers.adaptive_attack.agents.prompts.chain_discovery_prompt import (
    CHAIN_DISCOVERY_SYSTEM_PROMPT,
    build_chain_discovery_user_prompt,
)
from services.snipers.adaptive_attack.agents.prompts.failure_analysis_prompt import (
    FAILURE_ANALYSIS_SYSTEM_PROMPT,
    build_failure_analysis_user_prompt,
)

__all__ = [
    "ADAPTATION_SYSTEM_PROMPT",
    "build_adaptation_user_prompt",
    "CHAIN_DISCOVERY_SYSTEM_PROMPT",
    "build_chain_discovery_user_prompt",
    "FAILURE_ANALYSIS_SYSTEM_PROMPT",
    "build_failure_analysis_user_prompt",
]
