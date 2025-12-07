# Phase 3: Entrypoint Multi-mode Streaming

## Prerequisites
- Phase 1 Complete: `events.py`, `cancellation.py`, `checkpoint.py`
- Phase 2 Complete: Nodes instrumented with `safe_get_stream_writer()`

## Goals

1. Add multi-mode streaming support to entrypoint
2. Register cancellation manager at scan start
3. Support both legacy SSE events and new StreamWriter events
4. Enable checkpointing for state persistence

---

## 3.1 Files to Modify

| File | Changes |
|------|---------|
| `services/swarm/entrypoint.py` | Add multi-mode streaming, cancellation registration, checkpoint support |

---

## 3.2 Streaming Modes

LangGraph supports multiple streaming modes. We'll support:

| Mode | Description | Use Case |
|------|-------------|----------|
| `values` | Full state after each node | Default, legacy events in `state.events` |
| `custom` | Only StreamWriter events | Real-time progress, lighter payload |
| `debug` | Both state and custom events | Development/debugging |

---

## 3.3 Implementation

### Current Entrypoint (Before)

```python
async for state_update in graph.astream(initial_state):
    for node_name, node_output in state_update.items():
        if isinstance(node_output, dict) and "events" in node_output:
            for event in node_output["events"]:
                yield event
```

### Updated Entrypoint (After)

```python
from typing import Literal
from services.swarm.swarm_observability import (
    get_cancellation_manager,
    remove_cancellation_manager,
    get_checkpointer,
)

StreamMode = Literal["values", "custom", "debug"]

@observe()
async def execute_scan_streaming(
    request: ScanJobDispatch,
    agent_types: Optional[List[str]] = None,
    stream_mode: StreamMode = "custom",  # New parameter
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute scanning with multi-mode streaming.

    Args:
        request: Scan job dispatch with target info
        agent_types: Agent types to run
        stream_mode: Streaming mode - "values", "custom", or "debug"
            - "values": Legacy events from state.events
            - "custom": Real-time StreamWriter events only
            - "debug": Both state events and StreamWriter events
    """
    # ... existing setup code ...

    # Register cancellation manager
    manager = get_cancellation_manager(audit_id)

    # Get checkpointer for persistence
    checkpointer = get_checkpointer(persistent=False)  # or True for SQLite

    # Build initial state
    initial_state = SwarmState(
        audit_id=audit_id,
        target_url=target_url,
        agent_types=agent_types,
        recon_context=blueprint_data,
        scan_config=scan_config,
        safety_policy=safety_policy,
    )

    # Get compiled graph with checkpointer
    graph = get_swarm_graph()

    # Build config with thread_id for checkpointing
    config = {
        "configurable": {
            "thread_id": audit_id,
        }
    }

    try:
        if stream_mode == "values":
            # Legacy mode: events from state accumulator
            async for state_update in graph.astream(
                initial_state,
                config=config,
            ):
                for node_name, node_output in state_update.items():
                    if isinstance(node_output, dict) and "events" in node_output:
                        for event in node_output["events"]:
                            yield event

        elif stream_mode == "custom":
            # Custom mode: StreamWriter events only
            async for event in graph.astream(
                initial_state,
                config=config,
                stream_mode="custom",
            ):
                # StreamWriter events come through directly
                yield event

        elif stream_mode == "debug":
            # Debug mode: Both state events and StreamWriter events
            async for chunk in graph.astream(
                initial_state,
                config=config,
                stream_mode=["values", "custom"],
            ):
                if isinstance(chunk, tuple):
                    mode, data = chunk
                    if mode == "custom":
                        yield data
                    elif mode == "values":
                        for node_name, node_output in data.items():
                            if isinstance(node_output, dict) and "events" in node_output:
                                for event in node_output["events"]:
                                    yield {"_mode": "state", **event}
                else:
                    yield chunk

    except Exception as e:
        logger.error(f"Graph execution error: {e}", exc_info=True)
        yield {
            "type": "log",
            "level": "error",
            "message": f"Scan failed: {e}",
        }
    finally:
        # Cleanup cancellation manager
        remove_cancellation_manager(audit_id)
```

---

## 3.4 Checkpointer Integration

To enable state persistence (for resuming cancelled scans):

```python
# In build_swarm_graph() or get_swarm_graph()
from services.swarm.swarm_observability import get_checkpointer

def build_swarm_graph(checkpointer=None) -> StateGraph:
    """Build the Swarm scanning graph with optional checkpointing."""
    graph = StateGraph(SwarmState)

    # ... add nodes and edges ...

    # Compile with checkpointer
    return graph.compile(checkpointer=checkpointer)


def get_swarm_graph(checkpointer=None) -> StateGraph:
    """Get compiled graph, optionally with checkpointer."""
    global _graph
    if _graph is None or checkpointer is not None:
        logger.info("Building Swarm graph...")
        _graph = build_swarm_graph(checkpointer)
        logger.info("Swarm graph built successfully")
    return _graph
```

---

## 3.5 API Router Updates

Update the scan router to accept stream mode:

```python
# In routers/scans.py

class ScanStreamMode(str, Enum):
    VALUES = "values"
    CUSTOM = "custom"
    DEBUG = "debug"

@router.post("/scan/stream")
async def stream_scan(
    request: ScanRequest,
    stream_mode: ScanStreamMode = ScanStreamMode.CUSTOM,
):
    """Stream scan results with configurable mode."""
    async def event_stream():
        async for event in execute_scan_streaming(
            request.dispatch,
            agent_types=request.agent_types,
            stream_mode=stream_mode.value,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )
```

---

## 3.6 Event Format

### Legacy Events (stream_mode="values")
From `state.events` accumulator:
```json
{
  "type": "probe_result",
  "agent": "sql",
  "probe_name": "sqli_tautology",
  "status": "fail"
}
```

### StreamWriter Events (stream_mode="custom")
From `safe_get_stream_writer()`:
```json
{
  "type": "probe_result",
  "timestamp": "2024-12-07T12:00:00Z",
  "node": "execute_agent",
  "agent": "sql",
  "progress": 0.45,
  "data": {
    "probe_name": "sqli_tautology",
    "status": "fail",
    "detector_score": 0.95
  }
}
```

---

## Done When

- [x] Entrypoint supports `stream_mode` parameter
- [x] Cancellation manager registered at scan start
- [x] Cancellation manager cleaned up in `finally` block
- [x] Legacy "values" mode works as before
- [x] New "custom" mode streams only StreamWriter events
- [x] "debug" mode combines both for development
- [x] API router updated to accept stream mode
- [x] Checkpointer optionally enabled for persistence

---

## Testing

```bash
# Test all streaming modes
python -m pytest tests/unit/services/swarm/ -v -o "addopts=" -k "entrypoint or stream"

# Manual test with curl
curl -N "http://localhost:8000/api/v1/scan/stream?stream_mode=custom" \
  -H "Content-Type: application/json" \
  -d '{"target_url": "http://test.com", "campaign_id": "test-123"}'
```

---

## Next Phase

After Phase 3, proceed to Phase 4: Control Endpoints (PHASE_4_API.md)
