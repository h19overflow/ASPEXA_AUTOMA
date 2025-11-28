"""FastAPI request/response schemas for Manual Sniping API.

Defines all Pydantic models for API validation and serialization.
Dependencies: pydantic
System role: API contract definitions
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Session Schemas ---


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    name: Optional[str] = None
    campaign_id: Optional[str] = None


class SessionSummary(BaseModel):
    """Brief session info for list view."""

    session_id: str
    name: Optional[str]
    campaign_id: Optional[str]
    status: str
    created_at: datetime
    attempt_count: int
    stats: Dict[str, Any]


class SessionListResponse(BaseModel):
    """Response for session list."""

    sessions: List[SessionSummary]
    total: int


class SessionDetailResponse(BaseModel):
    """Full session details with attempts."""

    session_id: str
    name: Optional[str]
    campaign_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    attempts: List[Dict[str, Any]]
    saved_chains: List[List[str]]
    stats: Dict[str, Any]
    s3_key: Optional[str] = None
    scan_id: Optional[str] = None


# --- Transform Schemas ---


class TransformRequest(BaseModel):
    """Request to preview transformation."""

    payload: str
    converters: List[str]


class TransformStepResponse(BaseModel):
    """Single transformation step."""

    converter_name: str
    input_payload: str
    output_payload: str
    success: bool
    error: Optional[str]


class TransformResponse(BaseModel):
    """Full transformation result."""

    original_payload: str
    final_payload: str
    steps: List[TransformStepResponse]
    total_converters: int
    successful_converters: int
    errors: List[str]


# --- Execute Schemas ---


class AuthConfigRequest(BaseModel):
    """Authentication configuration."""

    auth_type: str = "none"  # none, bearer, api_key, basic
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    header_name: str = "Authorization"


class TargetConfigRequest(BaseModel):
    """Target configuration for attack."""

    url: str
    protocol: str = "http"  # http, websocket
    headers: Dict[str, str] = Field(default_factory=dict)
    auth: AuthConfigRequest = Field(default_factory=AuthConfigRequest)
    timeout_seconds: int = 30
    message_field: str = "message"


class ExecuteRequest(BaseModel):
    """Request to execute attack."""

    session_id: str
    payload: str
    converters: List[str]
    target: TargetConfigRequest


class ExecuteResponse(BaseModel):
    """Response for attack execution (async)."""

    attempt_id: str
    session_id: str
    status: str
    message: str


# --- Save Schemas ---


class SaveSessionRequest(BaseModel):
    """Request to save session to S3."""

    name: Optional[str] = None


class SaveSessionResponse(BaseModel):
    """Response after saving session."""

    session_id: str
    s3_key: str
    scan_id: str
    status: str
    stats: Dict[str, Any]


# --- Converter Schemas ---


class ConverterInfoResponse(BaseModel):
    """Converter metadata."""

    name: str
    display_name: str
    description: str
    category: str
    example_input: str
    example_output: str


class ConverterListResponse(BaseModel):
    """List of available converters."""

    converters: List[ConverterInfoResponse]
    categories: List[str]


# --- Insights Schemas ---


class VulnerabilityPatternResponse(BaseModel):
    """Vulnerability pattern from campaign."""

    pattern_id: str
    source: str
    vulnerability_type: str
    description: str
    successful_payloads: List[str]
    confidence: float


class CampaignInsightsResponse(BaseModel):
    """Campaign intelligence response."""

    campaign_id: str
    campaign_name: Optional[str]
    recon: Optional[Dict[str, Any]]
    scan: Optional[Dict[str, Any]]
    exploit: Optional[Dict[str, Any]]
    patterns: List[VulnerabilityPatternResponse]
