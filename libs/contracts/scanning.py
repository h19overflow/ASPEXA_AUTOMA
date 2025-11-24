"""IF-03 and IF-04: Scanning Job Dispatch and Vulnerability Cluster contracts."""
from typing import Any, Dict, List
from pydantic import Field
from .common import StrictBaseModel, VulnerabilityCategory, SeverityLevel


class SafetyPolicy(StrictBaseModel):
    """Safety policy for scanning operations."""
    allowed_attack_vectors: List[str] = Field(
        default_factory=list,
        description="Permitted attack vector types"
    )
    blocked_attack_vectors: List[str] = Field(
        default_factory=list,
        description="Forbidden attack vector types"
    )
    aggressiveness: str = Field(..., description="Scan aggressiveness level")


class ScanJobDispatch(StrictBaseModel):
    """IF-03: Scan Job Dispatch (cmd_scan_start)."""
    job_id: str = Field(..., description="Scan job identifier")
    blueprint_context: Dict[str, Any] = Field(
        ...,
        description="The IF-02 ReconBlueprint payload"
    )
    safety_policy: SafetyPolicy


class Evidence(StrictBaseModel):
    """Evidence of a vulnerability."""
    input_payload: str = Field(..., description="Attack payload used")
    error_response: str = Field(..., description="Target's error response")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class VulnerabilityCluster(StrictBaseModel):
    """IF-04: Vulnerability Cluster (evt_vuln_found)."""
    audit_id: str = Field(..., description="UUID v4 audit identifier")
    cluster_id: str = Field(..., description="Vulnerability cluster identifier")
    category: VulnerabilityCategory = Field(..., description="Vulnerability category")
    severity: SeverityLevel = Field(..., description="Severity level")
    evidence: Evidence
    affected_component: str = Field(..., description="Affected component identifier")
