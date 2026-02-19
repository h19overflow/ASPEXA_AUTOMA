"""
Adaptive attack components.

Pause signal for controlling running attacks.
"""

from services.snipers.core.components.pause_signal import (
    request_pause,
    clear_pause,
    is_pause_requested,
)

__all__ = [
    "request_pause",
    "clear_pause",
    "is_pause_requested",
]
