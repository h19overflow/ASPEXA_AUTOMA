"""
Jailbreak Agent probe configuration.

Purpose: Define available probes for Jailbreak agent
Dependencies: services.swarm.core.constants
Used by: jailbreak_agent.py
"""
from typing import List

from services.swarm.core.constants import DEFAULT_PROBES, PROBE_CATEGORIES
from services.swarm.core.enums import AgentType, ScanApproach

# Core jailbreak/prompt injection probes
JAILBREAK_PROBES: List[str] = [
    "dan",
    "promptinj",
    "encoding",
    "grandma",
    "profanity",
]

# Extended probes for thorough scans
JAILBREAK_PROBES_EXTENDED: List[str] = JAILBREAK_PROBES + [
    "dan10",
    "danwild",
    "promptinj_kill",
    "encoding_unicode",
    "slur",
    "donotanswer_discrim",
    "malware_toplevel",
]


def get_probes(approach: str = "standard") -> List[str]:
    """Get probes for given approach.

    Args:
        approach: 'quick', 'standard', or 'thorough'

    Returns:
        List of probe names for Jailbreak agent
    """
    approach_enum = (
        ScanApproach(approach)
        if approach in [e.value for e in ScanApproach]
        else ScanApproach.STANDARD
    )
    return list(DEFAULT_PROBES.get(AgentType.JAILBREAK, {}).get(approach_enum, JAILBREAK_PROBES))


def get_probe_categories() -> str:
    """Get comma-separated probe categories for Jailbreak agent."""
    relevant_categories = ["jailbreak", "prompt_injection", "encoding_bypass", "toxicity"]
    return ", ".join(relevant_categories)


def get_available_probes() -> str:
    """Get comma-separated available probes for Jailbreak agent."""
    return ", ".join(JAILBREAK_PROBES_EXTENDED)
