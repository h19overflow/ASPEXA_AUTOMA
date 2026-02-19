"""
Structured intelligence models for tool exploitation.

Purpose: Represent discovered tool signatures, parameters, and business rules
from reconnaissance data to enable precise payload targeting.

Dependencies: None (pure data models)
System Role: Data layer for recon-to-payload pipeline
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Parameter definition for discovered tools."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (str, int, float, etc.)")
    required: bool = Field(default=True, description="Whether parameter is required")
    format_constraint: str | None = Field(
        default=None, description="Format pattern (e.g., TXN-XXXXX)"
    )
    validation_pattern: str | None = Field(
        default=None, description="Regex validation pattern"
    )
    default_value: str | None = Field(default=None, description="Default value if any")


class ToolSignature(BaseModel):
    """Complete signature of a discovered tool/function."""

    tool_name: str = Field(..., description="Tool/function name")
    description: str | None = Field(default=None, description="Tool purpose")
    parameters: list[ToolParameter] = Field(
        default_factory=list, description="Tool parameters"
    )
    business_rules: list[str] = Field(
        default_factory=list, description="Business constraints and authorization rules"
    )
    example_calls: list[str] = Field(
        default_factory=list, description="Example invocations"
    )
    authorization_required: bool = Field(
        default=True, description="Whether tool requires authorization"
    )


class ReconIntelligence(BaseModel):
    """Structured reconnaissance intelligence for payload generation."""

    tools: list[ToolSignature] = Field(
        default_factory=list, description="Discovered tool signatures"
    )
    llm_model: str | None = Field(default=None, description="Target LLM model")
    database_type: str | None = Field(default=None, description="Backend database type")
    content_filters: list[str] = Field(
        default_factory=list, description="Detected content filters/defenses"
    )
    system_prompt_leak: str | None = Field(
        default=None,
        description="Leaked system prompt revealing target's identity/purpose",
    )
    target_self_description: str | None = Field(
        default=None,
        description="How the target describes itself (e.g., 'Tech shop chatbot')",
    )
    raw_intelligence: dict = Field(
        default_factory=dict, description="Original recon data"
    )
