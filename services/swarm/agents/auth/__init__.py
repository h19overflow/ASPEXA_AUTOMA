"""
Auth Agent module for authorization surface vulnerability scanning.

Purpose: Export Auth agent components
Dependencies: auth_agent.py, auth_prompt.py, auth_probes.py, auth_tools.py
"""
from .auth_agent import AuthAgent
from .auth_probes import AUTH_PROBES, AUTH_PROBES_EXTENDED, get_probes
from .auth_prompt import AUTH_SYSTEM_PROMPT
from .auth_tools import AUTH_TOOLS, analyze_auth_infrastructure, get_auth_probe_list

__all__ = [
    "AuthAgent",
    "AUTH_SYSTEM_PROMPT",
    "AUTH_PROBES",
    "AUTH_PROBES_EXTENDED",
    "get_probes",
    "AUTH_TOOLS",
    "analyze_auth_infrastructure",
    "get_auth_probe_list",
]
