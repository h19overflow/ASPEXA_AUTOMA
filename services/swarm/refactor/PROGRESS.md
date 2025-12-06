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

## Next Steps

### Phase 3: Graph Orchestration (03_graph_orchestration.md)
- Not started
- **Goal:** Replace procedural `entrypoint.py` (~400 lines) with LangGraph state machine
- **Tasks:**
  1. Create `graph/` directory
  2. Create `graph/state.py` - Define `SwarmState` and `AgentResult` schemas
  3. Create `graph/nodes.py` - Define node functions (load_recon, plan_agent, execute_agent, persist_results)
  4. Create `graph/swarm_graph.py` - Build LangGraph workflow with StateGraph
  5. Update `entrypoint.py` to use graph (thin HTTP layer)
  6. Add tests for graph nodes

### Phase 4: Cleanup (04_cleanup.md)
- Not started
- **Goal:** Simplify schemas, remove dead code, consolidate config
- **Tasks:**
  1. Simplify `core/schema.py` (477 lines → ~150 lines)
  2. Delete dead code files (`agents/base_utils.py`, `agents/tools.py`, `agents/trinity.py`)
  3. Consolidate config (remove duplicate enums)
  4. Update tests for new structure

## Directory Structure After Phase 2

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

## Notes
- All new packages maintain backward compatibility via root `__init__.py`
- LangChain v1 `create_agent` with `ToolStrategy(ProbePlan)` for structured output
- Gemini 2.5 Pro as default model for agents
