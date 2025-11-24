"""
Agent system for intelligent security scanning.

Purpose: LangChain agents for analyzing recon intelligence and executing targeted scans
Role: Coordinates scanning with intelligent decision-making
Dependencies: langchain, langchain_google_genai, scanner, config
"""

from .base import create_scanning_agent, run_scanning_agent
from .trinity import (
    run_sql_agent,
    create_sql_agent,
    run_auth_agent,
    create_auth_agent,
    run_jailbreak_agent,
    create_jailbreak_agent,
)
from .tools import AGENT_TOOLS, analyze_target, execute_scan, get_available_probes
from .prompts import SYSTEM_PROMPTS, get_system_prompt
from .utils import (
    build_scan_message,
    validate_agent_type,
    parse_scan_result,
    format_vulnerability_summary,
)

__all__ = [
    # Base functionality
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
    "AGENT_TOOLS",
    "analyze_target",
    "execute_scan",
    "get_available_probes",
    
    # Prompts
    "SYSTEM_PROMPTS",
    "get_system_prompt",
    
    # Utils
    "build_scan_message",
    "validate_agent_type",
    "parse_scan_result",
    "format_vulnerability_summary",
]
