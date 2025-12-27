"""Persistence Layer for Audit Lake.

Two-tier storage:
- SQLite (local): Campaign tracking, stage flags, S3 key mappings
- S3 (cloud): Actual scan data (recon, garak, exploit results)

Usage:
    # Campaign management (local SQLite)
    from libs.persistence.sqlite import CampaignRepository, Campaign, Stage

    repo = CampaignRepository()
    campaign = repo.create_campaign("My Audit", "http://target.com/chat")
    repo.set_stage_complete(campaign.campaign_id, Stage.RECON, "scan-001")

    # Scan data (S3)
    from libs.persistence import save_scan, load_scan, ScanType

    await save_scan(ScanType.RECON, "scan-001", recon_data)
    result = await load_scan(ScanType.RECON, "scan-001")
"""
from typing import Any, Dict, List, Optional, Union

from libs.config.settings import get_settings

from .contracts import (
    AuditPhase,
    ArtifactMetadata,
    PersistenceError,
    ArtifactNotFoundError,
    ArtifactUploadError,
    ArtifactDownloadError,
)
from .s3 import S3PersistenceAdapter
from .scan_models import (
    ScanType,
    ReconResult,
    GarakResult,
    ExploitResult,
    ScanResultSummary,
    # Checkpoint models for adaptive attack pause/resume
    CheckpointStatus,
    CheckpointConfig,
    CheckpointIteration,
    CheckpointResumeState,
    CheckpointResult,
)

# SQLite imports (re-exported for convenience)
from .sqlite import (
    Campaign,
    CampaignStatus,
    Stage,
    ScanMapping,
    CampaignRepository,
)


# Phase name mapping for convenience
_PHASE_ALIASES = {
    "reconnaissance": AuditPhase.RECON,
    "recon": AuditPhase.RECON,
    "01_recon": AuditPhase.RECON,
    "scanning": AuditPhase.SCANNING,
    "02_scanning": AuditPhase.SCANNING,
    "planning": AuditPhase.PLANNING,
    "03_planning": AuditPhase.PLANNING,
    "execution": AuditPhase.EXECUTION,
    "04_execution": AuditPhase.EXECUTION,
}


def _resolve_phase(phase: str) -> AuditPhase:
    """Resolve phase string to AuditPhase enum."""
    normalized = phase.lower().strip()
    if normalized in _PHASE_ALIASES:
        return _PHASE_ALIASES[normalized]
    raise ValueError(f"Unknown phase: {phase}. Valid: {list(_PHASE_ALIASES.keys())}")


def _get_adapter() -> S3PersistenceAdapter:
    """Get configured S3 adapter from environment."""
    settings = get_settings()
    if not settings.s3_bucket_name:
        raise PersistenceError("S3_BUCKET_NAME not configured in environment")
    return S3PersistenceAdapter(
        bucket_name=settings.s3_bucket_name,
        region=settings.aws_region,
    )


async def save_artifact(
    audit_id: str,
    phase: str,
    filename: str,
    data: Dict[str, Any],
    adapter: Optional[S3PersistenceAdapter] = None,
) -> ArtifactMetadata:
    """Save a dictionary as JSON to S3.

    Args:
        audit_id: Unique audit identifier (UUID v4)
        phase: Phase name (e.g., "reconnaissance", "scanning")
        filename: Artifact filename (e.g., "blueprint_v1.json")
        data: Dictionary to serialize (Pydantic .model_dump() or dict)
        adapter: Optional custom adapter (for testing)

    Returns:
        ArtifactMetadata with storage location details

    Raises:
        ArtifactUploadError: If upload fails
        ValueError: If phase is invalid
    """
    adapter = adapter or _get_adapter()
    resolved_phase = _resolve_phase(phase)
    return await adapter.save_artifact(audit_id, resolved_phase, filename, data)


async def load_artifact(
    audit_id: str,
    phase: str,
    filename: str,
    adapter: Optional[S3PersistenceAdapter] = None,
) -> Dict[str, Any]:
    """Retrieve and parse a JSON artifact from S3.

    Args:
        audit_id: Unique audit identifier
        phase: Phase name
        filename: Artifact filename

    Returns:
        Parsed JSON as dictionary

    Raises:
        ArtifactNotFoundError: If artifact doesn't exist
        ArtifactDownloadError: If download fails
    """
    adapter = adapter or _get_adapter()
    resolved_phase = _resolve_phase(phase)
    return await adapter.load_artifact(audit_id, resolved_phase, filename)


