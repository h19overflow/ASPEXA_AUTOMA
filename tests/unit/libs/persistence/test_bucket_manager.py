"""Unit tests for S3 Bucket Manager CLI.

Tests the S3BucketManager class and helper functions for managing JSON files
in S3 buckets, including statistics gathering, file listing, and batch deletion.
"""
import argparse
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest
from botocore.exceptions import ClientError

from libs.persistence.bucket_manager import (
    BucketStats,
    S3BucketManager,
    _format_size,
    cmd_stats,
    cmd_reset,
    main,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_s3_client():
    """Create a mock boto3 S3 client."""
    return MagicMock()


@pytest.fixture
def manager(mock_s3_client):
    """Create S3BucketManager instance with mocked client."""
    with patch("libs.persistence.bucket_manager.boto3.client", return_value=mock_s3_client):
        return S3BucketManager(
            bucket_name="test-bucket",
            region="ap-southeast-2",
        )


# ============================================================================
# BucketStats Dataclass Tests
# ============================================================================


class TestBucketStats:
    """Tests for BucketStats dataclass."""

    def test_init_defaults(self):
        """Test BucketStats initializes with correct defaults."""
        stats = BucketStats()
        assert stats.total_files == 0
        assert stats.total_size_bytes == 0
        assert stats.files_by_prefix == {}
        assert stats.size_by_prefix == {}

    def test_total_size_mb_property(self):
        """Test total_size_mb property calculation."""
        stats = BucketStats(total_size_bytes=2 * 1024 * 1024)  # 2 MB
        assert stats.total_size_mb == 2.0

    def test_total_size_mb_property_fractional(self):
        """Test total_size_mb with fractional values."""
        stats = BucketStats(total_size_bytes=1536 * 1024)  # 1.5 MB
        assert stats.total_size_mb == 1.5

    def test_total_size_mb_property_bytes(self):
        """Test total_size_mb with small byte counts."""
        stats = BucketStats(total_size_bytes=512)
        assert stats.total_size_mb == pytest.approx(512 / (1024 * 1024))

    def test_add_file_single(self):
        """Test adding a single file with root prefix."""
        stats = BucketStats()
        stats.add_file("myfile.json", 1024)

        assert stats.total_files == 1
        assert stats.total_size_bytes == 1024
        assert stats.files_by_prefix["root"] == 1
        assert stats.size_by_prefix["root"] == 1024

    def test_add_file_with_prefix(self):
        """Test adding file with directory prefix."""
        stats = BucketStats()
        stats.add_file("campaigns/audit-123/data.json", 2048)

        assert stats.total_files == 1
        assert stats.total_size_bytes == 2048
        assert stats.files_by_prefix["campaigns"] == 1
        assert stats.size_by_prefix["campaigns"] == 2048

    def test_add_file_multiple_same_prefix(self):
        """Test adding multiple files to same prefix."""
        stats = BucketStats()
        stats.add_file("campaigns/file1.json", 1000)
        stats.add_file("campaigns/file2.json", 2000)

        assert stats.total_files == 2
        assert stats.total_size_bytes == 3000
        assert stats.files_by_prefix["campaigns"] == 2
        assert stats.size_by_prefix["campaigns"] == 3000

    def test_add_file_multiple_prefixes(self):
        """Test adding files to different prefixes."""
        stats = BucketStats()
        stats.add_file("campaigns/file1.json", 1000)
        stats.add_file("events/file2.json", 2000)
        stats.add_file("logs/file3.json", 3000)

        assert stats.total_files == 3
        assert stats.total_size_bytes == 6000
        assert stats.files_by_prefix == {"campaigns": 1, "events": 1, "logs": 1}
        assert stats.size_by_prefix == {"campaigns": 1000, "events": 2000, "logs": 3000}

    def test_add_file_deep_nesting(self):
        """Test that only first directory is used as prefix."""
        stats = BucketStats()
        stats.add_file("campaigns/audit-123/recon/data.json", 5000)

        assert stats.files_by_prefix["campaigns"] == 1
        assert stats.size_by_prefix["campaigns"] == 5000

    def test_add_file_no_prefix(self):
        """Test file at root level (no prefix)."""
        stats = BucketStats()
        stats.add_file("root_file.json", 1000)

        assert stats.files_by_prefix["root"] == 1
        assert stats.size_by_prefix["root"] == 1000


# ============================================================================
# Format Size Helper Tests
# ============================================================================


class TestFormatSize:
    """Tests for _format_size helper function."""

    def test_format_size_bytes(self):
        """Test formatting bytes."""
        assert _format_size(0) == "0 B"
        assert _format_size(512) == "512 B"
        assert _format_size(1023) == "1023 B"

    def test_format_size_kilobytes(self):
        """Test formatting kilobytes."""
        assert _format_size(1024) == "1.00 KB"
        assert _format_size(1024 * 5) == "5.00 KB"
        assert _format_size(1024 * 1024 - 1) == "1024.00 KB"

    def test_format_size_megabytes(self):
        """Test formatting megabytes."""
        assert _format_size(1024 * 1024) == "1.00 MB"
        assert _format_size(1024 * 1024 * 10) == "10.00 MB"
        assert _format_size(1024 * 1024 * 1024 - 1) == "1024.00 MB"

    def test_format_size_gigabytes(self):
        """Test formatting gigabytes."""
        assert _format_size(1024 * 1024 * 1024) == "1.00 GB"
        assert _format_size(1024 * 1024 * 1024 * 5) == "5.00 GB"

    def test_format_size_fractional_mb(self):
        """Test formatting fractional megabytes."""
        result = _format_size(1024 * 1024 * 1.5)
        assert "1.50 MB" == result

    def test_format_size_fractional_kb(self):
        """Test formatting fractional kilobytes."""
        result = _format_size(int(1024 * 2.5))
        assert "2.50 KB" == result


# ============================================================================
# S3BucketManager.get_stats() Tests
# ============================================================================


class TestS3BucketManagerGetStats:
    """Tests for S3BucketManager.get_stats() method."""

    @pytest.mark.asyncio
    async def test_get_stats_empty_bucket(self, manager, mock_s3_client):
        """Test get_stats with empty bucket."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": []}]
        mock_s3_client.get_paginator.return_value = mock_paginator

        stats = await manager.get_stats()

        assert stats.total_files == 0
        assert stats.total_size_bytes == 0
        assert stats.files_by_prefix == {}
        assert stats.size_by_prefix == {}

    @pytest.mark.asyncio
    async def test_get_stats_single_file(self, manager, mock_s3_client):
        """Test get_stats with single JSON file."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "campaigns/data.json", "Size": 1024}
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        stats = await manager.get_stats()

        assert stats.total_files == 1
        assert stats.total_size_bytes == 1024
        assert stats.files_by_prefix["campaigns"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_multiple_files_same_prefix(self, manager, mock_s3_client):
        """Test get_stats with multiple files in same prefix."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "campaigns/file1.json", "Size": 1000},
                    {"Key": "campaigns/file2.json", "Size": 2000},
                    {"Key": "campaigns/file3.json", "Size": 3000},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        stats = await manager.get_stats()

        assert stats.total_files == 3
        assert stats.total_size_bytes == 6000
        assert stats.files_by_prefix["campaigns"] == 3
        assert stats.size_by_prefix["campaigns"] == 6000

    @pytest.mark.asyncio
    async def test_get_stats_multiple_prefixes(self, manager, mock_s3_client):
        """Test get_stats with files in multiple prefixes."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "campaigns/file1.json", "Size": 1000},
                    {"Key": "events/file2.json", "Size": 2000},
                    {"Key": "logs/file3.json", "Size": 3000},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        stats = await manager.get_stats()

        assert stats.total_files == 3
        assert stats.total_size_bytes == 6000
        assert stats.files_by_prefix == {"campaigns": 1, "events": 1, "logs": 1}
        assert stats.size_by_prefix == {"campaigns": 1000, "events": 2000, "logs": 3000}

    @pytest.mark.asyncio
    async def test_get_stats_ignores_non_json_files(self, manager, mock_s3_client):
        """Test that non-JSON files are ignored."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "campaigns/data.json", "Size": 1000},
                    {"Key": "campaigns/data.txt", "Size": 2000},
                    {"Key": "campaigns/data.csv", "Size": 3000},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        stats = await manager.get_stats()

        assert stats.total_files == 1
        assert stats.total_size_bytes == 1000

    @pytest.mark.asyncio
    async def test_get_stats_pagination(self, manager, mock_s3_client):
        """Test get_stats with multiple pages."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "campaigns/file1.json", "Size": 1000}]},
            {"Contents": [{"Key": "events/file2.json", "Size": 2000}]},
            {"Contents": [{"Key": "logs/file3.json", "Size": 3000}]},
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        stats = await manager.get_stats()

        assert stats.total_files == 3
        assert stats.total_size_bytes == 6000

    @pytest.mark.asyncio
    async def test_get_stats_pagination_empty_pages(self, manager, mock_s3_client):
        """Test get_stats with empty pages in pagination."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "campaigns/file1.json", "Size": 1000}]},
            {},  # Empty page
            {"Contents": [{"Key": "events/file2.json", "Size": 2000}]},
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        stats = await manager.get_stats()

        assert stats.total_files == 2
        assert stats.total_size_bytes == 3000

    @pytest.mark.asyncio
    async def test_get_stats_client_error(self, manager, mock_s3_client):
        """Test get_stats handles ClientError."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "ListObjectsV2",
        )
        mock_s3_client.get_paginator.return_value = mock_paginator

        with pytest.raises(RuntimeError) as exc_info:
            await manager.get_stats()

        assert "Failed to list bucket" in str(exc_info.value)


# ============================================================================
# S3BucketManager.list_json_files() Tests
# ============================================================================


class TestS3BucketManagerListJsonFiles:
    """Tests for S3BucketManager.list_json_files() method."""

    @pytest.mark.asyncio
    async def test_list_json_files_empty(self, manager, mock_s3_client):
        """Test list_json_files with empty bucket."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": []}]
        mock_s3_client.get_paginator.return_value = mock_paginator

        files = await manager.list_json_files()

        assert files == []

    @pytest.mark.asyncio
    async def test_list_json_files_single(self, manager, mock_s3_client):
        """Test list_json_files with single file."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "campaigns/data.json", "Size": 1024}
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        files = await manager.list_json_files()

        assert len(files) == 1
        assert files[0]["Key"] == "campaigns/data.json"
        assert files[0]["Size"] == 1024

    @pytest.mark.asyncio
    async def test_list_json_files_multiple(self, manager, mock_s3_client):
        """Test list_json_files with multiple files."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "campaigns/file1.json", "Size": 1000},
                    {"Key": "campaigns/file2.json", "Size": 2000},
                    {"Key": "events/file3.json", "Size": 3000},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        files = await manager.list_json_files()

        assert len(files) == 3
        assert files[0]["Key"] == "campaigns/file1.json"
        assert files[2]["Key"] == "events/file3.json"

    @pytest.mark.asyncio
    async def test_list_json_files_filters_non_json(self, manager, mock_s3_client):
        """Test that non-JSON files are filtered out."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "campaigns/data.json", "Size": 1000},
                    {"Key": "campaigns/data.txt", "Size": 2000},
                    {"Key": "campaigns/data.jsonl", "Size": 3000},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        files = await manager.list_json_files()

        assert len(files) == 1
        assert files[0]["Key"] == "campaigns/data.json"

    @pytest.mark.asyncio
    async def test_list_json_files_pagination(self, manager, mock_s3_client):
        """Test list_json_files with pagination."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "page1.json", "Size": 1000}]},
            {"Contents": [{"Key": "page2.json", "Size": 2000}]},
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        files = await manager.list_json_files()

        assert len(files) == 2

    @pytest.mark.asyncio
    async def test_list_json_files_client_error(self, manager, mock_s3_client):
        """Test list_json_files handles ClientError."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Bucket not found"}},
            "ListObjectsV2",
        )
        mock_s3_client.get_paginator.return_value = mock_paginator

        with pytest.raises(RuntimeError) as exc_info:
            await manager.list_json_files()

        assert "Failed to list bucket" in str(exc_info.value)


