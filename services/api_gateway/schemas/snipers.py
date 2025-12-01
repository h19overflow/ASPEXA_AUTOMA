"""
Snipers Attack Schemas.

Purpose: Pydantic models for snipers attack phase API requests/responses
Role: Validate input and serialize output for composable attack endpoints
Dependencies: Pydantic V2
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class FramingType(str, Enum):
    """Available framing strategies for payload articulation."""
    QA_TESTING = "qa_testing"
    COMPLIANCE_AUDIT = "compliance_audit"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    EDUCATIONAL = "educational"
    RESEARCH = "research"


class ScorerType(str, Enum):
    """Available scorers for attack success evaluation."""
    JAILBREAK = "jailbreak"
    PROMPT_LEAK = "prompt_leak"
    DATA_LEAK = "data_leak"
    TOOL_ABUSE = "tool_abuse"
    PII_EXPOSURE = "pii_exposure"


# =============================================================================
# Phase 1: Payload Articulation
# =============================================================================

class CustomFraming(BaseModel):
    """Custom framing strategy for payload articulation."""
    name: str = Field(..., description="Framing strategy name")
    system_context: str = Field(..., description="System context for the framing")
    user_prefix: str = Field("", description="Prefix for user message")
    user_suffix: str = Field("", description="Suffix for user message")


class Phase1Request(BaseModel):
    """Request for Phase 1: Payload Articulation."""
    campaign_id: str = Field(..., description="Campaign ID to load intelligence from S3")
    payload_count: int = Field(
        default=3,
        ge=1,
        le=6,
        description="Number of payloads to generate (1-6)"
    )
    framing_types: Optional[list[FramingType]] = Field(
        None,
        description="Specific framing types to use (None = auto-select)"
    )
    custom_framing: Optional[CustomFraming] = Field(
        None,
        description="Custom framing strategy (overrides framing_types)"
    )


class ConverterChainResponse(BaseModel):
    """Converter chain selection result."""
    chain_id: str = Field(..., description="Unique chain identifier")
    converter_names: list[str] = Field(..., description="Ordered list of converter names")
    defense_patterns: list[str] = Field(
        default_factory=list,
        description="Defense patterns this chain targets"
    )


class Phase1Response(BaseModel):
    """Response from Phase 1: Payload Articulation."""
    campaign_id: str
    selected_chain: Optional[ConverterChainResponse] = None
    articulated_payloads: list[str]
    framing_type: str
    framing_types_used: list[str]
    context_summary: dict[str, Any]
    garak_objective: str
    defense_patterns: list[str]
    tools_detected: list[str]


# =============================================================================
# Phase 2: Conversion
# =============================================================================

class Phase2Request(BaseModel):
    """Request for Phase 2: Conversion."""
    payloads: list[str] = Field(
        ...,
        min_length=1,
        description="Articulated payloads to convert (from Phase 1)"
    )
    converter_names: Optional[list[str]] = Field(
        None,
        description="Converter names to apply in order (None = passthrough)"
    )
    converter_params: Optional[dict[str, dict[str, Any]]] = Field(
        None,
        description="Optional parameters for specific converters"
    )


class Phase2WithChainRequest(BaseModel):
    """Request for Phase 2 using Phase 1 result chain."""
    phase1_response: Phase1Response = Field(
        ...,
        description="Complete Phase 1 response to use chain from"
    )
    override_converters: Optional[list[str]] = Field(
        None,
        description="Override chain with these converters"
    )


class ConvertedPayloadResponse(BaseModel):
    """Single converted payload with metadata."""
    original: str
    converted: str
    chain_id: str
    converters_applied: list[str]
    errors: Optional[list[str]] = None


class Phase2Response(BaseModel):
    """Response from Phase 2: Conversion."""
    chain_id: str
    converter_names: list[str]
    payloads: list[ConvertedPayloadResponse]
    success_count: int
    error_count: int


class AvailableConvertersResponse(BaseModel):
    """List of available converters."""
    converters: list[str]


# =============================================================================
# Phase 3: Attack Execution
# =============================================================================

class Phase3Request(BaseModel):
    """Request for Phase 3: Attack Execution."""
    campaign_id: str = Field(..., description="Campaign ID for persistence")
    target_url: str = Field(..., description="Target URL to attack")
    payloads: list[ConvertedPayloadResponse] = Field(
        ...,
        min_length=1,
        description="Converted payloads from Phase 2"
    )
    headers: Optional[dict[str, str]] = Field(
        None,
        description="Custom HTTP headers"
    )
    timeout: int = Field(30, ge=5, le=120, description="Request timeout in seconds")
    max_concurrent: int = Field(3, ge=1, le=10, description="Max concurrent requests")


class Phase3WithPhase2Request(BaseModel):
    """Request for Phase 3 using Phase 2 result."""
    campaign_id: str = Field(..., description="Campaign ID for persistence")
    target_url: str = Field(..., description="Target URL to attack")
    phase2_response: Phase2Response = Field(
        ...,
        description="Complete Phase 2 response"
    )
    headers: Optional[dict[str, str]] = None
    timeout: int = Field(30, ge=5, le=120)
    max_concurrent: int = Field(3, ge=1, le=10)


class AttackResponseItem(BaseModel):
    """Single attack response."""
    payload_index: int
    payload: str
    response: str
    status_code: int
    latency_ms: float
    error: Optional[str] = None


class ScorerResultItem(BaseModel):
    """Single scorer result."""
    severity: str
    confidence: float
    reasoning: Optional[str] = None


class CompositeScoreResponse(BaseModel):
    """Composite scoring result."""
    overall_severity: str
    total_score: float
    is_successful: bool
    scorer_results: dict[str, ScorerResultItem]


class Phase3Response(BaseModel):
    """Response from Phase 3: Attack Execution."""
    campaign_id: str
    target_url: str
    attack_responses: list[AttackResponseItem]
    composite_score: CompositeScoreResponse
    is_successful: bool
    overall_severity: str
    total_score: float
    learned_chain: Optional[ConverterChainResponse] = None
    failure_analysis: Optional[dict[str, Any]] = None
    adaptation_strategy: Optional[dict[str, Any]] = None


# =============================================================================
# Full Attack (Single-Shot)
# =============================================================================

class FullAttackRequest(BaseModel):
    """Request for complete single-shot attack."""
    campaign_id: str = Field(..., description="Campaign ID to load intelligence from S3")
    target_url: str = Field(..., description="Target URL to attack")
    payload_count: int = Field(3, ge=1, le=6, description="Number of payloads to generate")
    framing_types: Optional[list[FramingType]] = Field(
        None,
        description="Framing types (None = auto-select)"
    )
    converter_names: Optional[list[str]] = Field(
        None,
        description="Override converters (None = use Phase 1 selection)"
    )
    max_concurrent: int = Field(3, ge=1, le=10, description="Max concurrent attack requests")


class FullAttackResponse(BaseModel):
    """Response from complete single-shot attack."""
    campaign_id: str
    target_url: str
    scan_id: str
    phase1: Phase1Response
    phase2: Phase2Response
    phase3: Phase3Response
    is_successful: bool
    overall_severity: str
    total_score: float
    payloads_generated: int
    payloads_sent: int


# =============================================================================
# Adaptive Attack
# =============================================================================

class AdaptiveAttackRequest(BaseModel):
    """Request for adaptive attack with auto-retry."""
    campaign_id: str = Field(..., description="Campaign ID to load intelligence from S3")
    target_url: str = Field(..., description="Target URL to attack")
    max_iterations: int = Field(
        5,
        ge=1,
        le=20,
        description="Maximum adaptation iterations"
    )
    payload_count: int = Field(2, ge=1, le=6, description="Initial number of payloads")
    framing_types: Optional[list[FramingType]] = Field(
        None,
        description="Initial framing types (None = auto-select)"
    )
    converter_names: Optional[list[str]] = Field(
        None,
        description="Initial converter chain (None = auto-select)"
    )
    success_scorers: Optional[list[ScorerType]] = Field(
        None,
        description="Scorers that must succeed (None = any scorer success)"
    )
    success_threshold: float = Field(
        0.8,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for success"
    )


class IterationHistoryItem(BaseModel):
    """Single iteration history entry."""
    iteration: int
    is_successful: bool
    score: float
    framing: Optional[str] = None
    converters: Optional[list[str]] = None


class AdaptiveAttackResponse(BaseModel):
    """Response from adaptive attack."""
    campaign_id: str
    target_url: str
    scan_id: str
    is_successful: bool
    total_iterations: int
    best_score: float
    best_iteration: int
    iteration_history: list[IterationHistoryItem]
    final_phase3: Optional[Phase3Response] = None
    adaptation_reasoning: Optional[str] = None


# =============================================================================
# SSE Streaming Events
# =============================================================================

class SniperStreamEventType(str, Enum):
    """Event types for SSE streaming during attack execution."""
    # Phase markers
    ATTACK_STARTED = "attack_started"
    PHASE1_START = "phase1_start"
    PHASE1_PROGRESS = "phase1_progress"
    PHASE1_COMPLETE = "phase1_complete"
    PHASE2_START = "phase2_start"
    PHASE2_PROGRESS = "phase2_progress"
    PHASE2_COMPLETE = "phase2_complete"
    PHASE3_START = "phase3_start"
    PHASE3_PROGRESS = "phase3_progress"
    PHASE3_COMPLETE = "phase3_complete"
    ATTACK_COMPLETE = "attack_complete"
    # Data events
    PAYLOAD_GENERATED = "payload_generated"
    PAYLOAD_CONVERTED = "payload_converted"
    ATTACK_SENT = "attack_sent"
    RESPONSE_RECEIVED = "response_received"
    SCORE_CALCULATED = "score_calculated"
    # Error events
    ERROR = "error"
    WARNING = "warning"


class SniperStreamEvent(BaseModel):
    """Single SSE event during attack execution."""
    type: SniperStreamEventType
    phase: Optional[str] = Field(None, description="Current phase (phase1, phase2, phase3)")
    message: str = Field(..., description="Human-readable message")
    data: Optional[dict[str, Any]] = Field(None, description="Event-specific data")
    timestamp: str = Field(..., description="ISO timestamp")
    progress: Optional[float] = Field(None, ge=0, le=1, description="Progress 0-1 within current phase")
