"""
Garak-based security scanner with HTTP endpoint support and result parsing.

Purpose: Core scanning engine - executes probes, collects results, parses reports
Role: Core scanning engine
Dependencies: garak, libs.connectivity

Package Structure:
- execution/: Core scanning (GarakScanner, probe loading)
- generators/: Target communication (HTTP, WebSocket, rate limiting)
- detection/: Vulnerability detection (detectors, triggers)
- reporting/: Result formatting (reports, vulnerability clusters)
"""

# Core scanner - from new package structure
from .execution import GarakScanner, get_scanner, load_probe, get_probe_prompts

# Models stay at root
from .models import ProbeResult

# Reporting - from new package
from .reporting import (
    parse_results_to_clusters,
    format_scan_results,
    get_results_summary,
    generate_comprehensive_report_from_results,
    get_category_for_probe,
    get_severity,
)

# Generators - from new package
from .generators import HTTPGenerator, WebSocketGenerator, RateLimiter

# Detection - from new package
from .detection import load_detector, run_detectors_on_attempt, get_detector_triggers

# Backward compat alias
HttpGenerator = HTTPGenerator

__all__ = [
    # Scanner
    "GarakScanner",
    "get_scanner",
    "load_probe",
    "get_probe_prompts",
    # Models
    "ProbeResult",
    # Reporting
    "parse_results_to_clusters",
    "format_scan_results",
    "get_results_summary",
    "generate_comprehensive_report_from_results",
    "get_category_for_probe",
    "get_severity",
    # Generators
    "HTTPGenerator",
    "HttpGenerator",  # Backward compat
    "WebSocketGenerator",
    "RateLimiter",
    # Detection
    "load_detector",
    "run_detectors_on_attempt",
    "get_detector_triggers",
]
