"""S3 Persistence Adapter for the Audit Lake.

Provides async operations for storing/retrieving audit artifacts from S3.
All boto3 calls are wrapped in asyncio.to_thread to prevent blocking.

Structure: s3://{bucket}/campaigns/{audit_id}/{phase}/{filename}
"""
import asyncio
import json
from typing import Any, Dict, List, Protocol, Optional

import boto3
from botocore.exceptions import ClientError

from .contracts import (
    AuditPhase,
    ArtifactMetadata,
    ArtifactNotFoundError,
    ArtifactUploadError,
    ArtifactDownloadError,
)


class S3ClientProtocol(Protocol):
    """Protocol for S3 client operations (enables DI/testing)."""

    def put_object(self, **kwargs) -> Dict[str, Any]: ...
    def get_object(self, **kwargs) -> Dict[str, Any]: ...
    def list_objects_v2(self, **kwargs) -> Dict[str, Any]: ...
    def head_object(self, **kwargs) -> Dict[str, Any]: ...


class S3PersistenceAdapter:
    """Async adapter for S3 artifact storage.

    Wraps synchronous boto3 calls in asyncio.to_thread for non-blocking I/O.

    Args:
        bucket_name: S3 bucket name
        region: AWS region
        client: Optional S3 client (for testing)
    """

    def __init__(
        self,
        bucket_name: str,
        region: str = "ap-southeast-2",
        client: Optional[S3ClientProtocol] = None,
    ):
        self._bucket = bucket_name
        self._region = region
        self._client = client or boto3.client("s3", region_name=region)

    def _build_key(self, audit_id: str, phase: AuditPhase, filename: str) -> str:
        """Build S3 object key from components."""
        return f"campaigns/{audit_id}/{phase.value}/{filename}"

    async def save_artifact(
        self,
        audit_id: str,
        phase: AuditPhase,
        filename: str,
        data: Dict[str, Any],
    ) -> ArtifactMetadata:
        """Save a dictionary as JSON to S3.

        Args:
            audit_id: Unique audit identifier
            phase: Audit phase (determines directory)
            filename: Artifact filename (should end in .json)
            data: Dictionary to serialize as JSON

        Returns:
            ArtifactMetadata with storage details

        Raises:
            ArtifactUploadError: If upload fails
        """
        s3_key = self._build_key(audit_id, phase, filename)
        body = json.dumps(data, indent=2, default=str)

        try:
            await asyncio.to_thread(
                self._client.put_object,
                Bucket=self._bucket,
                Key=s3_key,
                Body=body.encode("utf-8"),
                ContentType="application/json",
            )
        except ClientError as e:
            raise ArtifactUploadError(
                f"Failed to upload {s3_key}: {e.response['Error']['Message']}"
            ) from e

        return ArtifactMetadata(
            audit_id=audit_id,
            phase=phase,
            filename=filename,
            s3_key=s3_key,
            size_bytes=len(body.encode("utf-8")),
            content_type="application/json",
        )

    async def load_artifact(
        self,
        audit_id: str,
        phase: AuditPhase,
        filename: str,
    ) -> Dict[str, Any]:
        """Retrieve and parse a JSON artifact from S3.

        Args:
            audit_id: Unique audit identifier
            phase: Audit phase
            filename: Artifact filename

        Returns:
            Parsed JSON as dictionary

        Raises:
            ArtifactNotFoundError: If artifact doesn't exist
            ArtifactDownloadError: If download fails
        """
        s3_key = self._build_key(audit_id, phase, filename)

        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=self._bucket,
                Key=s3_key,
            )
            body = response["Body"].read().decode("utf-8")
            return json.loads(body)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("NoSuchKey", "404"):
                raise ArtifactNotFoundError(f"Artifact not found: {s3_key}") from e
            raise ArtifactDownloadError(
                f"Failed to download {s3_key}: {e.response['Error']['Message']}"
            ) from e

    async def list_audit_files(self, audit_id: str) -> List[str]:
        """List all files for a specific audit.

        Args:
            audit_id: Unique audit identifier

        Returns:
            List of relative paths (e.g., "01_recon/blueprint.json")
        """
        prefix = f"campaigns/{audit_id}/"

        try:
            response = await asyncio.to_thread(
                self._client.list_objects_v2,
                Bucket=self._bucket,
                Prefix=prefix,
            )
        except ClientError as e:
            raise ArtifactDownloadError(
                f"Failed to list audit {audit_id}: {e.response['Error']['Message']}"
            ) from e

        files = []
        for obj in response.get("Contents", []):
            # Strip the prefix to get relative path
            relative_path = obj["Key"].replace(prefix, "")
            if relative_path:
                files.append(relative_path)
        return files

    async def artifact_exists(
        self,
        audit_id: str,
        phase: AuditPhase,
        filename: str,
    ) -> bool:
        """Check if an artifact exists.

        Args:
            audit_id: Unique audit identifier
            phase: Audit phase
            filename: Artifact filename

        Returns:
            True if artifact exists
        """
        s3_key = self._build_key(audit_id, phase, filename)

        try:
            await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._bucket,
                Key=s3_key,
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise
