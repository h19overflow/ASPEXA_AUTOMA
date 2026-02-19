"""
LLM system prompts for adaptive attack agents.
"""

from services.snipers.core.agents.prompts.adaptation_prompt import (
    ADAPTATION_SYSTEM_PROMPT,
    build_adaptation_user_prompt,
)
from services.snipers.core.agents.prompts.chain_discovery_prompt import (
    CHAIN_DISCOVERY_SYSTEM_PROMPT,
    build_chain_discovery_user_prompt,
)
from services.snipers.core.agents.prompts.failure_analysis_prompt import (
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
