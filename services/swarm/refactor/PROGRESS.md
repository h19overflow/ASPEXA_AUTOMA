# Refactoring Progress

## Completed

### Phase 1: Agent Restructure (01_agent_restructure.md)
- Created `agents/base_agent.py` with `BaseAgent` ABC and `ProbePlan` schema
- Created `agents/sql/` directory:
  - `sql_agent.py` - SQLAgent class using LangChain v1 `create_agent`
  - `sql_prompt.py` - System prompt for SQL agent
  - `sql_probes.py` - Probe configuration
  - `sql_tools.py` - LangChain tools (analyze_sql_infrastructure, get_sql_probe_list)
- Created `agents/auth/` directory (same structure)
- Created `agents/jailbreak/` directory (same structure)
- Updated `agents/__init__.py` with `AGENT_REGISTRY` and `get_agent()` factory
- Maintained backward compatibility with legacy imports

### Phase 2: Scanner Simplification (02_scanner_simplification.md) - COMPLETED
- Created `garak_scanner/execution/` package:
  - `scanner.py` - Main GarakScanner class (updated imports)
  - `probe_loader.py` - Probe loading utilities
  - `__init__.py` - Package exports
- Created `garak_scanner/generators/` package:
  - `rate_limiter.py` - Token bucket rate limiter
  - `websocket_generator.py` - WebSocket generator
  - `__init__.py` - Exports HTTPGenerator, WebSocketGenerator, RateLimiter
- Created `garak_scanner/detection/` package:
  - `detectors.py` - load_detector, run_detectors_on_attempt
  - `triggers.py` - get_detector_triggers
  - `__init__.py` - Package exports
- Created `garak_scanner/reporting/` package:
  - `report_parser.py` - Report generation functions
  - `formatters.py` - get_category_for_probe, get_severity
  - `__init__.py` - Package exports

#### Phase 2 Finalization (2025-12-06)

**What Changed:**

1. **Updated `garak_scanner/__init__.py`** - Now imports from new sub-packages:
   - `from .execution import GarakScanner, get_scanner, load_probe, get_probe_prompts`
   - `from .generators import HTTPGenerator, WebSocketGenerator, RateLimiter`
   - `from .detection import load_detector, run_detectors_on_attempt, get_detector_triggers`
   - `from .reporting import parse_results_to_clusters, format_scan_results, ...`
   - Added `HttpGenerator = HTTPGenerator` alias for backward compatibility

2. **Updated `garak_scanner/utils.py`** - Changed import:
   - From: `from .detectors import get_detector_triggers, run_detectors_on_attempt`
   - To: `from .detection import get_detector_triggers, run_detectors_on_attempt`

3. **Deleted old flat files** (replaced by sub-packages):
   - `garak_scanner/scanner.py` → moved to `execution/scanner.py`
   - `garak_scanner/detectors.py` → moved to `detection/detectors.py` + `triggers.py`
   - `garak_scanner/rate_limiter.py` → moved to `generators/rate_limiter.py`
   - `garak_scanner/websocket_generator.py` → moved to `generators/websocket_generator.py`
   - `garak_scanner/report_parser.py` → moved to `reporting/report_parser.py`

4. **Fixed external imports** that referenced old locations:
   - `libs/connectivity/adapters/pyrit_targets.py`:
     - From: `from services.swarm.garak_scanner.websocket_generator import WebSocketGenerator`
     - To: `from services.swarm.garak_scanner.generators import WebSocketGenerator`
   - `services/swarm/entrypoint.py`:
     - From: `from services.swarm.garak_scanner.scanner import get_scanner`
     - To: `from services.swarm.garak_scanner import get_scanner`

5. **Updated test imports**:
   - `tests/unit/services/swarm/test_aggregator.py`:
     - From: `from services.swarm.garak_scanner.report_parser import ...`
     - To: `from services.swarm.garak_scanner.reporting import ...`
   - `tests/unit/services/swarm/garak_scanner/test_detectors.py`:
     - From: `from services.swarm.garak_scanner.detectors import ...`
     - To: `from services.swarm.garak_scanner.detection import ...`
     - Updated all `@patch` decorators to use new path: `services.swarm.garak_scanner.detection.detectors`

**Verification:**
- All imports verified working via Python import test
- Backward compatibility maintained via root `__init__.py` re-exports

### Phase 3: Graph Orchestration (03_graph_orchestration.md) - COMPLETED

**What Changed (2025-12-06):**

1. **Created `graph/` package** with modular node structure:
   - `graph/__init__.py` - Package exports (SwarmState, AgentResult, get_swarm_graph)
   - `graph/state.py` - State definitions with LangGraph reducers
   - `graph/swarm_graph.py` - LangGraph StateGraph workflow with routing logic
   - `graph/nodes/` - Individual node modules for SRP compliance:
     - `load_recon.py` - Validate and load recon blueprint
     - `check_safety.py` - Safety policy enforcement
     - `plan_agent.py` - LLM planning phase
     - `execute_agent.py` - Scanner execution with streaming
     - `persist_results.py` - S3 persistence

2. **Replaced `entrypoint.py`** (from ~400 lines to ~145 lines):
   - Now a thin HTTP layer that builds initial state and invokes graph
   - Graph handles all orchestration logic via state machine
   - Events streamed from graph state updates

3. **Graph Architecture:**
   ```
   START -> load_recon -> check_safety -> plan -> execute -> check_safety (loop)
                              |                       |
                              v                       v
                           persist <-----------------+
                              |
                             END
   ```