# ============================================================================
# S3BucketManager.delete_json_files() Tests
# ============================================================================


class TestS3BucketManagerDeleteJsonFiles:
    """Tests for S3BucketManager.delete_json_files() method."""

    @pytest.mark.asyncio
    async def test_delete_json_files_dry_run_empty(self, manager, mock_s3_client):
        """Test delete_json_files dry_run with empty bucket."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": []}]
        mock_s3_client.get_paginator.return_value = mock_paginator

        deleted, freed = await manager.delete_json_files(dry_run=True)

        assert deleted == 0
        assert freed == 0
        mock_s3_client.delete_objects.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_json_files_dry_run_single_file(self, manager, mock_s3_client):
        """Test delete_json_files dry_run with single file."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "campaigns/data.json", "Size": 1024}
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        deleted, freed = await manager.delete_json_files(dry_run=True)

        assert deleted == 1
        assert freed == 1024
        mock_s3_client.delete_objects.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_json_files_dry_run_multiple_files(self, manager, mock_s3_client):
        """Test delete_json_files dry_run with multiple files."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "campaigns/file1.json", "Size": 1000},
                    {"Key": "campaigns/file2.json", "Size": 2000},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        deleted, freed = await manager.delete_json_files(dry_run=True)

        assert deleted == 2
        assert freed == 3000
        mock_s3_client.delete_objects.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_json_files_actual_single_batch(self, manager, mock_s3_client):
        """Test delete_json_files actual deletion single batch."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "campaigns/file1.json", "Size": 1000},
                    {"Key": "campaigns/file2.json", "Size": 2000},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_s3_client.delete_objects = AsyncMock()

        deleted, freed = await manager.delete_json_files(dry_run=False)

        assert deleted == 2
        assert freed == 3000
        mock_s3_client.delete_objects.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_json_files_actual_empty_bucket(self, manager, mock_s3_client):
        """Test delete_json_files actual deletion with empty bucket."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": []}]
        mock_s3_client.get_paginator.return_value = mock_paginator

        deleted, freed = await manager.delete_json_files(dry_run=False)

        assert deleted == 0
        assert freed == 0
        mock_s3_client.delete_objects.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_json_files_batching_under_limit(self, manager, mock_s3_client):
        """Test delete_json_files with files under batch limit (1000)."""
        files_content = [
            {"Key": f"file{i}.json", "Size": 1000}
            for i in range(500)
        ]
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": files_content}]
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_s3_client.delete_objects = AsyncMock()

        deleted, freed = await manager.delete_json_files(dry_run=False)

        assert deleted == 500
        assert freed == 500 * 1000
        # Should only call delete_objects once for single batch
        mock_s3_client.delete_objects.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_json_files_batching_multiple_batches(self, manager, mock_s3_client):
        """Test delete_json_files batching with files exceeding 1000 limit."""
        files_content = [
            {"Key": f"file{i}.json", "Size": 1000}
            for i in range(2500)
        ]
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": files_content}]
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_s3_client.delete_objects = AsyncMock()

        deleted, freed = await manager.delete_json_files(dry_run=False)

        assert deleted == 2500
        assert freed == 2500 * 1000
        # Should call delete_objects 3 times (1000 + 1000 + 500)
        assert mock_s3_client.delete_objects.call_count == 3

    @pytest.mark.asyncio
    async def test_delete_json_files_batch_size_exact_boundary(self, manager, mock_s3_client):
        """Test delete_json_files with file count exactly at batch boundary."""
        files_content = [
            {"Key": f"file{i}.json", "Size": 1000}
            for i in range(2000)
        ]
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": files_content}]
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_s3_client.delete_objects = AsyncMock()

        deleted, freed = await manager.delete_json_files(dry_run=False)

        assert deleted == 2000
        assert freed == 2000 * 1000
        # Should call delete_objects exactly 2 times (1000 + 1000)
        assert mock_s3_client.delete_objects.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_json_files_batch_structure(self, manager, mock_s3_client):
        """Test that delete_objects is called with correct batch structure."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "file1.json", "Size": 1000},
                    {"Key": "file2.json", "Size": 2000},
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_s3_client.delete_objects = AsyncMock()

        await manager.delete_json_files(dry_run=False)

        mock_s3_client.delete_objects.assert_called_once()
        call_kwargs = mock_s3_client.delete_objects.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-bucket"
        assert "Delete" in call_kwargs
        assert "Objects" in call_kwargs["Delete"]
        assert len(call_kwargs["Delete"]["Objects"]) == 2
        assert call_kwargs["Delete"]["Objects"][0]["Key"] == "file1.json"
        assert call_kwargs["Delete"]["Objects"][1]["Key"] == "file2.json"

    @pytest.mark.asyncio
    async def test_delete_json_files_client_error(self, manager, mock_s3_client):
        """Test delete_json_files handles ClientError during deletion."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "file1.json", "Size": 1000}
                ]
            }
        ]
        mock_s3_client.get_paginator.return_value = mock_paginator

        # Make delete_objects raise error when called
        mock_s3_client.delete_objects.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "DeleteObjects",
        )

        with pytest.raises(RuntimeError) as exc_info:
            await manager.delete_json_files(dry_run=False)

        assert "Failed to delete batch" in str(exc_info.value)


# ============================================================================
# CLI Command Tests
# ============================================================================


class TestCmdStats:
    """Tests for cmd_stats command handler."""

    @pytest.mark.asyncio
    async def test_cmd_stats_empty_bucket(self, manager, capsys):
        """Test cmd_stats output with empty bucket."""
        manager.get_stats = AsyncMock(return_value=BucketStats())

        exit_code = await cmd_stats(manager)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No JSON files found in bucket" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_stats_with_files(self, manager, capsys):
        """Test cmd_stats output with files."""
        stats = BucketStats()
        stats.add_file("campaigns/file1.json", 1024)
        stats.add_file("events/file2.json", 2048)
        manager.get_stats = AsyncMock(return_value=stats)

        exit_code = await cmd_stats(manager)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Total JSON files: 2" in captured.out
        assert "Total size:" in captured.out
        assert "Breakdown by prefix:" in captured.out
        assert "campaigns" in captured.out
        assert "events" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_stats_displays_sizes(self, manager, capsys):
        """Test that cmd_stats displays formatted sizes."""
        stats = BucketStats()
        stats.add_file("campaigns/file1.json", 1024 * 1024)  # 1 MB
        manager.get_stats = AsyncMock(return_value=stats)

        await cmd_stats(manager)

        captured = capsys.readouterr()
        assert "1.00 MB" in captured.out


class TestCmdReset:
    """Tests for cmd_reset command handler."""

    @pytest.mark.asyncio
    async def test_cmd_reset_dry_run_empty_bucket(self, manager, capsys):
        """Test cmd_reset with dry_run on empty bucket."""
        manager.list_json_files = AsyncMock(return_value=[])

        exit_code = await cmd_reset(manager, dry_run=True)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No JSON files found" in captured.out
        assert "[DRY RUN]" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_reset_dry_run_with_files(self, manager, capsys):
        """Test cmd_reset with dry_run showing sample files."""
        files = [
            {"Key": f"file{i}.json", "Size": 1000}
            for i in range(15)
        ]
        manager.list_json_files = AsyncMock(return_value=files)

        exit_code = await cmd_reset(manager, dry_run=True)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Files to delete: 15" in captured.out
        assert "Sample files that would be deleted:" in captured.out
        # Should show 10 files + "and X more"
        assert "and 5 more" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_reset_actual_with_force(self, manager, capsys):
        """Test cmd_reset actual deletion with force flag."""
        files = [{"Key": "file1.json", "Size": 1000}]
        manager.list_json_files = AsyncMock(return_value=files)
        manager.delete_json_files = AsyncMock(return_value=(1, 1000))

        exit_code = await cmd_reset(manager, dry_run=False, force=True)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Deleted 1 files" in captured.out
        assert "1000 B" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_reset_actual_empty_bucket(self, manager, capsys):
        """Test cmd_reset actual deletion on empty bucket."""
        manager.list_json_files = AsyncMock(return_value=[])

        exit_code = await cmd_reset(manager, dry_run=False, force=True)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No JSON files found" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_reset_requires_confirmation(self, manager, monkeypatch):
        """Test cmd_reset requires confirmation without force flag."""
        files = [{"Key": "file1.json", "Size": 1000}]
        manager.list_json_files = AsyncMock(return_value=files)
        manager.delete_json_files = AsyncMock(return_value=(1, 1000))

        # Simulate user typing "DELETE"
        monkeypatch.setattr("builtins.input", lambda _: "DELETE")

        exit_code = await cmd_reset(manager, dry_run=False, force=False)

        assert exit_code == 0
        manager.delete_json_files.assert_called_once_with(dry_run=False)

    @pytest.mark.asyncio
    async def test_cmd_reset_cancels_on_wrong_confirmation(self, manager, monkeypatch, capsys):
        """Test cmd_reset cancels when wrong confirmation is provided."""
        files = [{"Key": "file1.json", "Size": 1000}]
        manager.list_json_files = AsyncMock(return_value=files)
        manager.delete_json_files = AsyncMock()

        # Simulate user typing wrong confirmation
        monkeypatch.setattr("builtins.input", lambda _: "no")

        exit_code = await cmd_reset(manager, dry_run=False, force=False)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Cancelled" in captured.out
        manager.delete_json_files.assert_not_called()


# ============================================================================
# CLI Argument Parsing Tests
# ============================================================================


class TestMainArgumentParsing:
    """Tests for CLI argument parsing via main()."""

    def test_main_stats_command(self, monkeypatch):
        """Test main with stats command."""
        with patch("libs.persistence.bucket_manager.get_settings") as mock_settings:
            mock_settings.return_value.s3_bucket_name = "test-bucket"
            mock_settings.return_value.aws_region = "ap-southeast-2"

            with patch("libs.persistence.bucket_manager.asyncio.run") as mock_run:
                mock_run.return_value = 0
                monkeypatch.setattr("sys.argv", ["bucket_manager.py", "stats"])

                exit_code = main()

                assert exit_code == 0
                mock_run.assert_called_once()

    def test_main_reset_command_dry_run(self, monkeypatch):
        """Test main with reset command and --dry-run."""
        with patch("libs.persistence.bucket_manager.get_settings") as mock_settings:
            mock_settings.return_value.s3_bucket_name = "test-bucket"
            mock_settings.return_value.aws_region = "ap-southeast-2"

            with patch("libs.persistence.bucket_manager.asyncio.run") as mock_run:
                mock_run.return_value = 0
                monkeypatch.setattr("sys.argv", ["bucket_manager.py", "reset", "--dry-run"])

                exit_code = main()

                assert exit_code == 0

    def test_main_reset_command_force(self, monkeypatch):
        """Test main with reset command and --force."""
        with patch("libs.persistence.bucket_manager.get_settings") as mock_settings:
            mock_settings.return_value.s3_bucket_name = "test-bucket"
            mock_settings.return_value.aws_region = "ap-southeast-2"

            with patch("libs.persistence.bucket_manager.asyncio.run") as mock_run:
                mock_run.return_value = 0
                monkeypatch.setattr("sys.argv", ["bucket_manager.py", "reset", "--force"])

                exit_code = main()

                assert exit_code == 0

    def test_main_reset_command_both_flags(self, monkeypatch):
        """Test main with reset command and both --dry-run and --force."""
        with patch("libs.persistence.bucket_manager.get_settings") as mock_settings:
            mock_settings.return_value.s3_bucket_name = "test-bucket"
            mock_settings.return_value.aws_region = "ap-southeast-2"

            with patch("libs.persistence.bucket_manager.asyncio.run") as mock_run:
                mock_run.return_value = 0
                monkeypatch.setattr("sys.argv", ["bucket_manager.py", "reset", "--dry-run", "--force"])

                exit_code = main()

                assert exit_code == 0

    def test_main_missing_command(self, monkeypatch):
        """Test main with no command provided."""
        monkeypatch.setattr("sys.argv", ["bucket_manager.py"])

        with pytest.raises(SystemExit):
            main()

    def test_main_no_bucket_configured(self, monkeypatch):
        """Test main when S3_BUCKET_NAME not configured."""
        with patch("libs.persistence.bucket_manager.get_settings") as mock_settings:
            mock_settings.return_value.s3_bucket_name = None
            monkeypatch.setattr("sys.argv", ["bucket_manager.py", "stats"])

            exit_code = main()

            assert exit_code == 1

    def test_main_settings_load_error(self, monkeypatch):
        """Test main when settings fail to load."""
        with patch("libs.persistence.bucket_manager.get_settings") as mock_settings:
            mock_settings.side_effect = Exception("Config error")
            monkeypatch.setattr("sys.argv", ["bucket_manager.py", "stats"])

            exit_code = main()

            assert exit_code == 1


# ============================================================================
# Integration Tests
# ============================================================================


class TestS3BucketManagerIntegration:
    """Integration tests for S3BucketManager."""

    @pytest.mark.asyncio
    async def test_stats_then_list_consistency(self, manager, mock_s3_client):
        """Test that stats and list_json_files are consistent."""
        files_data = [
            {"Key": "campaigns/file1.json", "Size": 1000},
            {"Key": "campaigns/file2.json", "Size": 2000},
            {"Key": "events/file3.json", "Size": 3000},
        ]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": files_data}]
        mock_s3_client.get_paginator.return_value = mock_paginator

        stats = await manager.get_stats()
        files = await manager.list_json_files()

        assert stats.total_files == len(files)
        assert stats.total_size_bytes == sum(f["Size"] for f in files)

    @pytest.mark.asyncio
    async def test_delete_matches_list(self, manager, mock_s3_client):
        """Test that delete counts match list results."""
        files_data = [
            {"Key": f"file{i}.json", "Size": 1000}
            for i in range(150)
        ]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": files_data}]
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_s3_client.delete_objects = AsyncMock()

        deleted, freed = await manager.delete_json_files(dry_run=True)
        files = await manager.list_json_files()

        assert deleted == len(files)
        assert freed == sum(f["Size"] for f in files)
