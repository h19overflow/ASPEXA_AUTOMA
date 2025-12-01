"""
Payload effectiveness tracking models.

Purpose: Records which framing/format/tool combinations succeeded for
learning and optimization over time.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from services.snipers.utils.prompt_articulation.models.framing_strategy import FramingType


class EffectivenessRecord(BaseModel):
    """Single attack attempt outcome."""

    # Attack configuration
    framing_type: FramingType
    format_control: str = Field(..., description="Output control phrase used")
    domain: str = Field(..., description="Target domain")
    tool_name: str | None = Field(None, description="Tool targeted if any")

    # Outcome
    success: bool = Field(..., description="Did payload achieve objective")
    score: float = Field(..., ge=0.0, le=1.0, description="Scorer-assigned effectiveness")

    # Context
    payload_preview: str = Field(..., description="First 200 chars of payload")
    defense_triggered: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class EffectivenessSummary(BaseModel):
    """Aggregated statistics for a framing/domain combination."""

    framing_type: FramingType
    domain: str
    total_attempts: int = 0
    successful_attempts: int = 0
    average_score: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts
