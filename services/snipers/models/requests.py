"""Request and input models."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from services.snipers.models.enums import AttackMode, ProbeCategory


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
