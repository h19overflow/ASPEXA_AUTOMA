"""Attack results, phase results, and report models."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from services.snipers.models.reasoning import HumanFeedback
from services.snipers.models.requests import (
    ExampleFinding,
    GarakVulnerabilityFinding,
    VulnerableProbe,
)


class AttackResult(BaseModel):
    """Result of a single attack execution."""
    success: bool = Field(..., description="Whether attack succeeded")
    probe_name: str = Field(..., description="Probe that was exploited")
    attempt_number: int = Field(..., ge=1, description="Attempt sequence number")
    payload: str = Field(..., description="Attack payload used")
    response: str = Field(..., description="Target's response")
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Scorer confidence in success"
    )
    scorer_name: str = Field(..., description="Scorer that evaluated the result")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Attack execution timestamp"
    )
    human_reviewed: bool = Field(
        default=False, description="Whether human has reviewed this result"
    )
    human_feedback: Optional[HumanFeedback] = Field(
        None, description="Human feedback on the attack result"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if attack failed"
    )


class ExploitJobResult(BaseModel):
    """Result of exploit job execution."""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    probes_executed: List[str] = Field(..., description="Probes that were exploited")
    attack_results: List[AttackResult] = Field(
        ..., description="All attack results"
    )
    successful_attacks: int = Field(..., description="Number of successful attacks")
    failed_attacks: int = Field(..., description="Number of failed attacks")
    execution_time_seconds: float = Field(..., description="Total execution time")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Job completion timestamp"
    )


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
# Phase Result Dataclasses
# ============================================================================

@dataclass
class Phase1Result:
    """Result from Phase 1 execution - ready for handoff to Phase 2."""
    campaign_id: str
    articulated_payloads: List[str]
    framing_type: str
    framing_types_used: List[str]
    context_summary: Dict[str, Any]
    garak_objective: str
    defense_patterns: List[str]
    tools_detected: List[str]
    selected_chain: Any = None


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
    """Result from Phase 2 converter application."""
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
    """Result from Phase 3 attack execution."""
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
