"""
Contextual information for intelligent payload generation.

Purpose: Encapsulates target intelligence, attack history, and objectives
to enable context-aware prompt crafting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


class TargetInfo(BaseModel):
    """Target system characteristics from reconnaissance."""

    domain: str = Field(..., description="Target application domain")
    tools: list[str] = Field(default_factory=list, description="Available tools/functions")
    infrastructure: dict[str, Any] = Field(
        default_factory=dict, description="Tech stack details"
    )
    model_name: str | None = Field(None, description="LLM model if detected")


class AttackHistory(BaseModel):
    """Historical attack attempt patterns."""

    failed_approaches: list[str] = Field(
        default_factory=list, description="Unsuccessful strategies"
    )
    successful_patterns: list[str] = Field(
        default_factory=list, description="Effective patterns"
    )
    blocked_keywords: set[str] = Field(
        default_factory=set, description="Detected defense triggers"
    )


@dataclass
class PayloadContext:
    """Complete context for payload generation.

    Aggregates target intelligence, attack history, and current objective
    to inform framing strategy selection and prompt crafting.
    """

    target: TargetInfo
    history: AttackHistory
    observed_defenses: list[str] = field(default_factory=list)
    objective: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize for LLM prompt injection."""
        return {
            "domain": self.target.domain,
            "tools": self.target.tools,
            "failed_approaches": self.history.failed_approaches,
            "successful_patterns": self.history.successful_patterns,
            "objective": self.objective,
        }
