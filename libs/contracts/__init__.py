"""Data contracts for the Aspexa system."""
from .common import (
    DepthLevel,
    AttackEngine,
    VulnerabilityCategory,
    SeverityLevel,
    ResultStatus,
    ArtifactType,
    StrictBaseModel,
)
from .recon import (
    TargetConfig,
    ScopeConfig,
    ReconRequest,
    DetectedTool,
    InfrastructureIntel,
    AuthStructure,
    Intelligence,
    ReconBlueprint,
)
from .scanning import (
    SafetyPolicy,
    ScanJobDispatch,
    Evidence,
    VulnerabilityCluster,
)

__all__ = [
    # Common
    "DepthLevel",
    "AttackEngine",
    "VulnerabilityCategory",
    "SeverityLevel",
    "ResultStatus",
    "ArtifactType",
    "StrictBaseModel",
    # Recon
    "TargetConfig",
    "ScopeConfig",
    "ReconRequest",
    "DetectedTool",
    "InfrastructureIntel",
    "AuthStructure",
    "Intelligence",
    "ReconBlueprint",
    # Scanning
    "SafetyPolicy",
    "ScanJobDispatch",
    "Evidence",
    "VulnerabilityCluster",
]
