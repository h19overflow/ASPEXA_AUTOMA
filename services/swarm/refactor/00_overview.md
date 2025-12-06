# Swarm Service Refactor Overview

## Current Problems

### 1. Tangled Responsibilities
- `schema.py` does data transformation (80+ lines in `from_scan_job`)
- `base.py` mixes agent creation, execution, and context management
- `tools.py` has context vars that create hidden state
- `entrypoint.py` is 400 lines of procedural orchestration

### 2. Over-Engineering
- Factory pattern for 3 agents that are nearly identical
- `ToolContext` + `set_tool_context` + `_get_tool_context` = hidden global state
- `base_utils.py` exists only to break circular imports
- Multiple schema classes for the same data (`ScanInput`, `ScanContext`, `ScanConfig`)

### 3. Garak Scanner Sprawl
- `detectors.py` - loads detectors (useful)
- `rate_limiter.py` - token bucket (may not be needed)
- `report_parser.py` - formats reports (useful)
- `websocket_generator.py` - WS support (rarely used)
- `scanner.py` - actual execution (core)
- `models.py` - event types (useful)
- `utils.py` - helpers (consolidate)

### 4. No Clear Flow
Current flow is procedural spaghetti:
```
entrypoint -> run_planning_agent -> create_planning_agent -> tools -> scanner -> persist
```

## Target Architecture

### Simple Mental Model
```
Recon -> Agent Selection -> Probe Planning -> Probe Execution -> Report Persistence
```

### Directory Structure (Target)
```
services/swarm/
├── agents/
│   ├── sql/
│   │   ├── __init__.py
│   │   ├── sql_agent.py          # Agent class
│   │   ├── sql_prompt.py         # System prompt
│   │   └── sql_probes.py         # Probe configuration
│   ├── auth/
│   │   └── ...
│   └── jailbreak/
│       └── ...
├── scanner/                       # Renamed from garak_scanner
│   ├── __init__.py
│   ├── executor.py               # Probe execution
│   ├── detectors.py              # Detection logic
│   └── models.py                 # Event types
├── persistence/
│   └── s3_adapter.py
├── graph/
│   ├── __init__.py
│   ├── state.py                  # Graph state definition
│   ├── nodes.py                  # Graph nodes
│   └── swarm_graph.py            # LangGraph definition
├── schemas.py                    # Simplified schemas
└── entrypoint.py                 # Thin HTTP layer
```

## Refactor Phases

| Phase | File | Focus |
|-------|------|-------|
| 1 | `01_agent_restructure.md` | Each agent gets own directory |
| 2 | `02_scanner_simplification.md` | Consolidate garak_scanner |
| 3 | `03_graph_orchestration.md` | Replace procedural with LangGraph |
| 4 | `04_cleanup.md` | Remove dead code, simplify schemas |

## Success Criteria

1. **KISS**: New dev understands flow in 5 minutes
2. **SRP**: Each file has one job
3. **Testable**: Each component mockable
4. **Observable**: Clear logging at each step
5. **Extensible**: Adding new agent = new directory + probe config
