"""
Swarm Observability Package.

Purpose: Enhanced streaming, cancellation, and state persistence for Swarm workflows
Dependencies: langgraph, pydantic

This package provides:
- Standardized event types for SSE streaming
- Cancellation and pause/resume support
- Checkpoint configuration for state persistence

Usage:
    from services.swarm.swarm_observability import (
        StreamEvent,
        EventType,
        create_event,
        CancellationManager,
        get_cancellation_manager,
        remove_cancellation_manager,
        get_checkpointer,
    )
"""

from .cancellation import (
    CancellationManager,
    get_active_scan_ids,
    get_cancellation_manager,
    remove_cancellation_manager,
)
from .checkpoint import get_checkpointer
from .events import EventType, StreamEvent, create_event, safe_get_stream_writer

__all__ = [
    # Events
    "StreamEvent",
    "EventType",
    "create_event",
    "safe_get_stream_writer",
    # Cancellation
    "CancellationManager",
    "get_cancellation_manager",
    "remove_cancellation_manager",
    "get_active_scan_ids",
    # Checkpoint
    "get_checkpointer",
]
