"""
Phase 4: Exploit Agent Pydantic Models

All data structures for the exploit agent system using Pydantic V2.
Supports Human-in-the-Loop (HITL) interactions and structured agent outputs.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
