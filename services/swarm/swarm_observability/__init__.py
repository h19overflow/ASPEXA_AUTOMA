"""
Swarm Observability Package.

Purpose: Streaming events and cancellation support for Swarm scan phases
Dependencies: pydantic
"""

from .cancellation import (
    CancellationManager,
    get_active_scan_ids,
    get_cancellation_manager,
    remove_cancellation_manager,
)
from .events import EventType, StreamEvent, create_event

__all__ = [
    # Events
    "StreamEvent",
    "EventType",
    "create_event",
    # Cancellation
    "CancellationManager",
    "get_cancellation_manager",
    "remove_cancellation_manager",
    "get_active_scan_ids",
]
