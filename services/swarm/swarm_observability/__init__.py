"""
Swarm Observability Package.

Purpose: Streaming events for Swarm scan phases
Dependencies: pydantic
"""

from .events import EventType, StreamEvent

__all__ = [
    # Events
    "StreamEvent",
    "EventType",
]
