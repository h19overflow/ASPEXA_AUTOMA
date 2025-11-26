"""IF-01 and IF-02: Reconnaissance Request and Blueprint contracts."""
from typing import Dict, List, Optional
from pydantic import Field, field_validator
from .common import StrictBaseModel, DepthLevel


class TargetConfig(StrictBaseModel):
    """Target configuration for reconnaissance."""
    url: str = Field(..., description="Target API endpoint URL")
    auth_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Authentication headers (e.g., Bearer tokens)"
    )


class ScopeConfig(StrictBaseModel):
    """Reconnaissance scope constraints."""
    depth: DepthLevel = Field(..., description="Reconnaissance depth level")
    max_turns: int = Field(..., gt=0, description="Maximum conversation turns")
    forbidden_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords that must not be used"
    )

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: DepthLevel) -> DepthLevel:
        """Ensure depth is one of the allowed values."""
        if v not in [DepthLevel.SHALLOW, DepthLevel.STANDARD, DepthLevel.AGGRESSIVE]:
            raise ValueError(f"depth must be one of: shallow, standard, aggressive")
        return v


class ReconRequest(StrictBaseModel):
    """IF-01: Reconnaissance Request (cmd_recon_start)."""
    audit_id: str = Field(..., description="UUID v4 audit identifier")
    target: TargetConfig
    scope: ScopeConfig
    special_instructions: Optional[str] = Field(
        default=None,
        description="Custom instructions to focus reconnaissance on specific areas"
    )


class DetectedTool(StrictBaseModel):
    """Detected tool in the target system."""
    name: str = Field(..., description="Tool name")
    arguments: List[str] = Field(
        default_factory=list,
        description="Tool argument names"
    )


class InfrastructureIntel(StrictBaseModel):
    """Infrastructure intelligence gathered during recon."""
    vector_db: Optional[str] = Field(None, description="Vector database type")
    model_family: Optional[str] = Field(None, description="LLM model family")
    rate_limits: Optional[str] = Field(None, description="Rate limiting policy")


class AuthStructure(StrictBaseModel):
    """Authentication structure analysis."""
    type: str = Field(..., description="Authentication type (e.g., RBAC, OAuth)")
    rules: List[str] = Field(
        default_factory=list,
        description="Authentication/Authorization rules"
    )
    vulnerabilities: List[str] = Field(
        default_factory=list,
        description="Detected authentication vulnerabilities"
    )


class Intelligence(StrictBaseModel):
    """Gathered intelligence about the target."""
    system_prompt_leak: List[str] = Field(
        default_factory=list,
        description="Leaked system prompt fragments"
    )
    detected_tools: List[DetectedTool] = Field(
        default_factory=list,
        description="Tools detected in the system"
    )
    infrastructure: InfrastructureIntel
    auth_structure: AuthStructure


class ReconBlueprint(StrictBaseModel):
    """IF-02: Reconnaissance Blueprint (evt_recon_finished)."""
    audit_id: str = Field(..., description="UUID v4 audit identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    intelligence: Intelligence
    raw_observations: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Raw deduplicated observations by category (for reference)"
    )
    structured_deductions: Optional[Dict[str, List[Dict[str, str]]]] = Field(
        default=None,
        description="Structured deductions organized by category with confidence levels"
    )
