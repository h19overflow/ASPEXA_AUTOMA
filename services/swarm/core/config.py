"""
Purpose: Probe mappings, defaults, and configurable settings for Swarm scanner
Role: Central configuration for probe selection and scan parameters
Dependencies: enums.py, constants.py
"""

from typing import List

# Re-export enums for backwards compatibility
from services.swarm.core.enums import AgentType, ScanApproach, VulnCategory

# Re-export constants for backwards compatibility
from services.swarm.core.constants import (
    PROBE_MAP,
    PROBE_DESCRIPTIONS,
    PROBE_TO_CATEGORY,
    DEFAULT_PROBES,
    INFRASTRUCTURE_PROBES,
)


def get_probes_for_agent(
    agent_type: str,
    approach: str = ScanApproach.STANDARD,
    infrastructure: dict = None,
    custom_probes: List[str] = None,
) -> List[str]:
    """Get probe list based on agent type, approach, and infrastructure."""
    if custom_probes:
        return [p for p in custom_probes if p in PROBE_MAP]

    agent_enum = AgentType(agent_type) if agent_type in [e.value for e in AgentType] else AgentType.SQL
    approach_enum = ScanApproach(approach) if approach in [e.value for e in ScanApproach] else ScanApproach.STANDARD
    probes = list(DEFAULT_PROBES.get(agent_enum, {}).get(approach_enum, ["promptinj"]))

    if infrastructure:
        # Check all possible infrastructure keys from ReconBlueprint
        # keys: vector_db, model_family, rate_limits
        search_terms = []
        for val in infrastructure.values():
            if val and isinstance(val, str):
                search_terms.append(val.lower())
        
        for key, extra_probes in INFRASTRUCTURE_PROBES.items():
            # If any value in infrastructure contains the key (e.g. "PostgreSQL" contains "postgresql")
            if any(key in term for term in search_terms):
                for p in extra_probes:
                    if p not in probes:
                        probes.append(p)

    return probes


def get_all_probe_names() -> List[str]:
    """Get list of all available probe short names."""
    return list(PROBE_MAP.keys())


def resolve_probe_path(probe_name: str) -> str:
    """
    Resolve probe short name to full module path.

    Args:
        probe_name: Short probe name (e.g., "dan", "promptinj")

    Returns:
        Full module path (e.g., "garak.probes.dan.Dan_11_0")

    Raises:
        ValueError: If probe_name is not in PROBE_MAP and doesn't look like a valid path
    """
    if probe_name in PROBE_MAP:
        return PROBE_MAP[probe_name]

    # If not found, check if it's already a full path
    if "." in probe_name and "garak.probes" in probe_name:
        return probe_name

    # Invalid probe name
    raise ValueError(
        f"Unknown probe: '{probe_name}'. "
        f"Available probes: {', '.join(sorted(PROBE_MAP.keys()))}"
    )


def get_probe_description(probe_name: str) -> str:
    """Get human-readable description for a probe."""
    return PROBE_DESCRIPTIONS.get(probe_name, probe_name)


def get_probe_category(probe_name: str) -> VulnCategory:
    """Get vulnerability category for a probe."""
    return PROBE_TO_CATEGORY.get(probe_name, VulnCategory.JAILBREAK)


def get_agent_probe_pool(
    agent_type: str, 
    approach: str = "standard",
    infrastructure: dict = None
) -> List[str]:
    """Get the probe pool for an agent type and approach."""
    return get_probes_for_agent(agent_type, approach, infrastructure=infrastructure)
