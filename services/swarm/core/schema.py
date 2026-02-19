"""
Purpose: Pydantic schemas for Swarm service I/O and configuration
Role: Data validation, user configuration, and structured inputs
Dependencies: pydantic, libs.contracts

Note: Output schemas are handled by:
  - garak_scanner.models.ProbeResult for probe-level results
  - libs.contracts.scanning.VulnerabilityCluster for final reporting
  - AgentScanResult for structured agent responses
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import Field, model_validator, field_validator

from libs.contracts.common import StrictBaseModel
from libs.contracts.scanning import VulnerabilityCluster
from services.swarm.core.config import ScanApproach


class ScanConfig(StrictBaseModel):
    """User-configurable scan parameters.

    This allows users to control:
    - Scan approach (quick/standard/thorough)
    - Specific probes to run
    - Maximum probes and prompts per probe limits
    - Rate limiting and connection type (HTTP/WebSocket)
    """
    approach: str = Field(
        default=ScanApproach.STANDARD,
        description="Scan intensity: quick, standard, or thorough"
    )
    custom_probes: Optional[List[str]] = Field(
        default=None,
        description="Override: specific probe names to run instead of defaults"
    )
    max_probes: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum number of probes per agent (1-20)"
    )
    max_prompts_per_probe: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of prompts to execute per probe (1-50)"
    )
    # Rate limiting
    requests_per_second: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Rate limit in requests per second (None = unlimited)"
    )
    # Request configuration
    request_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds (1-300)"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts on connection failure (0-10)"
    )
    retry_backoff: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Exponential backoff multiplier for retries (0.1-10.0)"
    )
    # Connection type
    connection_type: str = Field(
        default="http",
        description="Connection protocol: 'http' or 'websocket' (auto-detected from URL if not specified)"
    )

    @model_validator(mode='after')
    def validate_configuration(self):
        """Validate configuration consistency."""
        if self.connection_type not in ["http", "websocket"]:
            raise ValueError(f"connection_type must be 'http' or 'websocket', got '{self.connection_type}'")

        if self.requests_per_second is not None and self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be > 0 if provided")

        return self


class AgentScanResult(StrictBaseModel):
    """Structured result from agent scan execution."""
    success: bool = Field(..., description="Whether the scan completed successfully")
    audit_id: str = Field(..., description="Audit identifier")
    agent_type: str = Field(..., description="Agent type that executed the scan")
    vulnerabilities: List[VulnerabilityCluster] = Field(
        default_factory=list,
        description="List of discovered vulnerabilities"
    )
    probes_executed: List[str] = Field(
        default_factory=list,
        description="List of probe names that were executed"
    )
    probe_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed results for each probe execution (prompt, output, score, etc.)"
    )
    report_path: Optional[str] = Field(None, description="Path to scan report file")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the scan"
    )
    error: Optional[str] = Field(None, description="Error message if scan failed")


class ScanPlan(StrictBaseModel):
    """Agent's probe selection output.

    Internal contract: Agent -> Scanner.
    Not exposed in public API responses.
    """
    audit_id: str = Field(..., description="Audit identifier for tracking")
    agent_type: str = Field(..., description="Agent that created this plan")
    target_url: str = Field(..., description="Target endpoint URL")
    selected_probes: List[str] = Field(
        ...,
        description="Probe identifiers to execute, e.g., ['dan', 'encoding', 'promptinj']"
    )
    scan_config: ScanConfig = Field(
        default_factory=ScanConfig,
        description="Parallelization, timeouts, rate limits"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When the plan was created"
    )

    @field_validator("selected_probes")
    @classmethod
    def validate_probes_not_empty(cls, v: List[str]) -> List[str]:
        """Ensure at least one probe is selected."""
        if not v:
            raise ValueError("selected_probes cannot be empty")
        return v
