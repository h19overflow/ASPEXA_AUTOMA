"""
Cancellation and pause/resume manager for Swarm workflows.

Purpose: Enable graceful cancellation and pause/resume of long-running scans
Dependencies: asyncio

This module provides:
- CancellationManager for individual scan control
- Registry pattern for managing multiple concurrent scans
- Cooperative checkpoint mechanism for safe stopping points
"""

import asyncio
from typing import Any, Dict, Optional


class CancellationManager:
    """
    Manages cancellation and pause/resume state for a single scan.

    Uses asyncio.Event for thread-safe signaling between coroutines.
    The checkpoint() method should be called at safe stopping points
    in the workflow to check for cancellation or wait during pause.
    """

    def __init__(self) -> None:
        self._cancel = asyncio.Event()
        self._pause = asyncio.Event()
        self._pause.set()  # Start in non-paused state
        self._snapshot: Optional[Dict[str, Any]] = None

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancel.is_set()

    @property
    def is_paused(self) -> bool:
        """Check if the scan is currently paused."""
        return not self._pause.is_set()

    def cancel(self) -> None:
        """Request cancellation of the scan."""
        self._cancel.set()

    def pause(self) -> None:
        """Pause the scan at the next checkpoint."""
        self._pause.clear()

    def resume(self) -> None:
        """Resume a paused scan."""
        self._pause.set()

    async def checkpoint(self) -> bool:
        """
        Call at safe points in the workflow to check state.

        This method will:
        1. Block if paused until resume() is called
        2. Return True if cancelled, False otherwise

        Returns:
            True if the scan should be cancelled, False to continue
        """
        await self._pause.wait()
        return self._cancel.is_set()

    def save_snapshot(self, state: Dict[str, Any]) -> None:
        """
        Save a state snapshot for potential resumption.

        Args:
            state: Serializable state dict to preserve
        """
        self._snapshot = state

    def get_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the last saved snapshot.

        Returns:
            The saved state dict, or None if no snapshot exists
        """
        return self._snapshot


# Module-level registry for scan managers
_managers: Dict[str, CancellationManager] = {}


def get_cancellation_manager(scan_id: str) -> CancellationManager:
    """
    Get or create a CancellationManager for a scan.

    Args:
        scan_id: Unique identifier for the scan

    Returns:
        CancellationManager instance for the scan
    """
    if scan_id not in _managers:
        _managers[scan_id] = CancellationManager()
    return _managers[scan_id]


def remove_cancellation_manager(scan_id: str) -> None:
    """
    Remove a CancellationManager from the registry.

    Call this when a scan completes to free resources.

    Args:
        scan_id: Unique identifier for the scan
    """
    _managers.pop(scan_id, None)


def get_active_scan_ids() -> list[str]:
    """
    Get list of currently registered scan IDs.

    Returns:
        List of active scan identifiers
    """
    return list(_managers.keys())
