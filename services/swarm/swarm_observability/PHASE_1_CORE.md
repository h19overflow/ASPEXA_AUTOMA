# Phase 1: Core Infrastructure

## Files to Create

| File | Purpose |
|------|---------|
| `events.py` | Standardized event types |
| `cancellation.py` | Cancel/pause/resume manager |
| `checkpoint.py` | Checkpointer configuration |

---

## 1.1 events.py

```python
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel
from datetime import datetime


class EventType(str, Enum):
    # Lifecycle
    SCAN_STARTED = "scan_started"
    SCAN_PAUSED = "scan_paused"
    SCAN_CANCELLED = "scan_cancelled"
    SCAN_COMPLETE = "scan_complete"
    SCAN_ERROR = "scan_error"

    # Nodes
    NODE_ENTER = "node_enter"
    NODE_PROGRESS = "node_progress"
    NODE_EXIT = "node_exit"

    # Planning
    PLAN_START = "plan_start"
    PLAN_COMPLETE = "plan_complete"

    # Execution
    PROBE_START = "probe_start"
    PROBE_RESULT = "probe_result"
    PROBE_COMPLETE = "probe_complete"

    # Agent
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"

    # System
    LOG = "log"
    HEARTBEAT = "heartbeat"


class StreamEvent(BaseModel):
    type: EventType
    timestamp: datetime = None
    node: Optional[str] = None
    agent: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    progress: Optional[float] = None

    def __init__(self, **kwargs):
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.utcnow()
        super().__init__(**kwargs)
```

---

## 1.2 cancellation.py

```python
import asyncio
from typing import Optional, Dict, Any


class CancellationManager:
    def __init__(self):
        self._cancel = asyncio.Event()
        self._pause = asyncio.Event()
        self._pause.set()  # Not paused
        self._snapshot: Optional[Dict[str, Any]] = None

    @property
    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    @property
    def is_paused(self) -> bool:
        return not self._pause.is_set()

    def cancel(self) -> None:
        self._cancel.set()

    def pause(self) -> None:
        self._pause.clear()

    def resume(self) -> None:
        self._pause.set()

    async def checkpoint(self) -> bool:
        """Call at safe points. Returns True if cancelled."""
        await self._pause.wait()
        return self._cancel.is_set()

    def save_snapshot(self, state: Dict[str, Any]) -> None:
        self._snapshot = state

    def get_snapshot(self) -> Optional[Dict[str, Any]]:
        return self._snapshot


# Registry
_managers: Dict[str, CancellationManager] = {}


def get_manager(scan_id: str) -> CancellationManager:
    if scan_id not in _managers:
        _managers[scan_id] = CancellationManager()
    return _managers[scan_id]


def remove_manager(scan_id: str) -> None:
    _managers.pop(scan_id, None)
```

---

## 1.3 checkpoint.py

```python
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver


def get_checkpointer(persistent: bool = True):
    if not persistent:
        return MemorySaver()

    db_path = Path(__file__).parent.parent / "data" / "checkpoints.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(db_path))
```

---

## Done When

- [ ] All three files created
- [ ] Unit tests pass
- [ ] Imports work from `swarm_observability`
