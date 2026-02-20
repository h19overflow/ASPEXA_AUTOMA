"""
Standardized event types for Swarm observability streaming.

Purpose: Define event types and models for SSE streaming from Swarm workflows
Dependencies: pydantic, datetime, enum
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types for Swarm observability streaming."""

    # Lifecycle events
    SCAN_STARTED = "scan_started"
    SCAN_CANCELLED = "scan_cancelled"
    SCAN_COMPLETE = "scan_complete"
    SCAN_ERROR = "scan_error"

    # Phase events
    NODE_ENTER = "node_enter"
    NODE_EXIT = "node_exit"

    # Planning events
    PLAN_START = "plan_start"
    PLAN_COMPLETE = "plan_complete"

    # Execution events
    PROBE_START = "probe_start"
    PROBE_RESULT = "probe_result"
    PROBE_COMPLETE = "probe_complete"

    # Agent events
    AGENT_COMPLETE = "agent_complete"


class StreamEvent(BaseModel):
    """Structured event for SSE streaming.

    Args:
        type: Event category from EventType enum
        timestamp: When the event occurred (auto-generated if not provided)
        node: Current phase name (optional)
        agent: Agent identifier (optional)
        message: Human-readable event description (optional)
        data: Additional structured data (optional)
        progress: Progress percentage 0.0-1.0 (optional)
    """

    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    node: Optional[str] = None
    agent: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    model_config = {"use_enum_values": True}


def create_event(
    event_type: EventType,
    *,
    node: Optional[str] = None,
    agent: Optional[str] = None,
    message: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    progress: Optional[float] = None,
) -> StreamEvent:
    """Factory function to create StreamEvent instances.

    Args:
        event_type: The type of event to create
        node: Current phase name
        agent: Agent identifier
        message: Human-readable description
        data: Additional structured data
        progress: Progress percentage (0.0-1.0)

    Returns:
        StreamEvent instance with timestamp auto-populated
    """
    return StreamEvent(
        type=event_type,
        node=node,
        agent=agent,
        message=message,
        data=data,
        progress=progress,
    )
