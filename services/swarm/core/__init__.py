"""Core Swarm service modules: configuration, schemas, utilities, and consumers."""

from .config import (
    AgentType,
    ScanApproach,
    VulnCategory,
    PROBE_MAP,
    PROBE_DESCRIPTIONS,
    get_probes_for_agent,
    get_all_probe_names,
    resolve_probe_path,
    get_probe_description,
    get_probe_category,
)

from .schema import (
    ScanConfig,
    AgentScanResult,
)

from .utils import (
    StructuredFormatter,
    log_scan_start,
    log_scan_complete,
    log_scan_error,
    log_performance_metric,
    time_function,
)

__all__ = [
    # Config
    "AgentType",
    "ScanApproach",
    "VulnCategory",
    "PROBE_MAP",
    "PROBE_DESCRIPTIONS",
    "get_probes_for_agent",
    "get_all_probe_names",
    "resolve_probe_path",
    "get_probe_description",
    "get_probe_category",
    # Schema
    "ScanConfig",
    "AgentScanResult",
    # Utils
    "StructuredFormatter",
    "log_scan_start",
    "log_scan_complete",
    "log_scan_error",
    "log_performance_metric",
    "time_function",
]

