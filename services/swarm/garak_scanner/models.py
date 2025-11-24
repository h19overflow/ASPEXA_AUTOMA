"""
Data models for garak scanner.
"""
from dataclasses import dataclass


@dataclass
class ProbeResult:
    """Result from a single probe execution with detector-based pass/fail."""
    probe_name: str
    probe_description: str
    category: str
    prompt: str
    output: str
    status: str  # 'pass', 'fail', 'error'
    detector_name: str
    detector_score: float
    detection_reason: str
