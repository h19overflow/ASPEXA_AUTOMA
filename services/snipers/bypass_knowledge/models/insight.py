"""
Insight models for query responses.

Defines the output structures for historical knowledge queries,
including technique statistics and synthesized recommendations.
"""

from pydantic import BaseModel, Field


class TechniqueStats(BaseModel):
    """Statistics for a technique across episodes."""

    technique: str = Field(description="Technique name")
    success_count: int = Field(ge=0, description="Number of successful uses")
    total_attempts: int = Field(ge=0, description="Total times attempted")
    success_rate: float = Field(ge=0.0, le=1.0, description="Success rate (0-1)")
    avg_iterations: float = Field(ge=0.0, description="Average iterations to succeed")


class HistoricalInsight(BaseModel):
    """
    Synthesized intelligence from historical episodes.

    This is the output contract for the query processor - it aggregates
    similar episodes into actionable recommendations.
    """

    # === QUERY ===
    query: str = Field(description="Original question asked")
    similar_cases_found: int = Field(ge=0, description="Number of matching episodes")

    # === MECHANISM ANALYSIS ===
    dominant_mechanism: str = Field(
        description="Most common mechanism in matched episodes"
    )
    mechanism_confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in mechanism assessment"
    )

    # === RECOMMENDATIONS ===
    technique_stats: list[TechniqueStats] = Field(
        default_factory=list,
        description="Success rates for each technique",
    )
    recommended_technique: str = Field(
        default="", description="Best technique to try"
    )
    recommended_framing: str = Field(
        default="", description="Best framing approach"
    )
    recommended_converters: list[str] = Field(
        default_factory=list,
        description="Recommended text converters",
    )

    # === PATTERN ===
    key_pattern: str = Field(
        description="Synthesized insight about what works in this situation"
    )

    # === EXAMPLE ===
    representative_episode_id: str = Field(
        default="", description="ID of best matching episode"
    )
    representative_summary: str = Field(
        default="", description="Brief summary of representative episode"
    )

    # === META ===
    confidence: float = Field(
        ge=0.0, le=1.0, description="Overall confidence in this insight"
    )
    reasoning: str = Field(
        default="", description="How this insight was derived"
    )
