"""
Garak-based security scanner with HTTP endpoint support.

Purpose: Core scanning engine - executes probes, collects results
Role: Core scanning engine
Dependencies: garak, libs.connectivity

Package Structure:
- execution/: Core scanning (GarakScanner, probe loading)
- generators/: Target communication (HTTP, WebSocket, rate limiting)
- detection/: Vulnerability detection (detectors, triggers)
"""

# Core scanner
from .execution import GarakScanner, get_scanner

# Models
from .models import ProbeResult

# Generators
from .generators import HTTPGenerator, WebSocketGenerator, RateLimiter

# Detection
from .detection import load_detector, run_detectors_on_attempt, get_detector_triggers

__all__ = [
    # Scanner
    "GarakScanner",
    "get_scanner",
    # Models
    "ProbeResult",
    # Generators
    "HTTPGenerator",
    "WebSocketGenerator",
    "RateLimiter",
    # Detection
    "load_detector",
    "run_detectors_on_attempt",
    "get_detector_triggers",
]
