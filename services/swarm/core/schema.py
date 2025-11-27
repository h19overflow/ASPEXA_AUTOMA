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
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from pydantic import Field, model_validator, field_validator

from libs.contracts.common import StrictBaseModel
from libs.contracts.scanning import VulnerabilityCluster
from services.swarm.core.config import ScanApproach

if TYPE_CHECKING:
    from libs.contracts.scanning import ScanJobDispatch
    from libs.contracts.recon import ReconBlueprint


class ScanConfig(StrictBaseModel):
    """User-configurable scan parameters.

    This allows users to control:
    - Scan approach (quick/standard/thorough)
    - Number of probe attempts
    - Specific probes to run
    - Whether agent can adjust parameters dynamically
    - Parallel execution and rate limiting
    - Connection type (HTTP/WebSocket)
    """
    approach: str = Field(
        default=ScanApproach.STANDARD,
        description="Scan intensity: quick, standard, or thorough"
    )
    generations: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Override: number of attempts per probe (1-50). None = use approach default"
    )
    custom_probes: Optional[List[str]] = Field(
        default=None,
        description="Override: specific probe names to run instead of defaults"
    )
    allow_agent_override: bool = Field(
        default=True,
        description="Allow agent to adjust probe count based on recon intelligence"
    )
    max_probes: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of probes agent can run (1-20)"
    )
    max_generations: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Maximum generations agent can use per probe (1-50)"
    )
    # Parallel execution controls
    enable_parallel_execution: bool = Field(
        default=False,
        description="Enable parallel execution of probes and generations (master switch)"
    )
    max_concurrent_probes: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Maximum number of probes to run concurrently (1-10)"
    )
    max_concurrent_generations: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Maximum number of generation attempts per probe to run concurrently (1-5)"
    )
    # Rate limiting
    requests_per_second: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Rate limit in requests per second (None = unlimited)"
    )
    max_concurrent_connections: int = Field(
        default=5,
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
        description="Maximum retry attempts on failure (0-10)"
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
        
        # Validate concurrent limits don't exceed connection pool
        max_concurrent_ops = self.max_concurrent_probes * self.max_concurrent_generations
        if max_concurrent_ops > self.max_concurrent_connections:
            raise ValueError(
                f"max_concurrent_probes ({self.max_concurrent_probes}) * "
                f"max_concurrent_generations ({self.max_concurrent_generations}) = {max_concurrent_ops} "
                f"exceeds max_concurrent_connections ({self.max_concurrent_connections})"
            )
        
        # Warn if parallel execution enabled but limits are conservative
        if self.enable_parallel_execution:
            if self.max_concurrent_probes == 1 and self.max_concurrent_generations == 1:
                import warnings
                warnings.warn(
                    "enable_parallel_execution is True but both max_concurrent_probes and "
                    "max_concurrent_generations are 1. Parallel execution will have no effect.",
                    UserWarning
                )
        
        return self


class ScanInput(StrictBaseModel):
    """Input context for a Swarm agent scan."""

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
    config: ScanConfig = Field(
        default_factory=ScanConfig,
        description="User-configurable scan parameters"
    )


class ScanContext(StrictBaseModel):
    """Unified scan context that consolidates all configuration and intelligence.
    
    This class serves as a single source of truth for scan configuration,
    eliminating the need for multiple transformations across the codebase.
    """
    audit_id: str = Field(..., description="Audit identifier")
    agent_type: str = Field(..., description="Agent type: agent_sql, agent_auth, or agent_jailbreak")
    target_url: str = Field(..., description="Target LLM endpoint URL")
    infrastructure: Dict[str, Any] = Field(default_factory=dict, description="Infrastructure details")
    detected_tools: List[Dict[str, Any]] = Field(default_factory=list, description="Detected tools")
    config: ScanConfig = Field(default_factory=ScanConfig, description="Scan configuration")
    
    @classmethod
    def from_scan_job(
        cls,
        request: "ScanJobDispatch",
        blueprint: "ReconBlueprint",
        agent_type: str,
        default_target_url: str = "https://api.target.local/v1/chat"
    ) -> "ScanContext":
        """Build ScanContext from ScanJobDispatch and ReconBlueprint.

        This is the unified builder that replaces all the manual extraction
        and transformation logic in consumer.py.
        """
        # Extract infrastructure from intelligence
        infrastructure = {}
        detected_tools = []

        if blueprint.intelligence:
            if blueprint.intelligence.infrastructure:
                infra = blueprint.intelligence.infrastructure
                infrastructure = {
                    "vector_db": infra.vector_db,
                    "model_family": infra.model_family,
                    "rate_limits": infra.rate_limits,
                    "database": getattr(infra, "database", None),
                }

            if blueprint.intelligence.detected_tools:
                detected_tools = [t.model_dump() for t in blueprint.intelligence.detected_tools]

        # Build scan config from request.scan_config (the proper contract field)
        req_cfg = request.scan_config
        scan_config = ScanConfig(
            approach=req_cfg.approach,
            generations=req_cfg.generations,
            custom_probes=req_cfg.custom_probes or None,
            allow_agent_override=req_cfg.allow_agent_override,
            max_probes=req_cfg.max_probes,
            max_generations=req_cfg.max_generations,
            enable_parallel_execution=req_cfg.enable_parallel_execution,
            max_concurrent_probes=req_cfg.max_concurrent_probes,
            max_concurrent_generations=req_cfg.max_concurrent_generations,
            requests_per_second=req_cfg.requests_per_second,
            max_concurrent_connections=req_cfg.max_concurrent_connections,
            request_timeout=req_cfg.request_timeout,
            max_retries=req_cfg.max_retries,
            retry_backoff=req_cfg.retry_backoff,
            connection_type=req_cfg.connection_type,
        )

        # Use target_url from request if provided, otherwise fall back to default
        resolved_target_url = request.target_url if request.target_url else default_target_url

        return cls(
            audit_id=blueprint.audit_id,
            agent_type=agent_type,
            target_url=resolved_target_url,
            infrastructure=infrastructure,
            detected_tools=detected_tools,
            config=scan_config,
        )
    
    def to_scan_input(self) -> ScanInput:
        """Convert ScanContext to ScanInput for backward compatibility."""
        return ScanInput(
            audit_id=self.audit_id,
            agent_type=self.agent_type,
            target_url=self.target_url,
            infrastructure=self.infrastructure,
            detected_tools=self.detected_tools,
            config=self.config,
        )


class ScanAnalysisResult(StrictBaseModel):
    """Structured result from analyze_target tool."""
    recommended_probes: List[str] = Field(..., description="Recommended probe names")
    recommended_generations: int = Field(..., description="Recommended generations per probe")
    risk_level: str = Field(..., description="Risk level: low, medium, high, critical")
    reasoning: str = Field(..., description="Reasoning for recommendations")
    infrastructure_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of infrastructure details"
    )