async def list_audit_files(
    audit_id: str,
    adapter: Optional[S3PersistenceAdapter] = None,
) -> List[str]:
    """List all files for a specific audit.

    Args:
        audit_id: Unique audit identifier

    Returns:
        List of relative paths (e.g., ["01_recon/blueprint.json"])
    """
    adapter = adapter or _get_adapter()
    return await adapter.list_audit_files(audit_id)


async def artifact_exists(
    audit_id: str,
    phase: str,
    filename: str,
    adapter: Optional[S3PersistenceAdapter] = None,
) -> bool:
    """Check if an artifact exists.

    Args:
        audit_id: Unique audit identifier
        phase: Phase name
        filename: Artifact filename

    Returns:
        True if artifact exists
    """
    adapter = adapter or _get_adapter()
    resolved_phase = _resolve_phase(phase)
    return await adapter.artifact_exists(audit_id, resolved_phase, filename)


# --- Scan Result Functions ---

async def save_scan(
    scan_type: ScanType,
    scan_id: str,
    data: Union[ReconResult, GarakResult, ExploitResult, Dict[str, Any]],
    adapter: Optional[S3PersistenceAdapter] = None,
) -> ScanResultSummary:
    """Save a scan result to S3.

    Args:
        scan_type: Type of scan (ScanType.RECON, GARAK, EXPLOIT)
        scan_id: Unique scan identifier
        data: Scan result (Pydantic model or dict)
        adapter: Optional custom adapter (for testing)

    Returns:
        ScanResultSummary with storage details

    Raises:
        ArtifactUploadError: If upload fails
    """
    adapter = adapter or _get_adapter()
    return await adapter.save_scan_result(scan_type, scan_id, data)


async def load_scan(
    scan_type: ScanType,
    scan_id: str,
    validate: bool = True,
    adapter: Optional[S3PersistenceAdapter] = None,
) -> Union[ReconResult, GarakResult, ExploitResult, Dict[str, Any]]:
    """Load a scan result from S3.

    Args:
        scan_type: Type of scan
        scan_id: Unique scan identifier
        validate: If True, return typed Pydantic model; else raw dict
        adapter: Optional custom adapter (for testing)

    Returns:
        Typed scan result or raw dict

    Raises:
        ArtifactNotFoundError: If scan doesn't exist
    """
    adapter = adapter or _get_adapter()
    return await adapter.load_scan_result(scan_type, scan_id, validate)


async def list_scans(
    scan_type: Optional[ScanType] = None,
    audit_id_filter: Optional[str] = None,
    adapter: Optional[S3PersistenceAdapter] = None,
) -> List[ScanResultSummary]:
    """List scan results from S3.

    Args:
        scan_type: Filter by type (None = all types)
        audit_id_filter: Filter by audit ID substring
        adapter: Optional custom adapter (for testing)

    Returns:
        List of ScanResultSummary objects
    """
    adapter = adapter or _get_adapter()
    return await adapter.list_scans(scan_type, audit_id_filter)


async def scan_exists(
    scan_type: ScanType,
    scan_id: str,
    adapter: Optional[S3PersistenceAdapter] = None,
) -> bool:
    """Check if a scan result exists."""
    adapter = adapter or _get_adapter()
    return await adapter.scan_exists(scan_type, scan_id)


async def delete_scan(
    scan_type: ScanType,
    scan_id: str,
    adapter: Optional[S3PersistenceAdapter] = None,
) -> bool:
    """Delete a scan result from S3."""
    adapter = adapter or _get_adapter()
    return await adapter.delete_scan(scan_type, scan_id)


__all__ = [
    # Artifact functions (S3)
    "save_artifact",
    "load_artifact",
    "list_audit_files",
    "artifact_exists",
    # Scan functions (S3)
    "save_scan",
    "load_scan",
    "list_scans",
    "scan_exists",
    "delete_scan",
    # Enums
    "AuditPhase",
    "ScanType",
    "CampaignStatus",
    "Stage",
    # Scan models
    "ArtifactMetadata",
    "ReconResult",
    "GarakResult",
    "ExploitResult",
    "ScanResultSummary",
    # Checkpoint models
    "CheckpointStatus",
    "CheckpointConfig",
    "CheckpointIteration",
    "CheckpointResumeState",
    "CheckpointResult",
    # Campaign models (SQLite)
    "Campaign",
    "ScanMapping",
    "CampaignRepository",
    # Exceptions
    "PersistenceError",
    "ArtifactNotFoundError",
    "ArtifactUploadError",
    "ArtifactDownloadError",
    # Adapter (for direct use/testing)
    "S3PersistenceAdapter",
]
