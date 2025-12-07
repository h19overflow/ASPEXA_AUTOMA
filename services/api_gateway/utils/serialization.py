"""JSON serialization utilities for SSE streaming.

Purpose: Handle datetime and Pydantic model serialization for event streaming
Dependencies: json, datetime, pydantic
"""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel


def _json_default(obj: Any) -> Any:
    """JSON encoder default handler for datetime and Pydantic models."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def serialize_event(event: Any) -> str:
    """
    Serialize event to JSON string, handling datetime and Pydantic models.

    Args:
        event: Event object (dict, Pydantic model, or other JSON-serializable type)

    Returns:
        JSON string representation of the event
    """
    if isinstance(event, BaseModel):
        # Pydantic model - use model_dump_json for proper serialization
        return event.model_dump_json()
    else:
        # Dict or other - use custom encoder for datetime handling
        return json.dumps(event, default=_json_default)
