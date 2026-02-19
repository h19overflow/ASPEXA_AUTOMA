"""
Framing strategy definitions and metadata.

Purpose: Defines legitimate-sounding personas and contexts for attack payloads.
Each strategy includes effectiveness ratings per domain and detection risk.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FramingType(str, Enum):
    """Available framing personas."""

    QA_TESTING = "qa_testing"
    COMPLIANCE_AUDIT = "compliance_audit"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    EDUCATIONAL = "educational"
    RESEARCH = "research"


class FramingStrategy(BaseModel):
    """Complete framing strategy definition."""

    type: FramingType
    name: str = Field(..., description="Human-readable strategy name")
    system_context: str = Field(..., description="LLM system prompt addition")
    user_prefix: str = Field(..., description="Payload prefix text")
    user_suffix: str = Field(default="", description="Payload suffix text")

    # Effectiveness ratings (0.0-1.0) per domain
    domain_effectiveness: dict[str, float] = Field(default_factory=dict)

    # Risk assessment
    detection_risk: Literal["low", "medium", "high"] = Field(default="medium")

    @field_validator("domain_effectiveness")
    @classmethod
    def validate_effectiveness(cls, v: dict[str, float]) -> dict[str, float]:
        """Ensure effectiveness scores are 0.0-1.0."""
        for domain, score in v.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(
                    f"Effectiveness score {score} for {domain} must be 0.0-1.0"
                )
        return v

    def get_effectiveness(self, domain: str) -> float:
        """Get effectiveness rating for domain, default 0.5 if unknown."""
        return self.domain_effectiveness.get(domain, 0.5)
