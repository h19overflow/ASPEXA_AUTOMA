"""Persistence layer contracts for the Audit Lake."""
from enum import Enum
from typing import Optional
from pydantic import Field
from libs.contracts.common import StrictBaseModel


class AuditPhase(str, Enum):
    """Audit phase directory names matching S3 structure."""
    RECON = "01_recon"
    SCANNING = "02_scanning"
    PLANNING = "03_planning"
    EXECUTION = "04_execution"


class ArtifactMetadata(StrictBaseModel):
    """Metadata for a stored artifact."""
    audit_id: str = Field(..., description="UUID v4 audit identifier")
    phase: AuditPhase = Field(..., description="Audit phase")
    filename: str = Field(..., description="Artifact filename")
    s3_key: str = Field(..., description="Full S3 object key")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")
    content_type: str = Field(default="application/json", description="MIME type")


class PersistenceError(Exception):
    """Base exception for persistence operations."""
    pass


class ArtifactNotFoundError(PersistenceError):
    """Artifact does not exist in storage."""
    pass


class ArtifactUploadError(PersistenceError):
    """Failed to upload artifact."""
    pass


class ArtifactDownloadError(PersistenceError):
    """Failed to download artifact."""
    pass
