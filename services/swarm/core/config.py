"""
Purpose: Probe mappings, defaults, and configurable settings for Swarm scanner
Role: Central configuration for probe selection and scan parameters
Dependencies: enums.py, constants.py
"""

from typing import List

from services.swarm.core.enums import AgentType, ScanApproach, VulnCategory
from services.swarm.core.constants import (
    PROBE_MAP,
    PROBE_DESCRIPTIONS,
    PROBE_TO_CATEGORY,
    DEFAULT_PROBES,
)


def get_probes_for_category(
    category: str,
    approach: str = ScanApproach.STANDARD,
    custom_probes: List[str] = None,
) -> List[str]:
    """Get probe list for a scan category and approach from DEFAULT_PROBES."""
    if custom_probes:
        return [p for p in custom_probes if p in PROBE_MAP]

    category_enum = AgentType(category) if category in [e.value for e in AgentType] else AgentType.SQL
    approach_enum = ScanApproach(approach) if approach in [e.value for e in ScanApproach] else ScanApproach.STANDARD
    return list(DEFAULT_PROBES.get(category_enum, {}).get(approach_enum, ["promptinj"]))


def get_all_probe_names() -> List[str]:
    """Get list of all available probe short names."""
    return list(PROBE_MAP.keys())


def resolve_probe_path(probe_name: str) -> str:
    """Resolve probe short name to full garak module path. Raises ValueError if unknown."""
    if probe_name in PROBE_MAP:
        return PROBE_MAP[probe_name]

    if "." in probe_name and "garak.probes" in probe_name:
        return probe_name

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


