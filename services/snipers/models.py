"""
Exploit Agent Pydantic Models

All data structures for the exploit agent system using Pydantic V2.
Supports Human-in-the-Loop (HITL) interactions and structured agent outputs.

Includes multi-mode attack support:
- Guided: Uses Garak findings for intelligent attack selection
- Manual: Custom payload with optional converter chain
- Sweep: Category-based automated probe execution

Phase models:
- Phase1Result: Output from payload articulation phase
- Phase2Result: Output from converter application phase
- ConvertedPayload: Individual converted payload with metadata
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from services.snipers.chain_discovery.models import ConverterChain


# ============================================================================
# Attack Mode Enums
# ============================================================================

class AttackMode(str, Enum):
    """Attack execution mode."""
    GUIDED = "guided"      # Uses Garak findings for pattern analysis
    MANUAL = "manual"      # Custom payload with optional converters
    SWEEP = "sweep"        # All probes in selected categories


class ProbeCategory(str, Enum):
    """Probe categories for sweep mode."""
    JAILBREAK = "jailbreak"              # DAN, roleplay bypass
    PROMPT_INJECTION = "prompt_injection"  # Ignore instructions
    ENCODING = "encoding"                # Base64, ROT13, Unicode bypass
    DATA_EXTRACTION = "data_extraction"   # System prompt leak
    TOOL_EXPLOITATION = "tool_exploitation"  # Function call abuse


# ============================================================================
# Streaming Event Models
# ============================================================================

class AttackEvent(BaseModel):
    """SSE event emitted during attack execution."""
    type: Literal[
        "started",
        "plan",
        "approval_required",
        "payload",
        "turn",
        "response",
        "result",
        "score",
        "error",
        "complete"
    ]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Multi-Mode Request Models
# ============================================================================

class ExploitStreamRequest(BaseModel):
    """Request for streaming exploit execution (all modes)."""
    target_url: str = Field(..., description="Target endpoint URL")
    mode: AttackMode = Field(..., description="Attack mode")
    campaign_id: Optional[str] = Field(None, description="Optional campaign for persistence")
    # Manual mode fields
    custom_payload: Optional[str] = Field(None, description="Custom payload for manual mode")
    converters: Optional[List[str]] = Field(None, description="Converters to apply in order")
    # Sweep mode fields
    categories: Optional[List[ProbeCategory]] = Field(None, description="Probe categories for sweep")
    probes_per_category: int = Field(5, ge=1, le=20, description="Max probes per category")
    # Guided mode fields
    probe_name: Optional[str] = Field(None, description="Specific probe for guided mode")
    # Config
    require_plan_approval: bool = Field(True, description="Require human approval before execution")


# ============================================================================
# Core Input Models
# ============================================================================

class ExampleFinding(BaseModel):
    """A single example of a successful attack from Garak scan."""
    prompt: str = Field(..., description="The attack prompt that succeeded")
    output: str = Field(..., description="The target's response")
    detector_name: str = Field(..., description="Detector that triggered")
    detector_score: float = Field(..., ge=0.0, le=1.0, description="Detector confidence score")
    detection_reason: str = Field(..., description="Why the detector triggered")


class VulnerableProbe(BaseModel):
    """Summary of a vulnerable probe from Garak scan."""
    probe_name: str = Field(..., description="Name of the vulnerable probe")
    status: str = Field(..., description="Vulnerability status")
    vulnerability_count: int = Field(..., ge=1, description="Number of vulnerabilities found")
    affected_component: str = Field(..., description="Affected component identifier")
    audit_id: str = Field(..., description="Audit identifier")


class GarakVulnerabilityFinding(BaseModel):
    """Individual vulnerability finding from Garak scan."""
    probe_name: str = Field(..., description="Name of the probe")
    status: str = Field(..., description="Finding status (pass/fail)")
    detector_name: str = Field(..., description="Detector that triggered")
    detector_score: float = Field(..., ge=0.0, le=1.0, description="Detector score")
    detection_reason: str = Field(..., description="Why the detector triggered")
    prompt: str = Field(..., description="Attack prompt used")
    output: str = Field(..., description="Target's response")
    affected_component: str = Field(..., description="Affected component")
    audit_id: str = Field(..., description="Audit identifier")


class ExploitAgentInput(BaseModel):
    """Complete input context for an exploit agent instance."""
    probe_name: str = Field(..., description="Name of the vulnerable probe")
    example_findings: List[ExampleFinding] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="1-3 example findings that succeeded"
    )
    target_url: str = Field(..., description="Target endpoint URL")
    recon_intelligence: Optional[Dict[str, Any]] = Field(
        None,
        description="Recon intelligence data from Phase 2"
    )
    vulnerability_cluster: Optional[Dict[str, Any]] = Field(
        None,
        description="Vulnerability cluster if available"
    )
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Agent configuration"
    )


# ============================================================================
# Agent Reasoning Output Models (Structured Agent Outputs)
# ============================================================================

class PatternAnalysis(BaseModel):
    """Structured output from agent's pattern learning step."""
    common_prompt_structure: str = Field(
        ...,
        description="Identified common prompt pattern across examples"
    )
    payload_encoding_type: str = Field(
        ...,
        description="Encoding/transformation used in successful attacks"
    )
    success_indicators: List[str] = Field(
        ...,
        description="Output patterns that indicate successful exploitation"
    )
    reasoning_steps: List[str] = Field(
        ...,
        description="Chain of Thought reasoning steps"
    )
    step_back_analysis: str = Field(
        ...,
        description="High-level step-back analysis of the vulnerability"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in pattern analysis"
    )


