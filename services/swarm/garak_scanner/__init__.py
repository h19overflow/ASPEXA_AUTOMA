"""
Garak-based security scanner with HTTP endpoint support and result parsing.

Purpose: Core scanning engine - executes probes, collects results, parses reports
Role: Core scanning engine
Dependencies: garak, libs.connectivity
"""

from .scanner import GarakScanner, get_scanner
from .models import ProbeResult
from .report_parser import (
    parse_results_to_clusters,
    format_scan_results,
    get_results_summary,
    generate_comprehensive_report_from_results,
)
from libs.connectivity.adapters import GarakHttpGenerator as HttpGenerator

__all__ = [
    "GarakScanner",
    "get_scanner",
    "ProbeResult",
    "parse_results_to_clusters",
    "format_scan_results",
    "get_results_summary",
    "generate_comprehensive_report_from_results",
    "HttpGenerator",
]
