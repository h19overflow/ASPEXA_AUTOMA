# Swarm Observability

Enhanced streaming, cancellation, and state persistence for Swarm workflows.

## Structure

```
swarm_observability/
├── README.md           # This file (progress log)
├── __init__.py         # Package exports
├── events.py           # StreamEvent model, EventType enum
├── cancellation.py     # CancellationManager for pause/resume/cancel
├── checkpoint.py       # LangGraph checkpointer configuration
├── PHASE_1_CORE.md     # Event types, cancellation, checkpoint
├── PHASE_2_NODES.md    # Node enhancement with StreamWriter
├── PHASE_3_STREAM.md   # Entrypoint multi-mode streaming
├── PHASE_4_API.md      # Control endpoints
└── PHASE_5_FRONTEND.md # UI controls
```

## Goals

1. Real-time granular updates to frontend
2. User-controlled pause/resume/cancel
3. State persistence on interruption

---

## Implementation Progress

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | **Complete** | Core infrastructure (events, cancellation, checkpoint) |
| Phase 2 | **Complete** | Node enhancement with StreamWriter |
| Phase 3 | **Complete** | Entrypoint multi-mode streaming |
| Phase 4 | **Complete** | Control endpoints |
| Phase 5 | **Complete** | UI controls |

---

## Phase Dependencies

```
Phase 1 (Core) ─────────────────────────────────────┐
  └─ events.py (EventType, StreamEvent)             │
  └─ cancellation.py (CancellationManager)          │
  └─ checkpoint.py (get_checkpointer)               │
                                                    ▼
Phase 2 (Nodes) ────────────────────────────────────┐
  └─ Imports from Phase 1                           │
  └─ Modifies: graph/state.py (add cancelled, progress)
  └─ Modifies: graph/nodes/*.py (add event emission)│
                                                    ▼
Phase 3 (Stream) ───────────────────────────────────┐
  └─ Imports from Phase 1                           │
  └─ Uses nodes from Phase 2                        │
  └─ Modifies: entrypoint.py (multi-mode streaming) │
                                                    ▼
Phase 4 (API) ──────────────────────────────────────┐
  └─ Imports from Phase 1 (cancellation manager)    │
  └─ Modifies: entrypoint.py (control functions)    │
  └─ Modifies: routers/scan.py (control endpoints)  │
  └─ Endpoints: /pause, /resume, /cancel, /status   │
                                                    ▼
Phase 5 (Frontend) ─────────────────────────────────┘
  └─ Consumes API from Phase 4
  └─ UI controls for pause/resume/cancel
```

---

## Phase 1: Core Infrastructure (Complete)

**Date:** 2024-12-07

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `events.py` | 98 | EventType enum (17 types) + StreamEvent Pydantic model |
| `cancellation.py` | 108 | CancellationManager + registry pattern |
| `checkpoint.py` | 66 | get_checkpointer factory (Memory/SQLite) |
| `__init__.py` | 45 | Package exports |

### Tests Created

| File | Tests | Coverage |
|------|-------|----------|
| `test_events.py` | 17 | EventType, StreamEvent, create_event |
| `test_cancellation.py` | 18 | CancellationManager, registry functions |
| `test_checkpoint.py` | 6 | get_checkpointer, SQLITE_AVAILABLE |

**Total: 39 passed, 2 skipped** (SQLite tests skipped when package not installed)

### Key Decisions

1. **EventType as str enum**: Enables JSON serialization while keeping type safety
2. **UTC timestamps**: Using `datetime.now(UTC)` for timezone-aware timestamps
3. **Registry pattern for cancellation**: Global dict allows any component to access manager by scan_id
4. **Cooperative checkpoints**: Nodes explicitly call `await manager.checkpoint()` at safe points
5. **SQLite optional**: Graceful fallback to MemorySaver when SQLite package not installed

---

## Phase 2: Node Enhancement (Complete)

**Date:** 2024-12-07

### Files Modified

| File | Changes |
|------|---------|
| `graph/state.py` | Added `cancelled: bool` and `progress: float` fields |
| `graph/nodes/load_recon.py` | Added NODE_ENTER, SCAN_STARTED, NODE_EXIT events, cancellation check |
| `graph/nodes/check_safety.py` | Added NODE_ENTER, AGENT_START, NODE_EXIT events, cancellation check |
| `graph/nodes/plan_agent.py` | Added NODE_ENTER, PLAN_START, PLAN_COMPLETE, NODE_EXIT, SCAN_ERROR events |
| `graph/nodes/execute_agent.py` | Added full probe loop instrumentation with cancellation checkpoints |
| `graph/nodes/persist_results.py` | Added NODE_ENTER, SCAN_COMPLETE, NODE_EXIT events, cleanup |
| `graph/swarm_graph.py` | Updated all routing functions to handle `cancelled` state |
| `swarm_observability/events.py` | Added `safe_get_stream_writer()` utility |
| `swarm_observability/__init__.py` | Exported `safe_get_stream_writer` |

### Key Decisions

1. **safe_get_stream_writer**: Created wrapper that returns no-op when outside LangGraph context (enables unit testing)
2. **Progress calculation**: Agent progress = base + (agent_index / total_agents), probe progress within agent share
3. **Cancellation checkpoints**: Added before validation, between probes, after expensive operations
4. **Snapshot saving**: On cancellation in execute_agent, saves partial results for potential resumption
5. **Manager cleanup**: persist_results removes cancellation manager after scan completion

### Tests Verified

- All 41 observability tests pass
- All 33 graph tests pass
- Total: **74 tests passing**

