"""
Failure Analysis Models.

Purpose: Pydantic models for LLM-powered failure analysis decisions
Role: Define structured schemas for agentic failure analysis output
Dependencies: pydantic
"""

from pydantic import BaseModel, Field


class DefenseSignal(BaseModel):
    """
    Rich defense signal with semantic understanding.

    Provides detailed information about a detected defense mechanism
    beyond simple keyword matching.
    """

    defense_type: str = Field(
        description="Category of defense (keyword_filter, pattern_matching, content_filter, etc.)"
    )
    evidence: str = Field(
        description="Specific text or pattern that triggered this detection"
    )
    severity: str = Field(
        description="How strongly this defense blocked the attack (low, medium, high)"
    )
    bypass_difficulty: str = Field(
        description="Estimated difficulty to bypass (easy, moderate, hard)"
    )


class FailureAnalysisDecision(BaseModel):
    """
    LLM-structured analysis of attack failure.

    Provides semantic understanding of why an attack failed and
    actionable guidance for the next iteration.
    """

    # Defense Understanding
    detected_defenses: list[DefenseSignal] = Field(
        default_factory=list,
        description="Rich defense objects with evidence and severity"
    )
    defense_reasoning: str = Field(
        description="Why these defenses triggered - semantic explanation"
    )
    defense_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in defense detection accuracy (0-1)"
    )

    # Root Cause Analysis
    primary_failure_cause: str = Field(
        description="Main reason for failure with semantic context"
    )
    contributing_factors: list[str] = Field(
        default_factory=list,
        description="Secondary causes that contributed to failure"
    )
    failure_chain_of_events: str = Field(
        description="How the failure unfolded step-by-step"
    )

    # Iteration Context
    pattern_across_iterations: str = Field(
        description="What pattern emerges from the attack history"
    )
    defense_adaptation_observed: str = Field(
        description="Is the target learning/adapting? How?"
    )
    exploitation_opportunity: str = Field(
        description="Where is the gap in defenses? What partial success occurred?"
    )

    # Actionable Guidance
    recommended_approach: str = Field(
        description="High-level strategy for next iteration"
    )
    specific_recommendations: list[str] = Field(
        default_factory=list,
        description="Concrete next steps to try"
    )
    avoid_strategies: list[str] = Field(
        default_factory=list,
        description="What NOT to do based on analysis"
    )

    # Meta
    analysis_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in this analysis (0-1)"
    )
    reasoning_trace: str = Field(
        description="Show your work - reasoning chain for transparency"
    )
