"""Streaming event models."""
from datetime import datetime
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


class AttackEvent(BaseModel):
    """SSE event emitted during attack execution."""
    type: Literal[
        "started",
        "plan",
        "approval_required",
        "payload",
        "turn",
        "response",
        "result",
        "score",
        "error",
        "complete"
    ]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any] = Field(default_factory=dict)