class ConverterSelection(BaseModel):
    """Structured output from agent's converter selection step."""
    selected_converters: List[str] = Field(
        ...,
        description="PyRIT converter names selected for attack"
    )
    reasoning: str = Field(
        ...,
        description="Why these converters were chosen"
    )
    step_back_analysis: str = Field(
        ...,
        description="High-level analysis before converter selection"
    )
    cot_steps: List[str] = Field(
        ...,
        description="Chain of thought reasoning steps"
    )


class PayloadGeneration(BaseModel):
    """Structured output from agent's payload generation step."""
    generated_payloads: List[str] = Field(
        ...,
        min_length=1,
        description="Generated attack payloads"
    )
    template_used: str = Field(
        ...,
        description="Template structure applied to generate payloads"
    )
    variations_applied: List[str] = Field(
        ...,
        description="Variations from example patterns"
    )
    reasoning: str = Field(
        ...,
        description="Chain of Thought reasoning for payload generation"
    )


class ScoringResult(BaseModel):
    """Structured output from agent's attack scoring step."""
    success: bool = Field(
        ...,
        description="Whether the attack was successful"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for success evaluation (0.0 = definitely failed, 1.0 = definitely succeeded)"
    )
    reasoning: str = Field(
        ...,
        description="Step-by-step explanation of why the attack succeeded or failed"
    )
    matched_indicators: List[str] = Field(
        ...,
        description="List of success indicators that matched in the response"
    )
    comparison_to_examples: str = Field(
        ...,
        description="How this response compares to the example successful outputs"
    )


# ============================================================================
# Human-in-the-Loop Models
# ============================================================================

class AttackPlan(BaseModel):
    """Complete attack plan presented to human for review/approval."""
    probe_name: str = Field(..., description="Probe being exploited")
    pattern_analysis: PatternAnalysis = Field(
        ...,
        description="Learned attack pattern"
    )
    converter_selection: ConverterSelection = Field(
        ...,
        description="Selected PyRIT converters"
    )
    payload_generation: PayloadGeneration = Field(
        ...,
        description="Generated attack payloads"
    )
    reasoning_summary: str = Field(
        ...,
        description="Agent's overall reasoning for the attack plan"
    )
    risk_assessment: str = Field(
        ...,
        description="Risk assessment of the planned attack"
    )


class HumanFeedback(BaseModel):
    """Human feedback on agent decisions."""
    approved: bool = Field(..., description="Whether human approved the action")
    feedback_text: Optional[str] = Field(
        None,
        description="Textual feedback from human"
    )
    modifications: Optional[Dict[str, Any]] = Field(
        None,
        description="Modifications requested by human"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of human feedback"
    )


# ============================================================================
# Attack Execution & Results Models
# ============================================================================

class AttackResult(BaseModel):
    """Result of a single attack execution."""
    success: bool = Field(..., description="Whether attack succeeded")
    probe_name: str = Field(..., description="Probe that was exploited")
    attempt_number: int = Field(..., ge=1, description="Attempt sequence number")
    payload: str = Field(..., description="Attack payload used")
    response: str = Field(..., description="Target's response")
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Scorer confidence in success"
    )
    scorer_name: str = Field(..., description="Scorer that evaluated the result")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Attack execution timestamp"
    )
    human_reviewed: bool = Field(
        default=False,
        description="Whether human has reviewed this result"
    )
    human_feedback: Optional[HumanFeedback] = Field(
        None,
        description="Human feedback on the attack result"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if attack failed"
    )


# ============================================================================
# LangGraph State Model
# ============================================================================

