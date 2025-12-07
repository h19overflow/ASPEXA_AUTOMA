"""Tests for swarm_observability cancellation module."""

import asyncio

import pytest

from services.swarm.swarm_observability.cancellation import (
    CancellationManager,
    get_active_scan_ids,
    get_cancellation_manager,
    remove_cancellation_manager,
)


class TestCancellationManager:
    """Tests for CancellationManager class."""

    def test_initial_state(self):
        """Manager should start in non-cancelled, non-paused state."""
        manager = CancellationManager()

        assert manager.is_cancelled is False
        assert manager.is_paused is False

    def test_cancel_sets_cancelled_flag(self):
        """Calling cancel() should set is_cancelled to True."""
        manager = CancellationManager()

        manager.cancel()

        assert manager.is_cancelled is True

    def test_pause_sets_paused_flag(self):
        """Calling pause() should set is_paused to True."""
        manager = CancellationManager()

        manager.pause()

        assert manager.is_paused is True

    def test_resume_clears_paused_flag(self):
        """Calling resume() after pause() should clear is_paused."""
        manager = CancellationManager()

        manager.pause()
        assert manager.is_paused is True

        manager.resume()
        assert manager.is_paused is False

    @pytest.mark.asyncio
    async def test_checkpoint_returns_false_when_not_cancelled(self):
        """checkpoint() should return False when not cancelled."""
        manager = CancellationManager()

        result = await manager.checkpoint()

        assert result is False

    @pytest.mark.asyncio
    async def test_checkpoint_returns_true_when_cancelled(self):
        """checkpoint() should return True when cancelled."""
        manager = CancellationManager()
        manager.cancel()

        result = await manager.checkpoint()

        assert result is True

    @pytest.mark.asyncio
    async def test_checkpoint_waits_when_paused(self):
        """checkpoint() should block when paused until resume()."""
        manager = CancellationManager()
        manager.pause()

        checkpoint_completed = False

        async def run_checkpoint():
            nonlocal checkpoint_completed
            await manager.checkpoint()
            checkpoint_completed = True

        task = asyncio.create_task(run_checkpoint())

        # Give it time to potentially complete (it shouldn't)
        await asyncio.sleep(0.05)
        assert checkpoint_completed is False

        # Resume should allow checkpoint to complete
        manager.resume()
        await asyncio.sleep(0.05)
        assert checkpoint_completed is True

        await task

    def test_save_and_get_snapshot(self):
        """Should be able to save and retrieve state snapshots."""
        manager = CancellationManager()
        state = {"current_probe": 5, "results": [1, 2, 3]}

        manager.save_snapshot(state)
        retrieved = manager.get_snapshot()

        assert retrieved == state

    def test_get_snapshot_returns_none_when_empty(self):
        """get_snapshot() should return None if no snapshot saved."""
        manager = CancellationManager()

        assert manager.get_snapshot() is None

    def test_snapshot_can_be_overwritten(self):
        """Saving a new snapshot should overwrite the previous one."""
        manager = CancellationManager()

        manager.save_snapshot({"version": 1})
        manager.save_snapshot({"version": 2})

        assert manager.get_snapshot() == {"version": 2}


class TestManagerRegistry:
    """Tests for the module-level manager registry."""

    def setup_method(self):
        """Clean up registry before each test."""
        for scan_id in get_active_scan_ids():
            remove_cancellation_manager(scan_id)

    def teardown_method(self):
        """Clean up registry after each test."""
        for scan_id in get_active_scan_ids():
            remove_cancellation_manager(scan_id)

    def test_get_manager_creates_new_manager(self):
        """get_cancellation_manager() should create manager if not exists."""
        manager = get_cancellation_manager("scan-001")

        assert isinstance(manager, CancellationManager)

    def test_get_manager_returns_same_instance(self):
        """get_cancellation_manager() should return same instance for same ID."""
        manager1 = get_cancellation_manager("scan-001")
        manager2 = get_cancellation_manager("scan-001")

        assert manager1 is manager2

    def test_different_scan_ids_get_different_managers(self):
        """Different scan IDs should get different manager instances."""
        manager1 = get_cancellation_manager("scan-001")
        manager2 = get_cancellation_manager("scan-002")

        assert manager1 is not manager2

    def test_remove_manager(self):
        """remove_cancellation_manager() should remove from registry."""
        manager1 = get_cancellation_manager("scan-001")

        remove_cancellation_manager("scan-001")

        # Getting again should create a new instance
        manager2 = get_cancellation_manager("scan-001")
        assert manager1 is not manager2

    def test_remove_nonexistent_manager_does_not_raise(self):
        """Removing non-existent manager should not raise error."""
        remove_cancellation_manager("nonexistent-scan")

    def test_get_active_scan_ids(self):
        """get_active_scan_ids() should return list of registered scan IDs."""
        get_cancellation_manager("scan-001")
        get_cancellation_manager("scan-002")
        get_cancellation_manager("scan-003")

        active_ids = get_active_scan_ids()

        assert set(active_ids) == {"scan-001", "scan-002", "scan-003"}

    def test_get_active_scan_ids_empty(self):
        """get_active_scan_ids() should return empty list when no managers."""
        active_ids = get_active_scan_ids()

        assert active_ids == []

    def test_manager_state_persists_across_gets(self):
        """Manager state should persist when retrieved multiple times."""
        manager = get_cancellation_manager("scan-001")
        manager.cancel()
        manager.save_snapshot({"state": "saved"})

        # Get same manager again
        same_manager = get_cancellation_manager("scan-001")

        assert same_manager.is_cancelled is True
        assert same_manager.get_snapshot() == {"state": "saved"}
