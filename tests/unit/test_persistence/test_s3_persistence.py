"""Unit tests for S3 Persistence Layer."""
import json
from io import BytesIO
from unittest.mock import MagicMock, AsyncMock
import pytest
from botocore.exceptions import ClientError

from libs.persistence import (
    save_artifact,
    load_artifact,
    list_audit_files,
    artifact_exists,
    AuditPhase,
    ArtifactMetadata,
    ArtifactNotFoundError,
    ArtifactUploadError,
    ArtifactDownloadError,
)
from libs.persistence.s3 import S3PersistenceAdapter


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    return MagicMock()


@pytest.fixture
def adapter(mock_s3_client):
    """Create S3PersistenceAdapter with mock client."""
    return S3PersistenceAdapter(
        bucket_name="test-bucket",
        region="ap-southeast-2",
        client=mock_s3_client,
    )


class TestS3PersistenceAdapter:
    """Tests for S3PersistenceAdapter class."""

    def test_build_key(self, adapter):
        """Test S3 key construction."""
        key = adapter._build_key("audit-123", AuditPhase.RECON, "blueprint.json")
        assert key == "campaigns/audit-123/01_recon/blueprint.json"

    def test_build_key_execution_phase(self, adapter):
        """Test key construction for execution phase."""
        key = adapter._build_key("audit-456", AuditPhase.EXECUTION, "kill_chain.json")
        assert key == "campaigns/audit-456/04_execution/kill_chain.json"

    @pytest.mark.asyncio
    async def test_save_artifact_success(self, adapter, mock_s3_client):
        """Test successful artifact save."""
        mock_s3_client.put_object.return_value = {}
        test_data = {"audit_id": "123", "status": "complete"}

        result = await adapter.save_artifact(
            audit_id="audit-123",
            phase=AuditPhase.RECON,
            filename="blueprint.json",
            data=test_data,
        )

        assert isinstance(result, ArtifactMetadata)
        assert result.audit_id == "audit-123"
        assert result.phase == AuditPhase.RECON
        assert result.filename == "blueprint.json"
        assert result.s3_key == "campaigns/audit-123/01_recon/blueprint.json"

        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["ContentType"] == "application/json"

    @pytest.mark.asyncio
    async def test_save_artifact_upload_error(self, adapter, mock_s3_client):
        """Test upload error handling."""
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject",
        )

        with pytest.raises(ArtifactUploadError) as exc_info:
            await adapter.save_artifact(
                audit_id="audit-123",
                phase=AuditPhase.RECON,
                filename="blueprint.json",
                data={"test": "data"},
            )

        assert "Access Denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_artifact_success(self, adapter, mock_s3_client):
        """Test successful artifact load."""
        test_data = {"audit_id": "123", "intelligence": {"tools": []}}
        body_content = json.dumps(test_data).encode("utf-8")

        mock_body = MagicMock()
        mock_body.read.return_value = body_content
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        result = await adapter.load_artifact(
            audit_id="audit-123",
            phase=AuditPhase.RECON,
            filename="blueprint.json",
        )

        assert result == test_data
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="campaigns/audit-123/01_recon/blueprint.json",
        )

    @pytest.mark.asyncio
    async def test_load_artifact_not_found(self, adapter, mock_s3_client):
        """Test artifact not found error."""
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
            "GetObject",
        )

        with pytest.raises(ArtifactNotFoundError):
            await adapter.load_artifact(
                audit_id="audit-123",
                phase=AuditPhase.RECON,
                filename="missing.json",
            )

    @pytest.mark.asyncio
    async def test_load_artifact_download_error(self, adapter, mock_s3_client):
        """Test generic download error."""
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "Internal server error"}},
            "GetObject",
        )

        with pytest.raises(ArtifactDownloadError):
            await adapter.load_artifact(
                audit_id="audit-123",
                phase=AuditPhase.RECON,
                filename="blueprint.json",
            )

    @pytest.mark.asyncio
    async def test_list_audit_files(self, adapter, mock_s3_client):
        """Test listing audit files."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "campaigns/audit-123/01_recon/blueprint.json"},
                {"Key": "campaigns/audit-123/02_scanning/garak_raw.jsonl"},
                {"Key": "campaigns/audit-123/03_planning/sniper_plan.json"},
            ]
        }

        result = await adapter.list_audit_files("audit-123")

        assert result == [
            "01_recon/blueprint.json",
            "02_scanning/garak_raw.jsonl",
            "03_planning/sniper_plan.json",
        ]

    @pytest.mark.asyncio
    async def test_list_audit_files_empty(self, adapter, mock_s3_client):
        """Test listing empty audit."""
        mock_s3_client.list_objects_v2.return_value = {}

        result = await adapter.list_audit_files("audit-empty")

        assert result == []

    @pytest.mark.asyncio
    async def test_artifact_exists_true(self, adapter, mock_s3_client):
        """Test artifact exists check - found."""
        mock_s3_client.head_object.return_value = {"ContentLength": 1234}

        result = await adapter.artifact_exists(
            audit_id="audit-123",
            phase=AuditPhase.RECON,
            filename="blueprint.json",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_artifact_exists_false(self, adapter, mock_s3_client):
        """Test artifact exists check - not found."""
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadObject",
        )

        result = await adapter.artifact_exists(
            audit_id="audit-123",
            phase=AuditPhase.RECON,
            filename="missing.json",
        )

        assert result is False


class TestPublicAPI:
    """Tests for public API functions."""

    @pytest.mark.asyncio
    async def test_save_artifact_phase_resolution(self, adapter, mock_s3_client):
        """Test phase string resolution in save_artifact."""
        mock_s3_client.put_object.return_value = {}

        result = await save_artifact(
            audit_id="audit-123",
            phase="reconnaissance",
            filename="blueprint.json",
            data={"test": True},
            adapter=adapter,
        )

        assert result.phase == AuditPhase.RECON

    @pytest.mark.asyncio
    async def test_save_artifact_scanning_phase(self, adapter, mock_s3_client):
        """Test scanning phase resolution."""
        mock_s3_client.put_object.return_value = {}

        result = await save_artifact(
            audit_id="audit-123",
            phase="scanning",
            filename="scan_dispatch.json",
            data={"job_id": "scan-001"},
            adapter=adapter,
        )

        assert result.phase == AuditPhase.SCANNING
        assert "02_scanning" in result.s3_key

    @pytest.mark.asyncio
    async def test_load_artifact_phase_resolution(self, adapter, mock_s3_client):
        """Test phase string resolution in load_artifact."""
        mock_body = MagicMock()
        mock_body.read.return_value = b'{"test": true}'
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        await load_artifact(
            audit_id="audit-123",
            phase="execution",
            filename="kill_chain.json",
            adapter=adapter,
        )

        call_key = mock_s3_client.get_object.call_args.kwargs["Key"]
        assert "04_execution" in call_key

    @pytest.mark.asyncio
    async def test_invalid_phase_raises_error(self, adapter):
        """Test invalid phase raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await save_artifact(
                audit_id="audit-123",
                phase="invalid_phase",
                filename="test.json",
                data={},
                adapter=adapter,
            )

        assert "Unknown phase" in str(exc_info.value)


class TestAuditPhase:
    """Tests for AuditPhase enum."""

    def test_phase_values(self):
        """Test phase enum values match S3 directory structure."""
        assert AuditPhase.RECON.value == "01_recon"
        assert AuditPhase.SCANNING.value == "02_scanning"
        assert AuditPhase.PLANNING.value == "03_planning"
        assert AuditPhase.EXECUTION.value == "04_execution"
