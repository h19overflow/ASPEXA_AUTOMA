"""
Standardized event types for Swarm observability streaming.

Purpose: Define event types and models for SSE streaming from Swarm workflows
Dependencies: pydantic, datetime, enum, langgraph

This module provides:
- EventType enum for categorizing stream events
- StreamEvent model for structured event data
- Factory function for creating events with proper defaults
- Safe wrapper for get_stream_writer that handles test contexts
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types for Swarm workflow observability."""

    # Lifecycle events
    SCAN_STARTED = "scan_started"
    SCAN_PAUSED = "scan_paused"
    SCAN_RESUMED = "scan_resumed"
    SCAN_CANCELLED = "scan_cancelled"
    SCAN_COMPLETE = "scan_complete"
    SCAN_ERROR = "scan_error"

    # Node events
    NODE_ENTER = "node_enter"
    NODE_PROGRESS = "node_progress"
    NODE_EXIT = "node_exit"

    # Planning events
    PLAN_START = "plan_start"
    PLAN_COMPLETE = "plan_complete"

    # Execution events
    PROBE_START = "probe_start"
    PROBE_RESULT = "probe_result"
    PROBE_COMPLETE = "probe_complete"

    # Agent events
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"

    # System events
    LOG = "log"
    HEARTBEAT = "heartbeat"


class StreamEvent(BaseModel):
    """
    Structured event for SSE streaming.

    Args:
        type: Event category from EventType enum
        timestamp: When the event occurred (auto-generated if not provided)
        node: Current graph node name (optional)
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
    """
    Factory function to create StreamEvent instances.

    Args:
        event_type: The type of event to create
        node: Current graph node name
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


def _noop_writer(event: Dict[str, Any]) -> None:
    """No-op writer for use outside of LangGraph context."""
    pass


def safe_get_stream_writer() -> Callable[[Dict[str, Any]], None]:
    """
    Safely get the LangGraph stream writer, or return a no-op if outside context.

    This wrapper handles the RuntimeError that occurs when get_stream_writer()
    is called outside of a LangGraph runnable context (e.g., in unit tests).

    Returns:
        StreamWriter callable if in LangGraph context, otherwise a no-op function
    """
    try:
        from langgraph.config import get_stream_writer
        return get_stream_writer()
    except RuntimeError:
        # Outside of LangGraph runnable context (e.g., unit tests)
        logger.debug("get_stream_writer called outside LangGraph context, using no-op")
        return _noop_writer
    except ImportError:
        # LangGraph not installed
        logger.debug("LangGraph not installed, using no-op writer")
        return _noop_writer
