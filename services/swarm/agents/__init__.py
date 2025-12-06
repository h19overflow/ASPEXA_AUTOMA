"""
Agent system for intelligent security scanning.

Purpose: LangChain agents for analyzing recon intelligence and executing targeted scans
Role: Coordinates scanning with intelligent decision-making
Dependencies: langchain, langchain_google_genai, scanner, config
"""
from typing import Dict, Type

# New agent architecture (LangChain v1)
from .base_agent import BaseAgent, ProbePlan
from .sql import SQLAgent
from .auth import AuthAgent
from .jailbreak import JailbreakAgent

# Legacy imports (backward compatibility)
from .base import (
    create_planning_agent,
    run_planning_agent,
    create_scanning_agent,
    run_scanning_agent,
)
from .trinity import (
    run_sql_agent,
    create_sql_agent,
    run_auth_agent,
    create_auth_agent,
    run_jailbreak_agent,
    create_jailbreak_agent,
)
from .tools import PLANNING_TOOLS, analyze_target, plan_scan, get_available_probes
from .prompts import SYSTEM_PROMPTS, get_system_prompt


# Agent registry for new architecture
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    "sql": SQLAgent,
    "auth": AuthAgent,
    "jailbreak": JailbreakAgent,
}


def get_agent(agent_type: str, **kwargs) -> BaseAgent:
    """Get agent instance by type.

    Args:
        agent_type: 'sql', 'auth', or 'jailbreak'
        **kwargs: Passed to agent constructor (e.g., model_name)

    Returns:
        Agent instance

    Raises:
        ValueError: If agent_type is unknown
    """
    if agent_type not in AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent type: {agent_type}. "
            f"Available: {list(AGENT_REGISTRY.keys())}"
        )
    return AGENT_REGISTRY[agent_type](**kwargs)


__all__ = [
    # New agent architecture (LangChain v1)
    "BaseAgent",
    "ProbePlan",
    "SQLAgent",
    "AuthAgent",
    "JailbreakAgent",
    "AGENT_REGISTRY",
    "get_agent",

    # Planning interface (legacy - still primary for entrypoint)
    "create_planning_agent",
    "run_planning_agent",

    # Backward compatibility (deprecated)
    "create_scanning_agent",
    "run_scanning_agent",

    # Specialized agents (The Trinity - legacy)
    "run_sql_agent",
    "create_sql_agent",
    "run_auth_agent",
    "create_auth_agent",
    "run_jailbreak_agent",
    "create_jailbreak_agent",

    # Tools
    "PLANNING_TOOLS",
    "analyze_target",
    "plan_scan",
    "get_available_probes",

    # Prompts
    "SYSTEM_PROMPTS",
    "get_system_prompt",
]
