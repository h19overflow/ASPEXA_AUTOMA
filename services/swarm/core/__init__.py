"""Core Swarm service modules: configuration, schemas, and enums."""

from .config import (
    AgentType,
    ScanApproach,
    VulnCategory,
    PROBE_MAP,
    PROBE_DESCRIPTIONS,
    get_probes_for_category,
    get_all_probe_names,
    resolve_probe_path,
    get_probe_description,
    get_probe_category,
)

from .schema import (
    ScanConfig,
    ScanPlan,
    ScanState,
    AgentResult,
)

__all__ = [
    # Config
    "AgentType",
    "ScanApproach",
    "VulnCategory",
    "PROBE_MAP",
    "PROBE_DESCRIPTIONS",
    "get_probes_for_category",
    "get_all_probe_names",
    "resolve_probe_path",
    "get_probe_description",
    "get_probe_category",
    # Schema
    "ScanConfig",
    "ScanPlan",
    "ScanState",
    "AgentResult",
]
