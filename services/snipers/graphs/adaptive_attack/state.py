"""
Adaptive Attack State Definition.

Purpose: TypedDict state for LangGraph adaptive attack loop
Role: Tracks attack parameters, results, and adaptation decisions
Dependencies: Phase result types, scoring models

State flows through:
START → articulate → convert → execute → evaluate → [adapt|END]
                                              ↑         ↓
                                              └─────────┘
"""

from typing import Any, Literal, TypedDict
from dataclasses import dataclass, field

from services.snipers.models import Phase1Result, Phase2Result, Phase3Result
from services.snipers.graphs.adaptive_attack.models.chain_discovery import (
    ChainDiscoveryContext,
    ChainDiscoveryDecision,
    ChainSelectionResult,
)


# Failure causes that trigger different adaptations
FailureCause = Literal[
    "no_impact",       # Attack had no effect - try different approach
    "blocked",         # Attack was blocked - escalate obfuscation
    "partial_success", # Some effect - refine current approach
    "rate_limited",    # Too many requests - slow down
    "error",           # Technical error - retry same approach
]

# Adaptation actions the system can take
AdaptationAction = Literal[
    "change_framing",          # Try different framing strategy
    "change_converters",       # Try different converter chain
    "escalate_obfuscation",    # Add more converters
    "regenerate_payloads",     # Generate new payloads
    "increase_payload_count",  # Generate more payloads
    "reduce_concurrency",      # Slow down requests
    "retry_same",              # Retry with same parameters
    "llm_strategy_generated",  # LLM generated custom strategy
]

# Available scorer types for success criteria
ScorerType = Literal[
    "jailbreak",
    "prompt_leak",
    "data_leak",
    "tool_abuse",
    "pii_exposure",
]

# All available scorers
ALL_SCORERS: list[ScorerType] = [
    "jailbreak",
    "prompt_leak",
    "data_leak",
    "tool_abuse",
    "pii_exposure",
]


class AdaptiveAttackState(TypedDict, total=False):
    """
    LangGraph state for adaptive attack loop.

    Tracks all parameters, results, and adaptation decisions
    across multiple attack iterations.
    """

    # === Campaign Configuration (immutable) ===
    campaign_id: str
    target_url: str
    max_iterations: int

    # === Success Criteria ===
    success_scorers: list[str]  # Scorers that must succeed (e.g., ["jailbreak"])
    success_threshold: float     # Minimum confidence for success (0.0-1.0)

    # === Current Iteration Parameters ===
    iteration: int
    payload_count: int
    framing_types: list[str] | None
    converter_names: list[str] | None
    max_concurrent: int

    # === Phase Results (updated each iteration) ===
    phase1_result: Phase1Result | None
    phase2_result: Phase2Result | None
    phase3_result: Phase3Result | None

    # === Attack Outcome ===
    is_successful: bool
    overall_severity: str
    total_score: float
    failure_cause: FailureCause | None

    # === Adaptation State ===
    adaptation_actions: list[AdaptationAction]
    tried_framings: list[str]
    tried_converters: list[list[str]]
    best_score: float
    best_iteration: int

    # === History (for learning) ===
    iteration_history: list[dict[str, Any]]

    # === Response Data (for LLM analysis) ===
    target_responses: list[str]  # Raw response texts from Phase 3

    # === Custom Framing (from LLM) ===
    custom_framing: dict[str, str] | None  # LLM-generated framing dict
    recon_custom_framing: dict[str, str] | None  # Recon-intelligence-based framing dict
    payload_guidance: str | None  # Instructions for payload articulation

    # === Adaptation Reasoning ===
    adaptation_reasoning: str  # LLM's reasoning chain
    defense_analysis: dict[str, Any]  # Parsed defense signals

    # === Chain Discovery (NEW) ===
    chain_discovery_context: ChainDiscoveryContext | None  # Extracted failure intelligence
    chain_discovery_decision: ChainDiscoveryDecision | None  # LLM chain candidates
    chain_selection_result: ChainSelectionResult | None  # Full selection observability

    # === Control Flow ===
    next_node: str | None
    error: str | None
    completed: bool


# Available framing types for rotation
FRAMING_TYPES = [
    "qa_testing",
    "compliance_audit",
    "documentation",
    "debugging",
    "educational",
    "research",
]

# Available converter chains for rotation (ordered by obfuscation level)
CONVERTER_CHAINS = [
    ["homoglyph"],
    ["unicode_substitution"],
    ["leetspeak"],
    ["base64"],
    ["homoglyph", "unicode_substitution"],
    ["leetspeak", "character_space"],
    ["base64", "rot13"],
    ["homoglyph", "leetspeak", "unicode_substitution"],
]


def create_initial_state(
    campaign_id: str,
    target_url: str,
    max_iterations: int = 5,
    payload_count: int = 2,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    max_concurrent: int = 3,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
) -> AdaptiveAttackState:
    """
    Create initial state for adaptive attack loop.

    Args:
        campaign_id: Campaign ID to load intelligence
        target_url: Target URL to attack
        max_iterations: Maximum adaptation iterations
        payload_count: Initial number of payloads
        framing_types: Initial framing types (None = auto)
        converter_names: Initial converters (None = auto from Phase 1)
        max_concurrent: Max concurrent requests
        success_scorers: Scorers that must succeed for attack to be considered successful
            Options: jailbreak, prompt_leak, data_leak, tool_abuse, pii_exposure
            Default: None (any scorer success counts)
        success_threshold: Minimum confidence threshold (0.0-1.0) for scorer success

    Returns:
        Initial AdaptiveAttackState
    """
    return AdaptiveAttackState(
        # Campaign config
        campaign_id=campaign_id,
        target_url=target_url,
        max_iterations=max_iterations,

        # Success criteria
        success_scorers=success_scorers or [],  # Empty = any scorer success
        success_threshold=success_threshold,

        # Current parameters
        iteration=0,
        payload_count=payload_count,
        framing_types=framing_types,
        converter_names=converter_names,
        max_concurrent=max_concurrent,

        # Phase results
        phase1_result=None,
        phase2_result=None,
        phase3_result=None,

        # Attack outcome
        is_successful=False,
        overall_severity="none",
        total_score=0.0,
        failure_cause=None,

        # Adaptation state
        adaptation_actions=[],
        tried_framings=[],
        tried_converters=[],
        best_score=0.0,
        best_iteration=0,

        # History
        iteration_history=[],

        # Response data (for LLM analysis)
        target_responses=[],

        # Custom framing (from LLM)
        custom_framing=None,
        recon_custom_framing=None,
        payload_guidance=None,

        # Adaptation reasoning
        adaptation_reasoning="",
        defense_analysis={},

        # Chain discovery
        chain_discovery_context=None,
        chain_discovery_decision=None,
        chain_selection_result=None,

        # Control flow
        next_node="articulate",
        error=None,
        completed=False,
    )