class ExploitAgentState(BaseModel):
    """LangGraph state for exploit agent workflow with HITL interrupts."""
    # Input context
    probe_name: str
    example_findings: List[ExampleFinding]
    target_url: str
    recon_intelligence: Optional[Dict[str, Any]] = None
    vulnerability_cluster: Optional[Dict[str, Any]] = None

    # Agent reasoning outputs
    pattern_analysis: Optional[PatternAnalysis] = None
    converter_selection: Optional[ConverterSelection] = None
    payload_generation: Optional[PayloadGeneration] = None
    attack_plan: Optional[AttackPlan] = None

    # Execution results
    attack_results: List[AttackResult] = Field(default_factory=list)

    # Human-in-the-Loop state
    human_approved: Optional[bool] = None
    human_feedback: Optional[HumanFeedback] = None
    awaiting_human_review: bool = False

    # Retry and adaptation
    retry_count: int = 0
    max_retries: int = 3

    # Workflow control
    next_action: Optional[str] = None
    error: Optional[str] = None
    completed: bool = False

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True


# ============================================================================
# Parser Output Models
# ============================================================================

class GarakReportSummary(BaseModel):
    """Summary of Garak scan report."""
    total_results: int = Field(..., description="Total test results")
    pass_count: int = Field(..., description="Number of passing tests")
    fail_count: int = Field(..., description="Number of failing tests")
    error_count: int = Field(..., description="Number of errors")
    probes_tested: List[str] = Field(..., description="List of probes tested")
    failing_probes: List[str] = Field(..., description="List of failing probes")


class ParsedGarakReport(BaseModel):
    """Complete parsed Garak report."""
    summary: GarakReportSummary
    vulnerable_probes: List[VulnerableProbe]
    vulnerability_findings: List[GarakVulnerabilityFinding]
    vulnerability_clusters: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# Dispatcher/Controller Models
# ============================================================================

class ExploitAgentConfig(BaseModel):
    """Configuration for exploit agent execution."""
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    timeout_seconds: int = Field(default=300, ge=0, description="Execution timeout")
    require_human_approval: bool = Field(
        default=True,
        description="Whether to require human approval before attacks"
    )
    enable_adaptive_payloads: bool = Field(
        default=True,
        description="Whether to adapt payloads based on failures"
    )


class ExploitJobRequest(BaseModel):
    """Request to execute exploit agent(s)."""
    garak_report_path: str = Field(..., description="Path to Garak report JSON")
    recon_blueprint_path: Optional[str] = Field(
        None,
        description="Path to Recon Blueprint JSON"
    )
    target_url: str = Field(..., description="Target endpoint URL")
    config: ExploitAgentConfig = Field(
        default_factory=ExploitAgentConfig,
        description="Agent execution configuration"
    )
    selected_probes: Optional[List[str]] = Field(
        None,
        description="Specific probes to exploit (None = all vulnerable probes)"
    )


class ExploitJobResult(BaseModel):
    """Result of exploit job execution."""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    probes_executed: List[str] = Field(..., description="Probes that were exploited")
    attack_results: List[AttackResult] = Field(
        ...,
        description="All attack results"
    )
    successful_attacks: int = Field(..., description="Number of successful attacks")
    failed_attacks: int = Field(..., description="Number of failed attacks")
    execution_time_seconds: float = Field(..., description="Total execution time")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Job completion timestamp"
    )


# ============================================================================
# Phase 1 & Phase 2 Flow Models (Dataclasses)
# ============================================================================

@dataclass
class Phase1Result:
    """Result from Phase 1 execution - ready for handoff to Phase 2.

    Contains articulated payloads ready for conversion.
    NOTE: In adaptive attack loop, selected_chain is None - chain selection
    is handled by adapt_node. For standalone execution, it may be set.
    """
    campaign_id: str
    articulated_payloads: List[str]
    framing_type: str
    framing_types_used: List[str]
    context_summary: Dict[str, Any]
    garak_objective: str
    defense_patterns: List[str]
    tools_detected: List[str]
    selected_chain: Any = None  # Optional - only used in standalone execution, not adaptive loop


@dataclass
class ConvertedPayload:
    """Single converted payload with metadata."""
    original: str
    converted: str
    chain_id: str
    converters_applied: List[str]
    errors: Optional[List[str]] = None


@dataclass
class Phase2Result:
    """Result from Phase 2 converter application.

    Contains converted payloads ready for attack execution.
    """
    chain_id: str
    converter_names: List[str]
    payloads: List[ConvertedPayload]
    success_count: int
    error_count: int


@dataclass
class AttackResponse:
    """Single attack response from target."""
    payload_index: int
    payload: str
    response: str
    status_code: int
    latency_ms: float
    error: Optional[str] = None


@dataclass
class Phase3Result:
    """Result from Phase 3 attack execution.

    Contains attack responses, composite scoring, and learning outcomes.
    """
    campaign_id: str
    target_url: str
    attack_responses: List[AttackResponse]
    composite_score: Any  # CompositeScore - avoid circular import
    is_successful: bool
    overall_severity: str
    total_score: float
    learned_chain: Any = None  # ConverterChain if successful
    failure_analysis: Optional[Dict[str, Any]] = None
    adaptation_strategy: Optional[Dict[str, Any]] = None
