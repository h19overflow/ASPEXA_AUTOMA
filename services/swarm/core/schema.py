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
    - Maximum probes limit
    - Parallel execution and rate limiting
    - Connection type (HTTP/WebSocket)
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
        default=10,
        ge=1,
        le=20,
        description="Maximum number of probes agent can run (1-20)"
    )
    # Parallel execution controls
    enable_parallel_execution: bool = Field(
        default=True,
        description="Enable parallel execution of probes"
    )
    max_concurrent_probes: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of probes to run concurrently (1-10)"
    )
    # Rate limiting
    requests_per_second: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Rate limit in requests per second (None = unlimited)"
    )
    max_concurrent_connections: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Maximum concurrent connections to target API (1-50)"
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
        # Validate connection type
        if self.connection_type not in ["http", "websocket"]:
            raise ValueError(f"connection_type must be 'http' or 'websocket', got '{self.connection_type}'")

        # Validate requests_per_second if provided
        if self.requests_per_second is not None and self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be > 0 if provided")

        # Validate concurrent probes don't exceed connection pool
        if self.max_concurrent_probes > self.max_concurrent_connections:
            raise ValueError(
                f"max_concurrent_probes ({self.max_concurrent_probes}) "
                f"exceeds max_concurrent_connections ({self.max_concurrent_connections})"
            )

        return self


class ScanInput(StrictBaseModel):
    """Input context for a Swarm agent scan.

    Contains full intelligence from reconnaissance phase to enable
    intelligent probe selection by the planning agent.
    """

    audit_id: str = Field(..., description="Audit identifier")
    agent_type: str = Field(
        ..., description="Agent type: agent_sql, agent_auth, or agent_jailbreak"
    )
    target_url: str = Field(..., description="Target LLM endpoint URL")
    infrastructure: Dict[str, Any] = Field(
        default_factory=dict, description="Infrastructure details from recon"
    )
    detected_tools: List[Dict[str, Any]] = Field(
        default_factory=list, description="Detected tools to test"
    )
    # Full intelligence fields for context-rich planning
    system_prompt_leaks: List[str] = Field(
        default_factory=list,
        description="Leaked system prompt fragments from recon"
    )
    raw_observations: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Raw observations by category from recon"
    )
    structured_deductions: Dict[str, List[Dict[str, str]]] = Field(
        default_factory=dict,
        description="Structured deductions with confidence levels"
    )
    config: ScanConfig = Field(
        default_factory=ScanConfig,
        description="User-configurable scan parameters"
    )


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


class PlanningPhaseResult(StrictBaseModel):
    """Result of the agent planning phase.

    Internal tracking model for entrypoint orchestration.
    """
    success: bool = Field(..., description="Whether planning succeeded")
    plan: Optional[ScanPlan] = Field(None, description="The plan if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: int = Field(default=0, description="Planning duration in milliseconds")

    @classmethod
    def from_success(cls, plan: ScanPlan, duration_ms: int) -> "PlanningPhaseResult":
        """Create a successful planning result."""
        return cls(success=True, plan=plan, duration_ms=duration_ms)

    @classmethod
    def from_error(cls, error: str, duration_ms: int = 0) -> "PlanningPhaseResult":
        """Create a failed planning result."""
        return cls(success=False, error=error, duration_ms=duration_ms)

