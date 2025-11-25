"""S3 Persistence Layer for the Audit Lake.

Public API providing simplified access to artifact storage.
Wraps S3PersistenceAdapter with environment configuration.

Usage:
    from libs.persistence import save_artifact, load_artifact, list_audit_files

    await save_artifact(
        audit_id="audit-123",
        phase="reconnaissance",
        filename="blueprint_v1.json",
        data={...}
    )
"""
from typing import Any, Dict, List, Optional

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


__all__ = [
    # Public API functions
    "save_artifact",
    "load_artifact",
    "list_audit_files",
    "artifact_exists",
    # Contracts
    "AuditPhase",
    "ArtifactMetadata",
    "PersistenceError",
    "ArtifactNotFoundError",
    "ArtifactUploadError",
    "ArtifactDownloadError",
    # Adapter (for direct use/testing)
    "S3PersistenceAdapter",
]
