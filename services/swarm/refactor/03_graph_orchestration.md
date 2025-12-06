# Phase 3: Graph-Based Orchestration

## Problem

Current `entrypoint.py` is 400 lines of procedural code:
```python
async def execute_scan_streaming(...):
    # Load blueprint (20 lines)
    # For each agent (nested loops)
        # Check safety policy (10 lines)
        # Build context (10 lines)
        # PHASE 1: Planning (50 lines)
        # PHASE 2: Execution (100 lines)
        # Persistence (30 lines)
    # Yield complete
```

Issues:
- Hard to test individual phases
- State management via local variables
- Error handling scattered throughout
- No clear state machine

## Target Architecture

Use LangGraph to define clear states and transitions:

```
                    ┌─────────────┐
                    │    START    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ LOAD_RECON  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌───▼───┐ ┌──────▼──────┐
       │  SQL_PLAN   │ │ AUTH  │ │  JAILBREAK  │
       └──────┬──────┘ │ _PLAN │ │   _PLAN     │
              │        └───┬───┘ └──────┬──────┘
       ┌──────▼──────┐     │            │
       │ SQL_EXECUTE │     │            │
       └──────┬──────┘     │            │
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │   PERSIST   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │     END     │
                    └─────────────┘
```

## Implementation

### Step 1: Define State

```python
# graph/state.py
"""
Graph state definition for Swarm scanning.

Purpose: Define typed state passed between graph nodes
Dependencies: pydantic, typing
"""
from typing import Dict, List, Any, Optional, Annotated
from pydantic import BaseModel, Field
from operator import add


class AgentResult(BaseModel):
    """Result from a single agent."""
    agent_type: str
    status: str  # 'success', 'failed', 'blocked', 'error'
    plan: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = Field(default_factory=list)
    vulnerabilities_found: int = 0
    error: Optional[str] = None


class SwarmState(BaseModel):
    """State passed through the scanning graph.

    Accumulates results as graph executes.
    """
    # Input
    audit_id: str
    target_url: str
    agent_types: List[str]
    recon_context: Dict[str, Any] = Field(default_factory=dict)
    scan_config: Dict[str, Any] = Field(default_factory=dict)

    # Progress
    current_agent_index: int = 0

    # Accumulator (uses reducer to append)
    agent_results: Annotated[List[AgentResult], add] = Field(default_factory=list)
    events: Annotated[List[Dict[str, Any]], add] = Field(default_factory=list)

    # Error tracking
    errors: List[str] = Field(default_factory=list)

    @property
    def current_agent(self) -> Optional[str]:
        """Get current agent type being processed."""
        if self.current_agent_index < len(self.agent_types):
            return self.agent_types[self.current_agent_index]
        return None

    @property
    def is_complete(self) -> bool:
        """Check if all agents have been processed."""
        return self.current_agent_index >= len(self.agent_types)
```

### Step 2: Define Nodes

