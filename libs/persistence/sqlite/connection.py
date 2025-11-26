"""SQLite connection management.

Provides thread-safe connection handling and schema initialization.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

DEFAULT_DB_PATH = Path.home() / ".aspexa" / "campaigns.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    target_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    -- Stage completion flags
    recon_complete INTEGER NOT NULL DEFAULT 0,
    garak_complete INTEGER NOT NULL DEFAULT 0,
    exploit_complete INTEGER NOT NULL DEFAULT 0,

    -- S3 scan ID mappings
    recon_scan_id TEXT,
    garak_scan_id TEXT,
    exploit_scan_id TEXT,

    -- Metadata
    description TEXT,
    tags TEXT DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_target ON campaigns(target_url);
CREATE INDEX IF NOT EXISTS idx_campaigns_created ON campaigns(created_at DESC);
"""


def init_database(db_path: Optional[Path] = None) -> None:
    """Initialize database schema.

    Args:
        db_path: Path to database file
    """
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_connection(
    db_path: Optional[Path] = None,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections.

    Auto-commits on success, rolls back on error.

    Args:
        db_path: Path to database file

    Yields:
        SQLite connection with Row factory
    """
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
