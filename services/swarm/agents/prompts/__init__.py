"""
Prompts package for scanning agents.

Purpose: Export all prompt templates for scanning agents.
Dependencies: Individual prompt modules, services.swarm.core.config
"""
from services.swarm.core.config import AgentType

from .planning_instruction_prompt import PLANNING_INSTRUCTION
from .sql_planning_prompt import SQL_PLANNING_PROMPT
from .auth_planning_prompt import AUTH_PLANNING_PROMPT
from .jailbreak_planning_prompt import JAILBREAK_PLANNING_PROMPT


SYSTEM_PROMPTS = {
    AgentType.SQL: SQL_PLANNING_PROMPT,
    AgentType.AUTH: AUTH_PLANNING_PROMPT,
    AgentType.JAILBREAK: JAILBREAK_PLANNING_PROMPT,
}


def get_system_prompt(agent_type: str, probe_categories: str, available_probes: str) -> str:
    """Get formatted system prompt for agent type.

    Args:
        agent_type: One of agent_sql, agent_auth, agent_jailbreak
        probe_categories: Comma-separated probe categories
        available_probes: Comma-separated probe names

    Returns:
        Formatted planning prompt with agent-specific instructions
    """
    agent_enum = AgentType(agent_type) if agent_type in [e.value for e in AgentType] else AgentType.SQL
    template = SYSTEM_PROMPTS.get(agent_enum, JAILBREAK_PLANNING_PROMPT)

    return template.format(
        planning_instruction=PLANNING_INSTRUCTION,
        probe_categories=probe_categories,
        available_probes=available_probes,
    )


__all__ = [
    "PLANNING_INSTRUCTION",
    "SQL_PLANNING_PROMPT",
    "AUTH_PLANNING_PROMPT",
    "JAILBREAK_PLANNING_PROMPT",
    "SYSTEM_PROMPTS",
    "get_system_prompt",
]
