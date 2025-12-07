# Phase 2: Node Enhancement

## Prerequisites
- Phase 1 Complete: `events.py`, `cancellation.py`, `checkpoint.py`

## Files to Modify

| File | Changes |
|------|---------|
| `graph/state.py` | Add `scan_id`, `cancelled`, `progress` fields |
| `graph/nodes/*.py` | Add `get_stream_writer()` calls to each node |

---

## 2.1 State Enhancement

### Current State (from `graph/state.py`)
The `SwarmState` already has:
- `audit_id` - can be used as scan_id for cancellation manager
- `events: Annotated[List[Dict], add]` - accumulator for SSE events
- `current_agent_index` - for progress calculation

### Fields to Add to `SwarmState`:

```python
# Add these fields to SwarmState class in graph/state.py

# Observability fields
cancelled: bool = Field(
    default=False,
    description="Whether scan was cancelled by user"
)
progress: float = Field(
    default=0.0,
    ge=0.0,
    le=1.0,
    description="Overall scan progress (0.0-1.0)"
)
```

### Note on scan_id
Use existing `audit_id` as the scan identifier for `get_cancellation_manager(state.audit_id)`.

---

## 2.2 Node Pattern

Each node should follow this pattern:

```python
from langgraph.config import get_stream_writer
from services.swarm.swarm_observability import (
    StreamEvent,
    EventType,
    create_event,
    get_cancellation_manager,
)


async def example_node(state: SwarmState) -> dict:
    """Node with observability instrumentation."""
    writer = get_stream_writer()
    manager = get_cancellation_manager(state.audit_id)

    # 1. Emit NODE_ENTER
    writer(create_event(
        EventType.NODE_ENTER,
        node="example_node",
        message="Starting example node",
    ).model_dump())

    # 2. Check cancellation at safe points
    if await manager.checkpoint():
        writer(create_event(
            EventType.SCAN_CANCELLED,
            node="example_node",
            message="Scan cancelled by user",
        ).model_dump())
        return {"cancelled": True}

    # 3. Do work with progress updates
    for i, item in enumerate(items):
        progress = i / len(items)
        writer(create_event(
            EventType.NODE_PROGRESS,
            node="example_node",
            progress=progress,
            data={"current_item": i, "total": len(items)},
        ).model_dump())

        # Process item...

        # Check cancellation in loops
        if await manager.checkpoint():
            return {"cancelled": True}

    # 4. Emit NODE_EXIT
    writer(create_event(
        EventType.NODE_EXIT,
        node="example_node",
        message="Completed example node",
        progress=1.0,
    ).model_dump())

    return {"result": result}
```

---

## 2.3 Nodes to Instrument

Find all graph nodes and add observability. Typical nodes:

| Node | Events to Emit |
|------|----------------|
| `recon` | NODE_ENTER, NODE_EXIT |
| `check_safety` | NODE_ENTER, NODE_EXIT |
| `plan_agent` | NODE_ENTER, PLAN_START, PLAN_COMPLETE, NODE_EXIT |
| `execute_agent` | NODE_ENTER, PROBE_START, PROBE_RESULT, PROBE_COMPLETE, NODE_EXIT |
| `persist` | NODE_ENTER, NODE_EXIT |

### execute_agent Special Handling

This node runs probes in a loop - needs cancellation checks:

```python
async def execute_agent(state: SwarmState) -> dict:
    writer = get_stream_writer()
    manager = get_cancellation_manager(state.audit_id)
    agent_type = state.current_agent

    writer(create_event(
        EventType.NODE_ENTER,
        node="execute_agent",
        agent=agent_type,
    ).model_dump())

    writer(create_event(
        EventType.AGENT_START,
        agent=agent_type,
        data={"plan": state.current_plan},
    ).model_dump())

    probes = get_probes_from_plan(state.current_plan)
    results = []

    for i, probe in enumerate(probes):
        # Check cancellation before each probe
        if await manager.checkpoint():
            manager.save_snapshot({
                "agent": agent_type,
                "completed_probes": i,
                "results": results,
            })
            return {"cancelled": True}

        progress = i / len(probes)
        writer(create_event(
            EventType.PROBE_START,
            agent=agent_type,
            data={"probe": probe.name, "index": i},
            progress=progress,
        ).model_dump())

        result = await run_probe(probe)
        results.append(result)

        writer(create_event(
            EventType.PROBE_RESULT,
            agent=agent_type,
            data={"status": result.status, "vulnerable": result.vulnerable},
        ).model_dump())

    writer(create_event(
        EventType.PROBE_COMPLETE,
        agent=agent_type,
        data={"total_probes": len(probes), "results_count": len(results)},
    ).model_dump())

    writer(create_event(
        EventType.AGENT_COMPLETE,
        agent=agent_type,
    ).model_dump())

    writer(create_event(
        EventType.NODE_EXIT,
        node="execute_agent",
    ).model_dump())

    return {"agent_results": [AgentResult(...)]}
```

---

## 2.4 Import Updates

Add to each node file:

```python
from langgraph.config import get_stream_writer
from services.swarm.swarm_observability import (
    EventType,
    create_event,
    get_cancellation_manager,
)
```

---

## 2.5 Routing Updates

Update routing functions to check `cancelled` state:

```python
def route_after_execute(state: SwarmState) -> str:
    if state.cancelled:
        return "persist"  # Save partial results
    if state.has_fatal_error:
        return "persist"
    if state.is_complete:
        return "persist"
    return "plan_agent"  # Next agent
```

---

## Done When

- [ ] `SwarmState` has `cancelled` and `progress` fields
- [ ] All nodes emit `NODE_ENTER` and `NODE_EXIT` events
- [ ] `execute_agent` checks cancellation before each probe
- [ ] `execute_agent` emits `PROBE_START`, `PROBE_RESULT`, `PROBE_COMPLETE`
- [ ] Routing functions handle `cancelled` state
- [ ] Unit tests updated for new state fields
- [ ] Integration test verifies events are emitted

---

## Testing

```bash
# After implementation, run:
python -m pytest tests/unit/services/swarm/ -v -o "addopts=" -k "node or state"
```

## Next Phase
After Phase 2, proceed to Phase 3: Entrypoint Multi-mode Streaming (PHASE_3_STREAM.md)
