"""Scanning endpoint schemas."""
from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Any, Dict, List, Optional


class ScanStreamMode(str, Enum):
    """Streaming mode for scan execution.

    - VALUES: Legacy mode, yields events from state.events accumulator
    - CUSTOM: StreamWriter events only (recommended for production)
    - DEBUG: Both state and StreamWriter events
    """

    VALUES = "values"
    CUSTOM = "custom"
    DEBUG = "debug"


class ScanConfigRequest(BaseModel):
    """User-configurable scan parameters for API requests."""

    approach: str = Field(
        default="standard",
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
        description="Maximum retry attempts on failure (0-10)"
    )
    retry_backoff: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Exponential backoff multiplier for retries (0.1-10.0)"
    )
    connection_type: str = Field(
        default="http",
        description="Connection protocol: 'http' or 'websocket'"
    )


class ScanStartRequest(BaseModel):
    """Request to start vulnerability scanning.

    Provide EITHER campaign_id (auto-loads recon from S3)
    OR blueprint_context (manual recon data).
    """
    campaign_id: Optional[str] = None
    blueprint_context: Optional[Dict[str, Any]] = None
    agent_types: Optional[List[str]] = None
    allowed_attack_vectors: List[str] = []
    blocked_attack_vectors: List[str] = []
    aggressiveness: str = "moderate"
    # Target URL
    target_url: Optional[str] = Field(
        default=None,
        description="Target LLM endpoint URL. Required for manual scans, optional for campaign scans."
    )
    # Scan configuration
    config: Optional[ScanConfigRequest] = Field(
        default=None,
        description="Optional scan configuration. If not provided, defaults are used."
    )
    # Streaming options
    stream_mode: ScanStreamMode = Field(
        default=ScanStreamMode.CUSTOM,
        description="Streaming mode: 'custom' (real-time), 'values' (legacy), or 'debug' (both)"
    )
    enable_checkpointing: bool = Field(
        default=False,
        description="Enable state persistence for pause/resume capability"
    )

    @model_validator(mode="after")
    def check_input_provided(self):
        if not self.campaign_id and not self.blueprint_context:
            raise ValueError("Must provide either campaign_id or blueprint_context")
        return self
