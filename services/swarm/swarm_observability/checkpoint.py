"""
Checkpointer configuration for Swarm state persistence.

Purpose: Configure LangGraph checkpointers for workflow state persistence
Dependencies: langgraph, pathlib

This module provides:
- Factory function for creating appropriate checkpointer instances
- Support for both persistent (SQLite) and in-memory checkpointing

Note: For SQLite persistence, install: pip install langgraph-checkpoint-sqlite
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from langgraph.checkpoint.memory import MemorySaver

# Type-only import to avoid IDE errors when package not installed
if TYPE_CHECKING:
    from langgraph.checkpoint.sqlite import SqliteSaver

# Runtime check for SQLite availability
try:
    from langgraph.checkpoint.sqlite import SqliteSaver as _SqliteSaver

    SQLITE_AVAILABLE = True
except ImportError:
    _SqliteSaver = None
    SQLITE_AVAILABLE = False


# Default database path relative to the swarm package
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "checkpoints.db"


def get_checkpointer(
    persistent: bool = True,
    db_path: Union[str, Path, None] = None,
) -> Any:
    """
    Create a checkpointer for LangGraph workflow persistence.

    Args:
        persistent: If True, use SQLite for persistence; if False, use memory
        db_path: Custom path for SQLite database (uses default if None)

    Returns:
        MemorySaver for in-memory or SqliteSaver for persistent storage

    Raises:
        ImportError: If persistent=True but langgraph-checkpoint-sqlite not installed
    """
    if not persistent:
        return MemorySaver()

    if not SQLITE_AVAILABLE or _SqliteSaver is None:
        raise ImportError(
            "SQLite checkpointer requires 'langgraph-checkpoint-sqlite'. "
            "Install with: pip install langgraph-checkpoint-sqlite"
        )

    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    return _SqliteSaver.from_conn_string(str(path))
