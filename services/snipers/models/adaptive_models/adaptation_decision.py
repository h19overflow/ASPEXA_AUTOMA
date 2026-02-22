"""
Adaptation Decision Model.

Purpose: Complete adaptation strategy for next attack iteration
Role: Structured LLM output with custom framing, converters, and reasoning
Dependencies: pydantic, defense_analysis
"""

from pydantic import BaseModel, Field

from services.snipers.models.adaptive_models.defense_analysis import DefenseAnalysis


class ReconCustomFraming(BaseModel):
    """
    LLM-discovered custom framing based on recon intelligence.

    Simpler structure focused on role/context alignment with target's
    self-description from system prompt leaks.
    """

    role: str = Field(description="Role to frame as (e.g., 'Tech shop customer')")
    context: str = Field(
        description="Context for the role (e.g., 'completing a purchase')"
    )
    justification: str = Field(
        description="Why this framing aligns with target's self-description"
    )


class CustomFraming(BaseModel):
    """
    LLM-generated framing strategy.

    Compatible with PayloadArticulation.execute(custom_framing=...) interface.
    """

    name: str = Field(
        description="Framing persona name, e.g., 'security_auditor'"
    )
    system_context: str = Field(
        description="System context describing the persona and authorization"
    )
    user_prefix: str = Field(
        description="Opening text before the payload"
    )
    user_suffix: str = Field(
        default="",
        description="Closing text after the payload"
    )
    rationale: str = Field(
        description="Why this framing might work against detected defenses"
    )


class AdaptationDecision(BaseModel):
    """
    Complete adaptation strategy for next iteration.

    Returned by StrategyGenerator after LLM analysis of responses and history.
    """

    # Defense analysis
    defense_analysis: DefenseAnalysis = Field(
        description="Analysis of target's defense mechanisms"
    )

    # Framing strategy
    use_custom_framing: bool = Field(
        description="Whether to use LLM-generated custom framing"
    )
    custom_framing: CustomFraming | None = Field(
        default=None,
        description="Custom framing if use_custom_framing is True"
    )
    recon_custom_framing: ReconCustomFraming | None = Field(
        default=None,
        description="Recon-intelligence-based custom framing (role/context alignment)",
    )
    preset_framing: str | None = Field(
        default=None,
        description="Preset framing type if use_custom_framing is False"
    )

    # Converter selection
    converter_chain: list[str] = Field(
        default_factory=list,
        description="Ordered list of converters to apply"
    )
    obfuscation_rationale: str = Field(
        description="Why these converters were selected"
    )

    # Payload guidance
    payload_adjustments: str = Field(
        description="Instructions for payload generation adjustments"
    )
    avoid_terms: list[str] = Field(
        default_factory=list,
        description="Keywords to avoid in payloads"
    )
    emphasize_terms: list[str] = Field(
        default_factory=list,
        description="Keywords to emphasize in payloads"
    )

    # Discovered Parameters
    discovered_parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Any specific validation rules, parameter formats, or IDs leaked by the target (e.g., {'account_format': 'ACC-[0-9]{3}'})."
    )

    # Meta
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in strategy success (0-1)"
    )
    reasoning: str = Field(
        description="Full reasoning chain for the decision"
    )
