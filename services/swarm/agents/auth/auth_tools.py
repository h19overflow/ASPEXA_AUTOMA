"""
Auth Agent LangChain tools.

Purpose: Define tools for authorization surface analysis
Dependencies: langchain.tools
Used by: auth_agent.py
"""
import json
from typing import Any, Dict

from langchain.tools import tool

from .auth_probes import get_probes


@tool
def analyze_auth_infrastructure(infrastructure: Dict[str, Any]) -> str:
    """Analyze target infrastructure for authorization attack vectors.

    Args:
        infrastructure: Dict with auth_type, user_roles, etc.

    Returns:
        Analysis summary with recommended focus areas
    """
    auth_type = infrastructure.get("auth_type", "unknown")
    user_roles = infrastructure.get("user_roles", [])
    has_rbac = infrastructure.get("has_rbac", False)

    findings = []
    if auth_type.lower() in ["jwt", "oauth", "bearer"]:
        findings.append(f"Token-based auth ({auth_type}) - test token manipulation")
    if len(user_roles) > 1:
        findings.append(f"Multiple roles ({len(user_roles)}) - test role escalation")
    if has_rbac:
        findings.append("RBAC detected - test permission boundary bypass")

    return " | ".join(findings) if findings else "Basic auth profile - test standard leakage probes"


@tool
def get_auth_probe_list(approach: str = "standard") -> str:
    """Get available probes for authorization surface scanning.

    Args:
        approach: Scan intensity ('quick', 'standard', 'thorough')

    Returns:
        JSON list of available probes
    """
    probes = get_probes(approach)
    return json.dumps({"probes": probes, "approach": approach})


# Export all tools for agent consumption
AUTH_TOOLS = [analyze_auth_infrastructure, get_auth_probe_list]
