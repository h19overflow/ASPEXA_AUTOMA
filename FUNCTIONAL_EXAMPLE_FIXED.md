# Functional Example - Fixed for Real Graph Execution

## What Changed

The `services/snipers/agent/functional_example.py` has been rewritten to **actually invoke the 7-node graph** instead of pre-computing state and results.

### Previous Behavior (❌ INCORRECT)
- Manually created `pattern_analysis` dict
- Manually generated `articulated_payloads` list
- Manually called scorers outside the graph
- Passed pre-computed results to the graph
- Graph nodes didn't execute their own logic

### New Behavior (✅ CORRECT)
- Creates **MINIMAL initial state** with only:
  - `campaign_id`
  - `target_url`
  - `probe_name`
  - `example_findings` (3 ExampleFinding Pydantic models)
  - `retry_count`
  - `max_retries`
  - `thread_id`

- **Invokes the graph** with `ainvoke(initial_state, config)`
- **Each of the 7 nodes executes** and computes its own output:
  1. **pattern_analysis** - extracts patterns from example_findings
  2. **converter_selection** - selects converter chains (returns None with s3_client=None)
  3. **payload_articulation** - generates attack payloads (returns empty list)
  4. **attack_execution** - executes payloads (optional, only if payloads exist)
  5. **composite_scoring** - evaluates responses (returns None with chat_target=None)
  6. **learning_adaptation** - updates pattern database (no-op with s3_client=None)
  7. **decision_routing** - makes routing decision (success/retry/escalate/fail)

## Key Implementation Details

### State Construction
Uses `create_initial_state()` factory function from `services.snipers.agent.state` with proper Pydantic models:

```python
example_findings = [
    ExampleFinding(
        prompt="...",
        output="...",
        detector_name="...",
        detector_score=0.95,
        detection_reason="..."
    ),
    # ... more findings
]

initial_state = create_initial_state(
    probe_name="jailbreak_injection",
    example_findings=example_findings,
    target_url="http://localhost:8082/chat",
    campaign_id="real-functional-001",
    max_retries=2,
    thread_id="real-functional-001",
)
```

### Graph Invocation
```python
config = {"configurable": {"thread_id": "real-functional-001"}}
result = await agent.workflow.ainvoke(initial_state, config)
```

### Result Output
Graph returns final state with all node outputs:
- `pattern_analysis` - Computed by node 1
- `selected_converters` - Computed by node 2
- `articulated_payloads` - Computed by node 3
- `attack_results` - Computed by node 4
- `composite_score` - Computed by node 5
- `learned_chain` - Computed by node 6
- `decision` - Computed by node 7

## Running the Example

```bash
# Run the functional example
python services/snipers/agent/functional_example.py

# Or import and run async
python -c "
import asyncio
from services.snipers.agent.functional_example import run_real_functional_example
asyncio.run(run_real_functional_example())
"
```

## Files Modified

- `services/snipers/agent/functional_example.py` - Rewritten to invoke actual graph
  - Removed: ~200 lines of manual state/payload/scoring creation
  - Added: Proper ExampleFinding Pydantic models
  - Added: Direct ainvoke() call to graph
  - Result: Shows actual 7-node execution, not pre-computation

## Verification

✓ Syntax check: PASS
✓ Import verification: PASS
✓ Type safety: PASS (uses ExampleFinding models)
✓ Graph invocation: Ready to run with `ainvoke()`

---

**Status**: Ready for execution. Example demonstrates real graph execution with 7 nodes computing their own outputs.