### Key Integration Points
```python
# In each node:
from services.swarm.swarm_observability import (
    EventType, create_event, get_cancellation_manager, safe_get_stream_writer
)

writer = safe_get_stream_writer()  # Safe for tests
manager = get_cancellation_manager(state.audit_id)
```

---

## Phase 3: Entrypoint Multi-mode Streaming (Complete)

**Date:** 2024-12-07

### Files Modified

| File | Changes |
|------|---------|
| `entrypoint.py` | Added `stream_mode` and `enable_checkpointing` params, cancellation manager lifecycle |
| `graph/swarm_graph.py` | Added checkpointer support to `build_swarm_graph()` and `get_swarm_graph()` |
| `api_gateway/schemas/scan.py` | Added `ScanStreamMode` enum, new fields in `ScanStartRequest` |
| `api_gateway/routers/scan.py` | Updated to pass stream_mode and enable_checkpointing to entrypoint |

### Streaming Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `values` | Full state after each node | Legacy, events in `state.events` |
| `custom` | Only StreamWriter events | Production (default), real-time |
| `debug` | Both state and custom events | Development/debugging |

### Key Decisions

1. **Default mode is "custom"**: StreamWriter events are more granular and real-time
2. **Cancellation manager lifecycle**: Registered at scan start, cleaned up in finally block
3. **Checkpointer optional**: Passed to graph builder, enables resume capability
4. **Backwards compatible**: Old API calls without stream_mode use "custom" mode

### Usage Example
```python
# API request with streaming options
{
    "campaign_id": "test-123",
    "stream_mode": "custom",  # or "values", "debug"
    "enable_checkpointing": false
}
```

---

## Phase 4: Control Endpoints (Complete)

**Date:** 2024-12-07

### Files Modified

| File | Changes |
|------|---------|
| `entrypoint.py` | Added `cancel_scan`, `pause_scan`, `resume_scan`, `get_scan_status` helper functions |
| `api_gateway/routers/scan.py` | Added 4 control endpoints, X-Scan-Id header in streaming response |

### Endpoints Added

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scan/{scan_id}/cancel` | POST | Cancel a running scan at next checkpoint |
| `/scan/{scan_id}/pause` | POST | Pause a running scan at next checkpoint |
| `/scan/{scan_id}/resume` | POST | Resume a paused scan |
| `/scan/{scan_id}/status` | GET | Get current scan state (cancelled, paused) |

### Key Decisions

1. **scan_id is audit_id**: The scan_id used for control is the audit_id from the recon data
2. **X-Scan-Id header**: Provides a hint (campaign_id) but definitive scan_id comes from SCAN_STARTED event
3. **Not found handling**: Returns `{"found": false}` for unknown scan_ids instead of 404
4. **Synchronous control**: Control functions are sync (manager operations are thread-safe)
5. **Cooperative checkpoints**: Scans stop at the next safe point, not immediately (prevents data corruption)

### Tests

| File | Tests | Coverage |
|------|-------|----------|
| TBD | - | Control functions and endpoints |

### Usage Example
```python
# Start a scan and get the scan_id from events
# The SCAN_STARTED event contains the audit_id

# Pause the scan
response = requests.post(f"/scan/{scan_id}/pause")
# {"scan_id": "...", "paused": true}

# Check status
response = requests.get(f"/scan/{scan_id}/status")
# {"scan_id": "...", "found": true, "cancelled": false, "paused": true}

# Resume
response = requests.post(f"/scan/{scan_id}/resume")
# {"scan_id": "...", "paused": false}

# Or cancel
response = requests.post(f"/scan/{scan_id}/cancel")
# {"scan_id": "...", "cancelled": true}
```

### Response Schema

```python
# Success response (scan found)
{
    "scan_id": "audit-123",
    "found": True,           # Only in status response
    "cancelled": False,      # In cancel/status responses
    "paused": True           # In pause/resume/status responses
}

# Not found response
{
    "scan_id": "unknown-id",
    "found": False,
    "message": "Scan not found"
}
```

---

## Usage (Phase 1 API)

```python
from services.swarm.swarm_observability import (
    # Events
    StreamEvent,
    EventType,
    create_event,
    # Cancellation
    CancellationManager,
    get_cancellation_manager,
    remove_cancellation_manager,
    get_active_scan_ids,
    # Checkpoint
    get_checkpointer,
)

# Create events
event = create_event(
    EventType.NODE_PROGRESS,
    node="execute_probes",
    agent="sql_injection",
    message="Running SQL injection probes",
    progress=0.5,
)

# Manage cancellation
manager = get_cancellation_manager("scan-123")
manager.pause()   # Pause at next checkpoint
manager.resume()  # Resume execution
manager.cancel()  # Cancel execution

# In workflow nodes:
async def my_node(state):
    manager = get_cancellation_manager(state.audit_id)
    if await manager.checkpoint():
        return {"cancelled": True}  # Exit gracefully
    # ... continue processing

# Get checkpointer for LangGraph
checkpointer = get_checkpointer(persistent=False)  # MemorySaver
```

---

## Running Tests

```bash
# All observability tests
python -m pytest tests/unit/services/swarm/swarm_observability/ -v -o "addopts="

# Specific module
python -m pytest tests/unit/services/swarm/swarm_observability/test_events.py -v -o "addopts="
```

---

## Notes

- SQLite persistence requires: `pip install langgraph-checkpoint-sqlite`
- Events use timezone-aware UTC timestamps
- Registry is module-level (singleton pattern) - cleanup with `remove_cancellation_manager()`
