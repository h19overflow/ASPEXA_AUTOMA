"""
Detection package - vulnerability detection logic.

Purpose: Load Garak detectors and evaluate probe results
Dependencies: garak.attempt
"""
from .detectors import load_detector, run_detectors_on_attempt
from .triggers import get_detector_triggers

__all__ = [
    "load_detector",
    "run_detectors_on_attempt",
    "get_detector_triggers",
]
