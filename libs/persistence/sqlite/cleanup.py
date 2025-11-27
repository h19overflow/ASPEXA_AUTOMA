"""SQLite cleanup utilities for environment reset.

Provides functions to delete all records from the database.
Use before deployment or for testing environment cleanup.
"""
import logging
from pathlib import Path
from typing import Optional

from .connection import get_connection, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


def delete_all_campaigns(db_path: Optional[Path] = None) -> int:
    """Delete all campaign records from the database.

    Args:
        db_path: Path to database file (uses default if not specified)

    Returns:
        Number of deleted records
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM campaigns")
        count = cursor.fetchone()[0]

        if count > 0:
            conn.execute("DELETE FROM campaigns")
            logger.info(f"Deleted {count} campaign(s) from database")
        else:
            logger.info("No campaigns to delete")

        return count


def reset_database(db_path: Optional[Path] = None) -> dict:
    """Reset the database by deleting all records from all tables.

    Args:
        db_path: Path to database file (uses default if not specified)

    Returns:
        Dictionary with deleted counts per table
    """
    results = {}

    with get_connection(db_path) as conn:
        # Get list of all tables
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]

            if count > 0:
                conn.execute(f"DELETE FROM {table}")
                logger.info(f"Deleted {count} record(s) from {table}")

            results[table] = count

    return results


def drop_database(db_path: Optional[Path] = None) -> bool:
    """Completely remove the database file.

    WARNING: This is destructive and cannot be undone.

    Args:
        db_path: Path to database file (uses default if not specified)

    Returns:
        True if file was deleted, False if it didn't exist
    """
    path = db_path or DEFAULT_DB_PATH

    if path.exists():
        path.unlink()
        logger.info(f"Deleted database file: {path}")
        return True
    else:
        logger.info(f"Database file does not exist: {path}")
        return False


def get_database_stats(db_path: Optional[Path] = None) -> dict:
    """Get statistics about the database.

    Args:
        db_path: Path to database file (uses default if not specified)

    Returns:
        Dictionary with table counts and database info
    """
    path = db_path or DEFAULT_DB_PATH

    if not path.exists():
        return {"exists": False, "path": str(path)}

    stats = {
        "exists": True,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "tables": {},
    }

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            stats["tables"][table] = cursor.fetchone()[0]

    return stats


if __name__ == "__main__":
    """CLI for database cleanup operations."""
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description="SQLite database cleanup utilities")
    parser.add_argument(
        "action",
        choices=["stats", "reset", "drop"],
        help="Action to perform: stats (show info), reset (delete records), drop (delete file)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help=f"Path to database file (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt for destructive actions",
    )

    args = parser.parse_args()

    if args.action == "stats":
        stats = get_database_stats(args.db_path)
        print(f"\nDatabase: {stats['path']}")
        print(f"Exists: {stats['exists']}")
        if stats["exists"]:
            print(f"Size: {stats['size_bytes']:,} bytes")
            print("\nTables:")
            for table, count in stats.get("tables", {}).items():
                print(f"  {table}: {count} records")

    elif args.action == "reset":
        if not args.force:
            confirm = input("This will delete ALL records. Continue? [y/N]: ")
            if confirm.lower() != "y":
                print("Aborted")
                sys.exit(0)

        results = reset_database(args.db_path)
        total = sum(results.values())
        print(f"\nDeleted {total} total record(s)")
        for table, count in results.items():
            print(f"  {table}: {count}")

    elif args.action == "drop":
        if not args.force:
            confirm = input("This will DELETE the database file. Continue? [y/N]: ")
            if confirm.lower() != "y":
                print("Aborted")
                sys.exit(0)

        deleted = drop_database(args.db_path)
        if deleted:
            print("Database file deleted")
        else:
            print("Database file did not exist")
