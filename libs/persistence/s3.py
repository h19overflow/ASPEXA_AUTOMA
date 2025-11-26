"""S3 Persistence Adapter for the Audit Lake.

Provides async operations for storing/retrieving audit artifacts from S3.
All boto3 calls are wrapped in asyncio.to_thread to prevent blocking.

Structures:
  - Audit artifacts: s3://{bucket}/campaigns/{audit_id}/{phase}/{filename}
  - Scan results: s3://{bucket}/scans/{scan_type}/{scan_id}.json
"""
import asyncio
import json
from typing import Any, Dict, List, Protocol, Optional, Union, Type, TypeVar

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel

from .contracts import (
    AuditPhase,
    ArtifactMetadata,
    ArtifactNotFoundError,
    ArtifactUploadError,
    ArtifactDownloadError,
)
from .scan_models import (
    ScanType,
    ReconResult,
    GarakResult,
    ExploitResult,
    ScanResultSummary,
)

T = TypeVar("T", bound=BaseModel)


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

    # --- Scan Result Methods ---

    def _build_scan_key(self, scan_type: ScanType, scan_id: str) -> str:
        """Build S3 key for scan results."""
        return f"scans/{scan_type.value}/{scan_id}.json"

    def _get_model_for_scan_type(
        self, scan_type: ScanType
    ) -> Type[Union[ReconResult, GarakResult, ExploitResult]]:
        """Return the Pydantic model class for a scan type."""
        mapping = {
            ScanType.RECON: ReconResult,
            ScanType.GARAK: GarakResult,
            ScanType.EXPLOIT: ExploitResult,
        }
        return mapping[scan_type]

    def _extract_scan_id(self, filename: str) -> str:
        """Extract scan ID from filename (removes extension and path)."""
        base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return base.rsplit(".", 1)[0] if "." in base else base

    async def save_scan_result(
        self,
        scan_type: ScanType,
        scan_id: str,
        data: Union[ReconResult, GarakResult, ExploitResult, Dict[str, Any]],
    ) -> ScanResultSummary:
        """Save a typed scan result to S3.

        Args:
            scan_type: Type of scan (recon, garak, exploit)
            scan_id: Unique scan identifier
            data: Scan result (Pydantic model or dict)

        Returns:
            ScanResultSummary with storage details

        Raises:
            ArtifactUploadError: If upload fails
        """
        s3_key = self._build_scan_key(scan_type, scan_id)

        # Convert Pydantic model to dict if needed
        if isinstance(data, BaseModel):
            body = data.model_dump_json(indent=2)
            audit_id = getattr(data, "audit_id", scan_id)
            timestamp = getattr(data, "timestamp", "")
        else:
            body = json.dumps(data, indent=2, default=str)
            audit_id = data.get("audit_id", scan_id)
            timestamp = data.get("timestamp", "")

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
                f"Failed to upload scan {s3_key}: {e.response['Error']['Message']}"
            ) from e

        return ScanResultSummary(
            scan_id=scan_id,
            scan_type=scan_type,
            audit_id=audit_id,
            timestamp=timestamp,
            s3_key=s3_key,
            filename=f"{scan_id}.json",
        )

    async def load_scan_result(
        self,
        scan_type: ScanType,
        scan_id: str,
        validate: bool = True,
    ) -> Union[ReconResult, GarakResult, ExploitResult, Dict[str, Any]]:
        """Load and optionally validate a scan result from S3.

        Args:
            scan_type: Type of scan
            scan_id: Unique scan identifier
            validate: If True, parse into typed Pydantic model

        Returns:
            Typed scan result model or raw dict

        Raises:
            ArtifactNotFoundError: If scan doesn't exist
            ArtifactDownloadError: If download fails
        """
        s3_key = self._build_scan_key(scan_type, scan_id)

        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=self._bucket,
                Key=s3_key,
            )
            body = response["Body"].read().decode("utf-8")
            raw_data = json.loads(body)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("NoSuchKey", "404"):
                raise ArtifactNotFoundError(f"Scan not found: {s3_key}") from e
            raise ArtifactDownloadError(
                f"Failed to download {s3_key}: {e.response['Error']['Message']}"
            ) from e

        if not validate:
            return raw_data

        model_class = self._get_model_for_scan_type(scan_type)
        return model_class.model_validate(raw_data)

    async def list_scans(
        self,
        scan_type: Optional[ScanType] = None,
        audit_id_filter: Optional[str] = None,
    ) -> List[ScanResultSummary]:
        """List scan results, optionally filtered by type or audit ID.

        Args:
            scan_type: Filter by scan type (None = all types)
            audit_id_filter: Filter by audit ID substring

        Returns:
            List of scan summaries
        """
        summaries: List[ScanResultSummary] = []
        types_to_search = [scan_type] if scan_type else list(ScanType)

        for st in types_to_search:
            prefix = f"scans/{st.value}/"
            try:
                response = await asyncio.to_thread(
                    self._client.list_objects_v2,
                    Bucket=self._bucket,
                    Prefix=prefix,
                )
            except ClientError as e:
                raise ArtifactDownloadError(
                    f"Failed to list scans: {e.response['Error']['Message']}"
                ) from e

            for obj in response.get("Contents", []):
                s3_key = obj["Key"]
                filename = s3_key.rsplit("/", 1)[-1]
                scan_id = self._extract_scan_id(filename)

                # Optionally filter by audit_id (requires loading file)
                if audit_id_filter:
                    try:
                        data = await self.load_scan_result(st, scan_id, validate=False)
                        if audit_id_filter not in data.get("audit_id", ""):
                            continue
                        audit_id = data.get("audit_id", scan_id)
                        timestamp = data.get("timestamp", "")
                    except Exception:
                        continue
                else:
                    audit_id = scan_id
                    timestamp = ""

                summaries.append(
                    ScanResultSummary(
                        scan_id=scan_id,
                        scan_type=st,
                        audit_id=audit_id,
                        timestamp=timestamp,
                        s3_key=s3_key,
                        filename=filename,
                    )
                )

        return summaries

    async def scan_exists(self, scan_type: ScanType, scan_id: str) -> bool:
        """Check if a scan result exists."""
        s3_key = self._build_scan_key(scan_type, scan_id)
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

    async def delete_scan(self, scan_type: ScanType, scan_id: str) -> bool:
        """Delete a scan result from S3.

        Args:
            scan_type: Type of scan
            scan_id: Scan identifier

        Returns:
            True if deleted, False if not found
        """
        s3_key = self._build_scan_key(scan_type, scan_id)
        try:
            await asyncio.to_thread(
                self._client.delete_object,
                Bucket=self._bucket,
                Key=s3_key,
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise ArtifactDownloadError(
                f"Failed to delete {s3_key}: {e.response['Error']['Message']}"
            ) from e