```python
# graph/nodes.py
"""
Graph nodes for Swarm scanning.

Purpose: Define individual steps in the scanning flow
Dependencies: graph.state, agents, scanner
"""
import logging
from typing import Dict, Any

from libs.contracts.recon import ReconBlueprint
from .state import SwarmState, AgentResult
from ..agents import get_agent
from ..scanner import ProbeExecutor, HTTPGenerator
from ..persistence.s3_adapter import persist_garak_result

logger = logging.getLogger(__name__)


async def load_recon(state: SwarmState) -> Dict[str, Any]:
    """Load and validate recon data.

    Node: LOAD_RECON
    """
    events = []

    events.append({
        "type": "log",
        "message": f"Loading recon for audit: {state.audit_id}"
    })

    # Validate recon context
    if not state.recon_context:
        return {
            "errors": ["No recon context provided"],
            "events": events,
        }

    # Extract key intelligence
    try:
        blueprint = ReconBlueprint(**state.recon_context)
        events.append({
            "type": "log",
            "message": f"Recon loaded: {len(blueprint.intelligence.detected_tools or [])} tools detected"
        })
    except Exception as e:
        return {
            "errors": [f"Invalid recon: {e}"],
            "events": events,
        }

    return {"events": events}


async def plan_agent(state: SwarmState) -> Dict[str, Any]:
    """Run planning for current agent.

    Node: {AGENT}_PLAN
    """
    agent_type = state.current_agent
    events = []

    events.append({
        "type": "plan_start",
        "agent": agent_type,
    })

    try:
        # Get agent instance
        agent = get_agent(agent_type)

        # Run planning
        plan = await agent.plan(state.recon_context)

        events.append({
            "type": "plan_complete",
            "agent": agent_type,
            "probes": plan.probes,
            "generations": plan.generations,
        })

        # Store plan in state for execution
        return {
            "events": events,
            # Plan stored for execute_agent to use
            "_current_plan": plan.model_dump(),
        }

    except Exception as e:
        logger.error(f"Planning failed for {agent_type}: {e}")
        return {
            "agent_results": [AgentResult(
                agent_type=agent_type,
                status="failed",
                error=str(e),
            )],
            "events": events + [{
                "type": "error",
                "agent": agent_type,
                "phase": "planning",
                "message": str(e),
            }],
            "current_agent_index": state.current_agent_index + 1,
        }


async def execute_agent(state: SwarmState) -> Dict[str, Any]:
    """Execute probes for current agent.

    Node: {AGENT}_EXECUTE
    """
    agent_type = state.current_agent
    events = []
    results = []

    # Get plan from previous node
    plan = state.get("_current_plan")
    if not plan:
        return {
            "agent_results": [AgentResult(
                agent_type=agent_type,
                status="failed",
                error="No plan available",
            )],
            "current_agent_index": state.current_agent_index + 1,
        }

    events.append({
        "type": "execution_start",
        "agent": agent_type,
    })

    try:
        # Create generator and executor
        generator = HTTPGenerator(
            endpoint_url=state.target_url,
            headers=state.scan_config.get("headers", {}),
            timeout=state.scan_config.get("timeout", 30),
        )
        executor = ProbeExecutor(generator)

        # Execute and collect results
        pass_count = 0
        fail_count = 0

        async for event in executor.execute(
            probes=plan["probes"],
            generations=plan["generations"],
        ):
            # Convert to dict and add to events
            event_dict = event.model_dump()
            event_dict["agent"] = agent_type
            events.append(event_dict)

            # Track results
            if hasattr(event, "status"):
                results.append(event_dict)
                if event.status == "pass":
                    pass_count += 1
                elif event.status == "fail":
                    fail_count += 1

        generator.close()

        return {
            "agent_results": [AgentResult(
                agent_type=agent_type,
                status="success",
                plan=plan,
                results=results,
                vulnerabilities_found=fail_count,
            )],
            "events": events,
            "current_agent_index": state.current_agent_index + 1,
        }

    except Exception as e:
        logger.error(f"Execution failed for {agent_type}: {e}")
        return {
            "agent_results": [AgentResult(
                agent_type=agent_type,
                status="error",
                error=str(e),
            )],
            "events": events,
            "current_agent_index": state.current_agent_index + 1,
        }


async def persist_results(state: SwarmState) -> Dict[str, Any]:
    """Persist all results to S3.

    Node: PERSIST
    """
    events = []

    for result in state.agent_results:
        if result.status == "success":
            try:
                await persist_garak_result(
                    campaign_id=state.audit_id,
                    scan_id=f"garak-{state.audit_id}-{result.agent_type}",
                    garak_report={
                        "audit_id": state.audit_id,
                        "agent_type": result.agent_type,
                        "results": result.results,
                        "vulnerabilities_found": result.vulnerabilities_found,
                    },
                    target_url=state.target_url,
                )
                events.append({
                    "type": "log",
                    "message": f"Persisted results for {result.agent_type}",
                })
            except Exception as e:
                events.append({
                    "type": "log",
                    "level": "warning",
                    "message": f"Failed to persist {result.agent_type}: {e}",
                })

    events.append({"type": "complete", "data": state.model_dump()})

    return {"events": events}
```

### Step 3: Build Graph