class ProbeResultDetail(StrictBaseModel):
    """Individual probe result with full details for observability."""
    probe_name: str = Field(..., description="Name of the probe")
    probe_description: str = Field(default="", description="Description of the probe")
    category: str = Field(default="unknown", description="Probe category")
    prompt: str = Field(default="", description="Attack prompt sent")
    output: str = Field(default="", description="Target response received")
    status: str = Field(..., description="Result status: pass, fail, or error")
    detector_name: str = Field(default="", description="Detector that triggered")
    detector_score: float = Field(default=0.0, description="Detector confidence score 0-1")
    detection_reason: str = Field(default="", description="Why detector triggered")


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
    generations_used: int = Field(default=0, description="Number of generations used")
    report_path: Optional[str] = Field(None, description="Path to scan report file")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the scan"
    )
    error: Optional[str] = Field(None, description="Error message if scan failed")


class ScanPlan(StrictBaseModel):
    """Agent's probe selection and configuration output.

    Internal contract: Agent -> Scanner.
    Not exposed in public API responses.
    """
    audit_id: str = Field(..., description="Audit identifier for tracking")
    agent_type: str = Field(..., description="Agent that created this plan")
    target_url: str = Field(..., description="Target endpoint URL")
    selected_probes: List[str] = Field(
        ...,
        description="Probe identifiers to execute, e.g., ['dan.Dan_11_0', 'encoding.InjectBase64']"
    )
    probe_reasoning: Dict[str, str] = Field(
        default_factory=dict,
        description="Why each probe was selected, keyed by probe name"
    )
    generations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of generation attempts per prompt"
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


class ScanPlanResponse(StrictBaseModel):
    """Structured response from planning agent.

    Wraps ScanPlan with additional context for logging and debugging.
    Internal use only.
    """
    plan: ScanPlan = Field(..., description="The scan plan to execute")
    analysis_summary: str = Field(
        ...,
        description="Brief summary of target analysis"
    )
    estimated_prompts: int = Field(
        default=0,
        ge=0,
        description="Estimated total prompts to send"
    )
    risk_assessment: str = Field(
        default="standard",
        description="Risk level: low, standard, high, critical"
    )

    @property
    def total_operations(self) -> int:
        """Calculate total operations: probes * prompts_per_probe * generations."""
        avg_prompts_per_probe = 10
        return len(self.plan.selected_probes) * avg_prompts_per_probe * self.plan.generations


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

