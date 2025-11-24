"""Cartographer agent structured output schema for reconnaissance turns."""
from typing import List, Optional
from pydantic import BaseModel, Field


class Deduction(BaseModel):
    """A deduction made from observations."""
    category: str = Field(
        ...,
        description="Category of deduction (system_prompt, tools, infrastructure, auth)"
    )
    finding: str = Field(..., description="What was deduced")
    confidence: str = Field(
        default="medium",
        description="Confidence level: low, medium, high"
    )


class ReconTurn(BaseModel):
    """Structured output for a single reconnaissance turn."""
    deductions: List[Deduction] = Field(
        default_factory=list,
        description="Deductions made from the target response"
    )
    next_question: str = Field(
        ...,
        description="The next strategic question to ask the target"
    )
    rationale: str = Field(
        ...,
        description="Why this question targets remaining gaps"
    )
    should_continue: bool = Field(
        default=True,
        description="Whether reconnaissance should continue"
    )
    stop_reason: Optional[str] = Field(
        default=None,
        description="Reason for stopping if should_continue is False"
    )