```python
# graph/swarm_graph.py
"""
LangGraph definition for Swarm scanning.

Purpose: Define the scanning workflow as a state machine
Dependencies: langgraph, graph.state, graph.nodes
"""
from langgraph.graph import StateGraph, END

from .state import SwarmState
from .nodes import load_recon, plan_agent, execute_agent, persist_results


def should_continue(state: SwarmState) -> str:
    """Determine next node based on state."""
    if state.errors:
        return "persist"  # Go to persist even on error
    if state.is_complete:
        return "persist"
    return "plan"


def build_swarm_graph() -> StateGraph:
    """Build the Swarm scanning graph.

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(SwarmState)

    # Add nodes
    graph.add_node("load_recon", load_recon)
    graph.add_node("plan", plan_agent)
    graph.add_node("execute", execute_agent)
    graph.add_node("persist", persist_results)

    # Add edges
    graph.set_entry_point("load_recon")
    graph.add_edge("load_recon", "plan")
    graph.add_edge("plan", "execute")
    graph.add_conditional_edges(
        "execute",
        should_continue,
        {
            "plan": "plan",
            "persist": "persist",
        }
    )
    graph.add_edge("persist", END)

    return graph.compile()


# Singleton instance
_graph = None

def get_swarm_graph() -> StateGraph:
    """Get or create the Swarm graph."""
    global _graph
    if _graph is None:
        _graph = build_swarm_graph()
    return _graph
```

### Step 4: Thin Entrypoint

```python
# entrypoint.py (NEW - simplified)
"""
HTTP entrypoint for Swarm scanning service.

Purpose: Thin HTTP layer that invokes the graph
Dependencies: graph.swarm_graph
"""
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from libs.contracts.scanning import ScanJobDispatch
from .graph import get_swarm_graph, SwarmState

logger = logging.getLogger(__name__)


async def execute_scan_streaming(
    request: ScanJobDispatch,
    agent_types: Optional[List[str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute scanning with streaming events.

    Thin wrapper that:
    1. Builds initial state from request
    2. Invokes graph
    3. Yields events from state
    """
    if agent_types is None:
        agent_types = ["sql", "auth", "jailbreak"]

    # Build initial state
    initial_state = SwarmState(
        audit_id=request.blueprint_context.get("audit_id", "unknown"),
        target_url=request.target_url or "https://api.target.local/v1/chat",
        agent_types=agent_types,
        recon_context=request.blueprint_context or {},
        scan_config={
            "approach": request.scan_config.approach,
            "headers": {},
            "timeout": request.scan_config.request_timeout,
        },
    )

    yield {"type": "log", "message": f"Starting scan with {len(agent_types)} agents"}

    # Run graph
    graph = get_swarm_graph()

    async for state_update in graph.astream(initial_state):
        # Yield events from state updates
        if "events" in state_update:
            for event in state_update["events"]:
                yield event

    yield {"type": "log", "message": "Scan complete"}
```

## Benefits

1. **Testable**: Each node is a pure function
2. **Observable**: State is explicit, can log at each transition
3. **Resumable**: Could persist state for pause/resume
4. **Extensible**: Add new agents = add new nodes
5. **Debuggable**: LangGraph has built-in tracing

## Migration Checklist

- [ ] Create `graph/` directory
- [ ] Create `graph/state.py`
- [ ] Create `graph/nodes.py`
- [ ] Create `graph/swarm_graph.py`
- [ ] Create new thin `entrypoint.py`
- [ ] Update API gateway to use new entrypoint
- [ ] Add tests for each node
- [ ] Delete old `entrypoint.py`

## Testing Strategy

```python
# tests/unit/services/swarm/graph/test_nodes.py
import pytest
from services.swarm.graph.state import SwarmState
from services.swarm.graph.nodes import load_recon, plan_agent


@pytest.mark.asyncio
async def test_load_recon_success():
    state = SwarmState(
        audit_id="test-001",
        target_url="http://localhost:8000",
        agent_types=["sql"],
        recon_context={"audit_id": "test-001", "intelligence": {}},
    )

    result = await load_recon(state)

    assert "errors" not in result or len(result["errors"]) == 0
    assert len(result["events"]) > 0


@pytest.mark.asyncio
async def test_load_recon_missing_context():
    state = SwarmState(
        audit_id="test-001",
        target_url="http://localhost:8000",
        agent_types=["sql"],
        recon_context={},  # Empty
    )

    result = await load_recon(state)

    assert len(result["errors"]) > 0
```