4. **Added comprehensive tests** (33 tests, all passing):
   - `tests/unit/services/swarm/graph/test_state.py` - State model tests
   - `tests/unit/services/swarm/graph/test_load_recon.py` - Recon node tests
   - `tests/unit/services/swarm/graph/test_check_safety.py` - Safety node tests
   - `tests/unit/services/swarm/graph/test_swarm_graph.py` - Graph routing tests
   - `tests/unit/services/swarm/graph/conftest.py` - Fixtures for valid recon data

**Verification:**
- All imports verified working
- All 33 tests passing
- Backward compatibility maintained

### Phase 4: Cleanup (04_cleanup.md) - COMPLETED

**What Changed (2025-12-06):**

1. **Deleted dead code files:**
   - `agents/trinity.py` - Deprecated wrappers, now inlined in `__init__.py`
   - `agents/base_utils.py` - Functionality inlined into `agents/base.py`

2. **Refactored `agents/base.py`:**
   - Inlined `extract_plan_from_result()` and `build_planning_input()` functions
   - Simplified `run_scanning_agent()` deprecated wrapper
   - Removed dependency on `base_utils.py`

3. **Updated `agents/__init__.py`:**
   - Removed imports from deleted files
   - Trinity agent wrappers (`run_sql_agent`, etc.) now defined directly
   - Maintains backward compatibility for legacy code

4. **Simplified `core/schema.py`:**
   - Removed unused `ProbeResultDetail` class
   - Removed unused `ScanPlanResponse` class
   - Reduced from 477 lines to 434 lines

5. **Config already consolidated** (done in earlier phase):
   - `core/enums.py` - Contains `AgentType`, `ScanApproach`, `VulnCategory`
   - `core/constants.py` - Contains `PROBE_MAP`, `PROBE_DESCRIPTIONS`, etc.
   - `core/config.py` - Re-exports for backward compatibility

**Files Deleted:**
- `services/swarm/agents/trinity.py`
- `services/swarm/agents/base_utils.py`

**Verification:**
- All 199 swarm unit tests passing
- All imports verified working
- Backward compatibility maintained via `__init__.py` re-exports

## Directory Structure After Phase 4

```
services/swarm/
├── entrypoint.py              # Thin HTTP layer (145 lines)
├── core/
│   ├── __init__.py            # Re-exports
│   ├── config.py              # Re-exports from enums/constants
│   ├── enums.py               # AgentType, ScanApproach, VulnCategory
│   ├── constants.py           # PROBE_MAP, PROBE_DESCRIPTIONS, etc.
│   ├── schema.py              # Simplified (434 lines)
│   └── utils.py               # Logging utilities
├── graph/                     # LangGraph orchestration
│   ├── __init__.py
│   ├── state.py              # SwarmState, AgentResult
│   ├── swarm_graph.py        # StateGraph definition
│   └── nodes/
│       ├── __init__.py
│       ├── load_recon.py
│       ├── check_safety.py
│       ├── plan_agent.py
│       ├── execute_agent.py
│       └── persist_results.py
├── garak_scanner/            # Scanning infrastructure
│   ├── execution/
│   ├── generators/
│   ├── detection/
│   └── reporting/
└── agents/                   # Agent implementations
    ├── __init__.py           # AGENT_REGISTRY, get_agent(), legacy wrappers
    ├── base_agent.py         # BaseAgent ABC
    ├── base.py               # run_planning_agent, create_planning_agent
    ├── tools.py              # PLANNING_TOOLS
    ├── prompts/              # System prompts
    ├── sql/
    ├── auth/
    └── jailbreak/
```

## Historical Directory Structures

### Directory Structure After Phase 2

```
garak_scanner/
├── __init__.py                 # Updated re-exports
├── models.py                   # Event types (stays at root)
├── utils.py                    # Updated to use new packages
│
├── execution/                  # Core scanning
│   ├── __init__.py
│   ├── scanner.py             # GarakScanner class
│   └── probe_loader.py        # Probe loading
│
├── generators/                 # Target communication
│   ├── __init__.py
│   ├── rate_limiter.py
│   └── websocket_generator.py
│
├── detection/                  # Vulnerability detection
│   ├── __init__.py
│   ├── detectors.py
│   └── triggers.py
│
└── reporting/                  # Result formatting
    ├── __init__.py
    ├── report_parser.py
    └── formatters.py
```

## Directory Structure After Phase 3

```
services/swarm/
├── entrypoint.py              # Thin HTTP layer (145 lines)
├── graph/                     # NEW: LangGraph orchestration
│   ├── __init__.py
│   ├── state.py              # SwarmState, AgentResult
│   ├── swarm_graph.py        # StateGraph definition
│   └── nodes/
│       ├── __init__.py
│       ├── load_recon.py
│       ├── check_safety.py
│       ├── plan_agent.py
│       ├── execute_agent.py
│       └── persist_results.py
├── garak_scanner/            # From Phase 2
│   ├── execution/
│   ├── generators/
│   ├── detection/
│   └── reporting/
└── agents/                   # From Phase 1
    ├── sql/
    ├── auth/
    └── jailbreak/
```

## Notes
- All new packages maintain backward compatibility via root `__init__.py`
- LangChain v1 `create_agent` with `ToolStrategy(ProbePlan)` for structured output
- Gemini 2.5 Pro as default model for agents
- LangGraph StateGraph for orchestration with conditional routing
