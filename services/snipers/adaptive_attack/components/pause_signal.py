"""Pause signal store for adaptive attack control.

Purpose: In-memory store for pause signals during adaptive attacks
Role: Enables graceful pause/resume of long-running attack streams
Dependencies: None (pure Python, thread-safe)

This module provides a simple way to signal running attacks to pause
after their current iteration completes.
"""
import threading
from typing import Dict, Set

# Thread-safe storage for pause signals
_pause_signals: Set[str] = set()
_lock = threading.Lock()


def request_pause(scan_id: str) -> None:
    """Request a running attack to pause.

    The attack will pause after completing its current iteration.

    Args:
        scan_id: Unique identifier for the running attack
    """
    with _lock:
        _pause_signals.add(scan_id)


def clear_pause(scan_id: str) -> None:
    """Clear the pause signal for an attack.

    Call this when resuming an attack.

    Args:
        scan_id: Unique identifier for the attack
    """
    with _lock:
        _pause_signals.discard(scan_id)


def is_pause_requested(scan_id: str) -> bool:
    """Check if a pause has been requested for an attack.

    Args:
        scan_id: Unique identifier for the attack

    Returns:
        True if pause was requested, False otherwise
    """
    with _lock:
        return scan_id in _pause_signals


def get_paused_attacks() -> Set[str]:
    """Get all attacks that have pause requests.

    Returns:
        Set of scan_ids with pending pause requests
    """
    with _lock:
        return _pause_signals.copy()


def clear_all() -> None:
    """Clear all pause signals (for testing/cleanup)."""
    with _lock:
        _pause_signals.clear()
