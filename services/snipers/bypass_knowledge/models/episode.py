"""
Episode models for bypass knowledge storage.

Defines the core data structures for capturing successful bypass attempts,
including defense fingerprints, investigation traces, and solutions.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class FailureDepth(str, Enum):
    """How quickly the defense blocked the attempt."""

    IMMEDIATE = "immediate_block"  # <100ms, no processing
    PARTIAL = "partial_then_refuse"  # Started complying, then stopped
    DELAYED = "delayed_block"  # Processed, then refused
    TIMEOUT = "timeout"  # No response


class Hypothesis(BaseModel):
    """A hypothesis about the defense mechanism."""

    mechanism_type: str = Field(
        description="Type of mechanism: semantic_classifier, keyword_filter, permission_check"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this hypothesis")
    evidence: str = Field(description="What observation led to this hypothesis")


class ProbeResult(BaseModel):
    """Result of a diagnostic probe sent to fingerprint the defense."""

    probe_type: str = Field(description="Type: encoding, authority_frame, synonym")
    probe_description: str = Field(description="Brief description of what was tested")
    result: str = Field(description="Outcome: blocked, partial, success")
    latency_ms: int = Field(ge=0, description="Response time (helps identify mechanism)")
    inference: str = Field(description="What we learned from this probe")


class BypassEpisode(BaseModel):
    """
    Complete record of a successful bypass for learning.

    Captures the full trajectory from initial block to successful bypass,
    including the defense fingerprint, investigation process, and solution.
    """

    # === IDENTITY ===
    episode_id: str = Field(description="UUID for this episode")
    campaign_id: str = Field(description="Parent campaign identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # === DEFENSE FINGERPRINT (Primary Index) ===
    defense_response: str = Field(description="Raw text of blocking response")
    defense_signals: list[str] = Field(
        default_factory=list,
        description="Detected signals: policy_citation, ethical_refusal, etc.",
    )
    failed_techniques: list[str] = Field(
        default_factory=list,
        description="Techniques that didn't work: encoding, direct_request, etc.",
    )
    failure_depths: dict[str, FailureDepth] = Field(
        default_factory=dict,
        description="How each failed technique was blocked",
    )

    # === INVESTIGATION ===
    hypotheses: list[Hypothesis] = Field(
        default_factory=list,
        description="Hypotheses formed about the defense mechanism",
    )
    probes: list[ProbeResult] = Field(
        default_factory=list,
        description="Diagnostic probes executed",
    )
    mechanism_conclusion: str = Field(
        description="Final assessment: e.g., 'Hybrid: semantic classifier + keyword filter'"
    )

    # === SOLUTION ===
    successful_technique: str = Field(
        description="What worked: verification_reversal, authority_framing, etc."
    )
    successful_framing: str = Field(
        description="Framing used: compliance_audit, qa_testing, etc."
    )
    successful_converters: list[str] = Field(
        default_factory=list,
        description="Text converters applied: homoglyph, leetspeak, etc.",
    )
    successful_prompt: str = Field(description="The actual winning prompt")
    jailbreak_score: float = Field(
        ge=0.0, le=1.0, description="Success score from evaluator"
    )

    # === REASONING (LLM-generated post-hoc) ===
    why_it_worked: str = Field(description="Explanation of why the bypass succeeded")
    key_insight: str = Field(
        description="Transferable learning for similar situations"
    )

    # === CONTEXT ===
    target_domain: str = Field(
        description="Domain: finance, customer_service, general, etc."
    )
    target_description: str = Field(
        default="", description="From recon intelligence"
    )
    objective_type: str = Field(
        description="Type: data_extraction, tool_abuse, jailbreak, etc."
    )

    # === METADATA ===
    iteration_count: int = Field(description="How many iterations to succeed")
    total_probes: int = Field(default=0, description="Total probes executed")
    execution_time_ms: int = Field(default=0, description="Total execution time")
