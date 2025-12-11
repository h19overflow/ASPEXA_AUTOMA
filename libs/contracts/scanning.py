"""IF-03 and IF-04: Scanning Job Dispatch and Vulnerability Cluster contracts."""
from typing import Any, Dict, List, Optional
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


class ScanConfigContract(StrictBaseModel):
    """Scan configuration passed through the contract layer."""
    approach: str = Field(default="standard", description="Scan intensity")
    custom_probes: List[str] = Field(default_factory=list, description="Custom probes to run")
    max_probes: int = Field(default=10, description="Maximum probes to run")
    # Parallel execution - ENABLED BY DEFAULT
    enable_parallel_execution: bool = Field(default=True, description="Enable parallel probe execution")
    max_concurrent_probes: int = Field(default=3, description="Concurrent probes (3 = good balance)")
    # Rate limiting
    requests_per_second: Optional[float] = Field(default=None, description="Rate limit (requests/sec)")
    max_concurrent_connections: int = Field(default=15, description="Max concurrent connections")
    # Request configuration
    request_timeout: int = Field(default=30, description="Request timeout seconds")
    max_retries: int = Field(default=3, description="Max retry attempts on connection failure")
    retry_backoff: float = Field(default=1.0, description="Retry backoff multiplier")
    connection_type: str = Field(default="http", description="Connection protocol")


class ScanJobDispatch(StrictBaseModel):
    """IF-03: Scan Job Dispatch (cmd_scan_start)."""
    job_id: str = Field(..., description="Scan job identifier")
    campaign_id: Optional[str] = Field(
        default=None,
        description="Campaign ID to load recon from S3. Use this OR blueprint_context."
    )
    blueprint_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The IF-02 ReconBlueprint payload. If not provided, loads from S3 using campaign_id."
    )
    safety_policy: SafetyPolicy
    scan_config: ScanConfigContract = Field(
        default_factory=ScanConfigContract,
        description="Scan configuration parameters"
    )
    target_url: Optional[str] = Field(
        default=None,
        description="Target LLM endpoint URL. If not provided, uses default."
    )


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
