"""
Defense Analysis Model.

Purpose: Structured analysis of target's defense mechanisms
Role: Captures refusal patterns, blocked keywords, and vulnerability hints
Dependencies: pydantic
"""

from typing import Literal

from pydantic import BaseModel, Field


class DefenseAnalysis(BaseModel):
    """
    Analysis of target's defense mechanisms from response text.

    Used by LLM to understand what blocked the attack and identify weaknesses.
    """

    refusal_type: Literal["hard_block", "soft_decline", "redirect", "partial", "none"] = Field(
        description="Type of refusal detected in response"
    )
    detected_patterns: list[str] = Field(
        default_factory=list,
        description="Defense patterns detected: keyword_filter, intent_detection, policy_citation, etc."
    )
    blocked_keywords: list[str] = Field(
        default_factory=list,
        description="Terms that likely triggered rejection"
    )
    response_tone: str = Field(
        default="neutral",
        description="Tone of response: apologetic, firm, helpful, confused, neutral"
    )
    vulnerability_hints: list[str] = Field(
        default_factory=list,
        description="Signs of partial success or exploitable weakness"
    )
