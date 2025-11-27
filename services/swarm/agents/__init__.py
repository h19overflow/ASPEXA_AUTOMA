"""
Agent system for intelligent security scanning.

Purpose: LangChain agents for analyzing recon intelligence and executing targeted scans
Role: Coordinates scanning with intelligent decision-making
Dependencies: langchain, langchain_google_genai, scanner, config
"""

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

__all__ = [
    # Planning interface (primary)
    "create_planning_agent",
    "run_planning_agent",

    # Backward compatibility (deprecated)
    "create_scanning_agent",
    "run_scanning_agent",

    # Specialized agents (The Trinity)
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
