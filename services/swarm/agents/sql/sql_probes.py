"""
SQL Agent probe configuration.

Purpose: Define available probes for SQL agent
Dependencies: services.swarm.core.constants
Used by: sql_agent.py
"""
from typing import List

from services.swarm.core.constants import DEFAULT_PROBES, PROBE_CATEGORIES
from services.swarm.core.enums import AgentType, ScanApproach

# Core SQL/data surface probes
SQL_PROBES: List[str] = [
    "promptinj",
    "encoding",
    "goodside_json",
    "pkg_python",
]

# Extended probes for thorough scans
SQL_PROBES_EXTENDED: List[str] = SQL_PROBES + [
    "promptinj_long",
    "encoding_hex",
    "goodside_tag",
    "pkg_js",
    "malware_subfunc",
    "donotanswer_malicious",
]


def get_probes(approach: str = "standard") -> List[str]:
    """Get probes for given approach.

    Args:
        approach: 'quick', 'standard', or 'thorough'

    Returns:
        List of probe names for SQL agent
    """
    approach_enum = (
        ScanApproach(approach)
        if approach in [e.value for e in ScanApproach]
        else ScanApproach.STANDARD
    )
    return list(DEFAULT_PROBES.get(AgentType.SQL, {}).get(approach_enum, SQL_PROBES))


def get_probe_categories() -> str:
    """Get comma-separated probe categories for SQL agent."""
    relevant_categories = ["prompt_injection", "encoding_bypass", "data_leakage", "package_hallucination"]
    return ", ".join(relevant_categories)


def get_available_probes() -> str:
    """Get comma-separated available probes for SQL agent."""
    return ", ".join(SQL_PROBES_EXTENDED)
