"""
Auth Agent probe configuration.

Purpose: Define available probes for Auth agent
Dependencies: services.swarm.core.constants
Used by: auth_agent.py
"""
from typing import List

from services.swarm.core.constants import DEFAULT_PROBES, PROBE_CATEGORIES
from services.swarm.core.enums import AgentType, ScanApproach

# Core authorization surface probes
AUTH_PROBES: List[str] = [
    "leak",
    "continuation",
    "goodside_tag",
    "donotanswer_infohazard",
]

# Extended probes for thorough scans
AUTH_PROBES_EXTENDED: List[str] = AUTH_PROBES + [
    "goodside_json",
    "glitch",
    "donotanswer_malicious",
    "malware_evasion",
]


def get_probes(approach: str = "standard") -> List[str]:
    """Get probes for given approach.

    Args:
        approach: 'quick', 'standard', or 'thorough'

    Returns:
        List of probe names for Auth agent
    """
    approach_enum = (
        ScanApproach(approach)
        if approach in [e.value for e in ScanApproach]
        else ScanApproach.STANDARD
    )
    return list(DEFAULT_PROBES.get(AgentType.AUTH, {}).get(approach_enum, AUTH_PROBES))


def get_probe_categories() -> str:
    """Get comma-separated probe categories for Auth agent."""
    relevant_categories = ["data_leakage", "harmful_content", "encoding_bypass"]
    return ", ".join(relevant_categories)


def get_available_probes() -> str:
    """Get comma-separated available probes for Auth agent."""
    return ", ".join(AUTH_PROBES_EXTENDED)
