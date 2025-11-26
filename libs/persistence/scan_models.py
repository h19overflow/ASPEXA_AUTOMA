"""Pydantic models for scan result types stored in S3.

Defines structured schemas for:
- Recon results (intelligence gathering)
- Garak jailbreak scan results
- Exploit attempt results

Each model validates the JSON structure and provides type safety.
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field

from libs.contracts.common import StrictBaseModel


class ScanType(str, Enum):
    """Types of security scans stored in S3."""
    RECON = "recon"
    GARAK = "garak"
    EXPLOIT = "exploit"


# --- Recon Models ---

class DetectedTool(StrictBaseModel):
    """A tool detected during reconnaissance."""
    name: str
    arguments: List[str] = Field(default_factory=list)


class AuthStructure(StrictBaseModel):
    """Authentication/authorization structure discovered."""
    type: str = "unknown"
    rules: List[str] = Field(default_factory=list)
    vulnerabilities: List[str] = Field(default_factory=list)


class ReconIntelligence(StrictBaseModel):
    """Intelligence gathered during reconnaissance."""
    system_prompt_leak: List[str] = Field(default_factory=list)
    detected_tools: List[DetectedTool] = Field(default_factory=list)
    infrastructure: Dict[str, Any] = Field(default_factory=dict)
    auth_structure: Optional[AuthStructure] = None


class StructuredDeduction(StrictBaseModel):
    """A deduction with confidence level."""
    finding: str
    confidence: str  # "low", "medium", "high"


class StructuredDeductions(StrictBaseModel):
    """Categorized deductions from reconnaissance."""
    tools: List[StructuredDeduction] = Field(default_factory=list)
    authorization: List[StructuredDeduction] = Field(default_factory=list)
    system_prompt: List[StructuredDeduction] = Field(default_factory=list)
    infrastructure: List[StructuredDeduction] = Field(default_factory=list)


class RawObservations(StrictBaseModel):
    """Raw observations before analysis."""
    system_prompt: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    authorization: List[str] = Field(default_factory=list)
    infrastructure: List[str] = Field(default_factory=list)


class ReconResult(StrictBaseModel):
    """Complete recon scan result."""
    audit_id: str
    timestamp: str
    intelligence: ReconIntelligence
    raw_observations: Optional[RawObservations] = None
    structured_deductions: Optional[StructuredDeductions] = None


# --- Garak Models ---

class GarakSummary(StrictBaseModel):
    """Summary statistics from a Garak scan."""
    total_results: int
    pass_count: int
    fail_count: int
    error_count: int = 0
    probes_tested: List[str] = Field(default_factory=list)
    failing_probes: List[str] = Field(default_factory=list)


class VulnerabilityEvidence(StrictBaseModel):
    """Evidence for a vulnerability finding."""
    input_payload: str
    error_response: str
    confidence_score: float


class VulnerabilityCluster(StrictBaseModel):
    """A cluster of related vulnerabilities."""
    cluster_id: str
    category: str  # VulnerabilityCategory as string
    severity: str  # SeverityLevel as string
    affected_component: str = "unknown"
    audit_id: str
    evidence: VulnerabilityEvidence


class VulnerabilityClusters(StrictBaseModel):
    """Collection of vulnerability clusters."""
    clusters: List[VulnerabilityCluster] = Field(default_factory=list)
    count: int = 0


class VulnerableProbe(StrictBaseModel):
    """A probe that found vulnerabilities."""
    probe_name: str
    status: str
    vulnerability_count: int
    affected_component: str = "unknown"
    audit_id: str


class VulnerableProbes(StrictBaseModel):
    """Collection of vulnerable probes."""
    summary: List[VulnerableProbe] = Field(default_factory=list)
    count: int = 0


class VulnerabilityFinding(StrictBaseModel):
    """Individual vulnerability finding."""
    probe_name: str
    status: str
    detector_name: str
    detector_score: float
    detection_reason: str
    prompt: str
    output: str
    affected_component: str = "unknown"
    audit_id: str


class VulnerabilityFindings(StrictBaseModel):
    """Collection of vulnerability findings."""
    results: List[VulnerabilityFinding] = Field(default_factory=list)
    total_count: int = 0


class GarakMetadata(StrictBaseModel):
    """Metadata about the Garak scan."""
    report_path: str
    audit_id: str
    affected_component: str = "unknown"
    total_vulnerability_clusters: int = 0
    total_vulnerable_probes: int = 0
    total_vulnerability_findings: int = 0


class GarakResult(StrictBaseModel):
    """Complete Garak jailbreak scan result."""
    audit_id: str
    timestamp: str
    summary: GarakSummary
    vulnerability_clusters: VulnerabilityClusters
    vulnerable_probes: VulnerableProbes
    vulnerability_findings: VulnerabilityFindings
    formatted_report: Optional[str] = None
    metadata: GarakMetadata


# --- Exploit Models ---

class PatternAnalysis(StrictBaseModel):
    """Analysis of attack patterns."""
    common_prompt_structure: str
    payload_encoding_type: str
    success_indicators: List[str] = Field(default_factory=list)
    reasoning_steps: List[str] = Field(default_factory=list)
    step_back_analysis: str
    confidence: float


class ExploitAttempt(StrictBaseModel):
    """Individual exploit attempt record."""
    payload: str
    transformed_payload: Optional[str] = None
    response: str
    success: bool
    confidence: float
    reasoning: str
    timestamp: str


class ProbeAttack(StrictBaseModel):
    """Attack attempts against a specific probe."""
    probe_name: str
    pattern_analysis: PatternAnalysis
    converters_used: List[str] = Field(default_factory=list)
    payloads_generated: int
    attempts: List[ExploitAttempt] = Field(default_factory=list)
    success_count: int
    fail_count: int
    overall_success: bool


class ExploitResult(StrictBaseModel):
    """Complete exploit execution result."""
    audit_id: str
    target_url: str
    timestamp: str
    probes_attacked: List[ProbeAttack] = Field(default_factory=list)
    total_attacks: int
    successful_attacks: int
    failed_attacks: int
    recon_intelligence_used: bool = False
    execution_time_seconds: float


# --- Unified Scan Result ---

class ScanResultSummary(StrictBaseModel):
    """Summary of any scan result for listing purposes."""
    scan_id: str
    scan_type: ScanType
    audit_id: str
    timestamp: str
    s3_key: str
    filename: str
