"""
Integration models for bypass knowledge hooks.

Purpose: Define data structures for hook inputs and outputs
Role: Type-safe contracts between integration layer and node hooks
Dependencies: Pydantic, HistoricalInsight from query module
"""

from pydantic import BaseModel, Field

from services.snipers.knowledge.models.insight import HistoricalInsight


class HistoryContext(BaseModel):
    """
    Historical context for strategy generation.

    Output from AdaptNodeHook.query_history() - contains
    historical insight plus computed recommendations for the adapter.
    """

    # Core insight from query processor
    insight: HistoricalInsight | None = Field(
        default=None,
        description="Full insight from historical query (None if query failed/disabled)",
    )

    # Computed recommendations
    boost_techniques: list[str] = Field(
        default_factory=list,
        description="Techniques to prioritize (high success rate in similar cases)",
    )
    avoid_techniques: list[str] = Field(
        default_factory=list,
        description="Techniques to deprioritize (low success rate in similar cases)",
    )
    recommended_framing: str = Field(
        default="",
        description="Best framing approach from historical data",
    )
    recommended_converters: list[str] = Field(
        default_factory=list,
        description="Recommended converter chain from historical data",
    )

    # Control flags
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in historical recommendations",
    )
    should_inject: bool = Field(
        default=False,
        description="Whether confidence is high enough to inject into prompts",
    )

    def to_prompt_context(self) -> str:
        """
        Format historical context for injection into strategy prompts.

        Returns:
            Markdown-formatted string describing historical intelligence,
            or empty message if no relevant history found.
        """
        if not self.insight or self.insight.similar_cases_found == 0:
            return "No historical data available for this defense pattern."

        lines = [
            "## Historical Intelligence",
            f"Based on {self.insight.similar_cases_found} similar past episodes:",
            "",
            f"**Likely Defense Mechanism:** {self.insight.dominant_mechanism}",
            f"**Confidence:** {self.confidence:.0%}",
            "",
            "**Recommended Approach:**",
            f"- Technique: {self.insight.recommended_technique}",
            f"- Framing: {self.insight.recommended_framing}",
        ]

        if self.insight.recommended_converters:
            lines.append(f"- Converters: {', '.join(self.insight.recommended_converters)}")

        lines.extend([
            "",
            f"**Key Pattern:** {self.insight.key_pattern}",
        ])

        if self.avoid_techniques:
            lines.extend([
                "",
                f"**Avoid These (Low Success Rate):** {', '.join(self.avoid_techniques)}",
            ])

        return "\n".join(lines)


class CaptureResult(BaseModel):
    """
    Result from episode capture attempt.

    Output from EvaluateNodeHook.maybe_capture() - indicates
    whether an episode was captured and where it was stored.
    """

    captured: bool = Field(
        default=False,
        description="Whether an episode was captured",
    )
    reason: str = Field(
        default="",
        description="Why capture did/didn't happen (threshold, disabled, etc.)",
    )
    episode_id: str | None = Field(
        default=None,
        description="ID of captured episode (if captured)",
    )
    log_path: str = Field(
        default="",
        description="Path to local log file for this capture",
    )
    stored_to_s3: bool = Field(
        default=False,
        description="Whether episode was stored to S3 Vectors",
    )

    def __str__(self) -> str:
        """Human-readable summary of capture result."""
        if not self.captured:
            return f"Not captured: {self.reason}"

        storage_status = "stored to S3" if self.stored_to_s3 else "logged locally only"
        return f"Captured {self.episode_id} ({storage_status})"
