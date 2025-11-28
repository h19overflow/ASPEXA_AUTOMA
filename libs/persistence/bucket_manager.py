"""S3 Bucket Manager CLI.

Provides commands to manage JSON files in the audit lake S3 bucket.
Commands:
  - stats: Show bucket statistics (file counts, sizes by prefix)
  - reset: Delete all JSON files from the bucket

Usage:
    python -m libs.persistence.bucket_manager stats
    python -m libs.persistence.bucket_manager reset [--dry-run] [--force]
"""
import argparse
import asyncio
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from libs.config.settings import get_settings


@dataclass
class BucketStats:
    """Statistics for S3 bucket contents."""

    total_files: int = 0
    total_size_bytes: int = 0
    files_by_prefix: Dict[str, int] = field(default_factory=dict)
    size_by_prefix: Dict[str, int] = field(default_factory=dict)

    @property
    def total_size_mb(self) -> float:
        """Total size in megabytes."""
        return self.total_size_bytes / (1024 * 1024)

    def add_file(self, key: str, size: int) -> None:
        """Add a file to the statistics."""
        self.total_files += 1
        self.total_size_bytes += size

        prefix = key.split("/")[0] if "/" in key else "root"
        self.files_by_prefix[prefix] = self.files_by_prefix.get(prefix, 0) + 1
        self.size_by_prefix[prefix] = self.size_by_prefix.get(prefix, 0) + size


class S3BucketManager:
    """Manages S3 bucket operations for audit lake.

    Args:
        bucket_name: S3 bucket name
        region: AWS region
    """

    def __init__(self, bucket_name: str, region: str = "ap-southeast-2"):
        self._bucket = bucket_name
        self._region = region
        self._client = boto3.client("s3", region_name=region)

    async def get_stats(self) -> BucketStats:
        """Gather statistics for all JSON files in the bucket.

        Returns:
            BucketStats with file counts and sizes
        """
        stats = BucketStats()
        paginator = self._client.get_paginator("list_objects_v2")

        try:
            pages = await asyncio.to_thread(
                lambda: list(paginator.paginate(Bucket=self._bucket))
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to list bucket: {e}") from e

        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".json"):
                    stats.add_file(key, obj["Size"])

        return stats

    async def list_json_files(self) -> List[Dict[str, any]]:
        """List all JSON files in the bucket.

        Returns:
            List of dicts with 'Key' and 'Size' for each file
        """
        files = []
        paginator = self._client.get_paginator("list_objects_v2")

        try:
            pages = await asyncio.to_thread(
                lambda: list(paginator.paginate(Bucket=self._bucket))
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to list bucket: {e}") from e

        for page in pages:
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".json"):
                    files.append({"Key": obj["Key"], "Size": obj["Size"]})

        return files

    async def delete_json_files(
        self, dry_run: bool = False
    ) -> tuple[int, int]:
        """Delete all JSON files from the bucket.

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            Tuple of (files_deleted, bytes_freed)
        """
        files = await self.list_json_files()
        if not files:
            return 0, 0

        total_size = sum(f["Size"] for f in files)

        if dry_run:
            return len(files), total_size

        # Delete in batches of 1000 (S3 limit)
        deleted_count = 0
        for i in range(0, len(files), 1000):
            batch = files[i : i + 1000]
            delete_objects = {"Objects": [{"Key": f["Key"]} for f in batch]}

            try:
                await asyncio.to_thread(
                    self._client.delete_objects,
                    Bucket=self._bucket,
                    Delete=delete_objects,
                )
                deleted_count += len(batch)
            except ClientError as e:
                raise RuntimeError(f"Failed to delete batch: {e}") from e

        return deleted_count, total_size


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


async def cmd_stats(manager: S3BucketManager) -> int:
    """Execute the stats command.

    Args:
        manager: S3BucketManager instance

    Returns:
        Exit code (0 for success)
    """
    print(f"Gathering statistics for bucket: {manager._bucket}")
    print("-" * 50)

    stats = await manager.get_stats()

    if stats.total_files == 0:
        print("No JSON files found in bucket.")
        return 0

    print(f"\nTotal JSON files: {stats.total_files}")
    print(f"Total size: {_format_size(stats.total_size_bytes)}")
    print("\nBreakdown by prefix:")
    print("-" * 50)

    for prefix in sorted(stats.files_by_prefix.keys()):
        count = stats.files_by_prefix[prefix]
        size = stats.size_by_prefix[prefix]
        print(f"  {prefix:20} {count:6} files  {_format_size(size):>12}")

    return 0


async def cmd_reset(
    manager: S3BucketManager, dry_run: bool = False, force: bool = False
) -> int:
    """Execute the reset command.

    Args:
        manager: S3BucketManager instance
        dry_run: If True, only show what would be deleted
        force: If True, skip confirmation prompt

    Returns:
        Exit code (0 for success, 1 for cancelled)
    """
    if dry_run:
        print(f"[DRY RUN] Analyzing bucket: {manager._bucket}")
    else:
        print(f"Preparing to delete all JSON files from: {manager._bucket}")

    print("-" * 50)

    files = await manager.list_json_files()

    if not files:
        print("No JSON files found in bucket. Nothing to delete.")
        return 0

    total_size = sum(f["Size"] for f in files)

    print(f"\nFiles to delete: {len(files)}")
    print(f"Space to free: {_format_size(total_size)}")

    if dry_run:
        print("\n[DRY RUN] No files were deleted.")
        print("\nSample files that would be deleted:")
        for f in files[:10]:
            print(f"  - {f['Key']}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
        return 0

    if not force:
        print("\nWARNING: This action cannot be undone!")
        confirm = input("Type 'DELETE' to confirm: ")
        if confirm != "DELETE":
            print("Cancelled.")
            return 1

    print("\nDeleting files...")
    deleted, freed = await manager.delete_json_files(dry_run=False)

    print(f"\nDeleted {deleted} files, freed {_format_size(freed)}")
    return 0


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Manage JSON files in the S3 audit lake bucket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # stats command
    subparsers.add_parser("stats", help="Show bucket statistics")

    # reset command
    reset_parser = subparsers.add_parser("reset", help="Delete all JSON files")
    reset_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without deleting",
    )
    reset_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    # Load settings
    try:
        settings = get_settings()
        if not settings.s3_bucket_name:
            print("Error: S3_BUCKET_NAME not configured in environment")
            return 1
    except Exception as e:
        print(f"Error loading settings: {e}")
        return 1

    manager = S3BucketManager(
        bucket_name=settings.s3_bucket_name,
        region=settings.aws_region,
    )

    # Execute command
    if args.command == "stats":
        return asyncio.run(cmd_stats(manager))
    elif args.command == "reset":
        return asyncio.run(cmd_reset(manager, args.dry_run, args.force))

    return 0


if __name__ == "__main__":
    sys.exit(main())
