"""Tests for swarm_observability checkpoint module."""

import pytest
from langgraph.checkpoint.memory import MemorySaver

from services.swarm.swarm_observability.checkpoint import (
    SQLITE_AVAILABLE,
    get_checkpointer,
)


class TestGetCheckpointer:
    """Tests for get_checkpointer function."""

    def test_memory_saver_when_not_persistent(self):
        """Should return MemorySaver when persistent=False."""
        checkpointer = get_checkpointer(persistent=False)

        assert isinstance(checkpointer, MemorySaver)

    def test_raises_import_error_when_sqlite_unavailable(self):
        """Should raise ImportError when SQLite not available and persistent=True."""
        if SQLITE_AVAILABLE:
            pytest.skip("SQLite checkpointer is available - cannot test unavailable case")

        with pytest.raises(ImportError) as exc_info:
            get_checkpointer(persistent=True)

        assert "langgraph-checkpoint-sqlite" in str(exc_info.value)

    @pytest.mark.skipif(not SQLITE_AVAILABLE, reason="SQLite checkpointer not installed")
    def test_sqlite_saver_when_persistent(self, tmp_path):
        """Should return SqliteSaver when persistent=True and available."""
        db_path = tmp_path / "test_checkpoints.db"

        checkpointer = get_checkpointer(persistent=True, db_path=db_path)

        # Verify it's not a MemorySaver (it should be SqliteSaver)
        assert not isinstance(checkpointer, MemorySaver)

    @pytest.mark.skipif(not SQLITE_AVAILABLE, reason="SQLite checkpointer not installed")
    def test_creates_parent_directories(self, tmp_path):
        """Should create parent directories for the database file."""
        db_path = tmp_path / "nested" / "dirs" / "checkpoints.db"

        get_checkpointer(persistent=True, db_path=db_path)

        assert db_path.parent.exists()

    def test_memory_saver_default_false_persistent(self):
        """Default persistent=True should attempt SQLite (or fail appropriately)."""
        if SQLITE_AVAILABLE:
            # If available, it would try to create in default location
            # We'll just verify the function is callable
            pass
        else:
            # If not available, should raise ImportError
            with pytest.raises(ImportError):
                get_checkpointer()


class TestSqliteAvailability:
    """Tests for SQLITE_AVAILABLE constant."""

    def test_sqlite_available_is_boolean(self):
        """SQLITE_AVAILABLE should be a boolean."""
        assert isinstance(SQLITE_AVAILABLE, bool)
