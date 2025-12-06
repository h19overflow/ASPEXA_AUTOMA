# Phase 4: Cleanup and Consolidation

## Overview

After phases 1-3, clean up remaining issues:
1. Simplify schemas
2. Remove dead code
3. Consolidate config
4. Update tests

## 1. Simplify Schemas

### Current State (schema.py)
```python
# 477 lines with:
- ScanConfig (120 lines)
- AuthIntelligence
- ScanInput
- ScanContext (+ 80 line from_scan_job method)
- ScanAnalysisResult
- ProbeResultDetail
- AgentScanResult
- ScanPlan
- ScanPlanResponse
- PlanningPhaseResult
```

### Target State
```python
# schemas.py (~150 lines)

class ScanConfig(StrictBaseModel):
    """User-configurable scan parameters."""
    approach: str = "standard"
    generations: int = 5
    max_probes: int = 10
    timeout: int = 30
    # Remove parallel execution complexity for now


class ReconContext(StrictBaseModel):
    """Intelligence from recon phase."""
    audit_id: str
    infrastructure: Dict[str, Any] = {}
    detected_tools: List[Dict[str, Any]] = []
    system_prompt_leaks: List[str] = []
    auth_rules: List[str] = []


class ProbePlan(StrictBaseModel):
    """Agent's probe selection."""
    probes: List[str]
    generations: int
    reasoning: Dict[str, str] = {}


class ProbeResult(StrictBaseModel):
    """Result from a single probe execution."""
    probe_name: str
    prompt: str
    output: str
    status: str  # pass, fail, error
    detector_name: str = ""
    detector_score: float = 0.0


class ScanReport(StrictBaseModel):
    """Final scan report for persistence."""
    audit_id: str
    agent_type: str
    probes_executed: List[str]
    results: List[ProbeResult]
    vulnerabilities_found: int
    duration_seconds: float
```

### Delete These
- `ScanInput` → replaced by `ReconContext`
- `ScanContext` → logic moves to graph nodes
- `ScanAnalysisResult` → inline in agent
- `ProbeResultDetail` → merged with `ProbeResult`
- `AgentScanResult` → replaced by graph state
- `ScanPlanResponse` → unnecessary wrapper
- `PlanningPhaseResult` → replaced by graph state

## 2. Remove Dead Code

### Files to Delete
```
agents/
├── base_utils.py      # DELETE - inlined
├── tools.py           # DELETE - context vars removed
├── trinity.py         # DELETE - useless wrappers
└── prompts.py         # DELETE - replaced by per-agent prompts

garak_scanner/         # DELETE entire directory
├── probes.py
├── rate_limiter.py
├── report_parser.py
├── scanner.py
├── utils.py
└── websocket_generator.py

core/
├── config.py          # SIMPLIFY - remove PROBE_MAP complexity
└── utils.py           # REVIEW - keep only what's used
```

### Functions to Delete
```python
# From core/config.py - delete
- get_probes_for_agent()  # Replaced by agent.available_probes
- get_generations_for_approach()  # Inline in agents
- PROBE_MAP  # Each agent owns its probes

# From agents/base.py - delete entire file
- create_planning_agent()
- run_planning_agent()
- run_scanning_agent()
- _build_planning_input()
```

## 3. Consolidate Config

### Current State
```python
# core/config.py has:
- AgentType enum
- ScanApproach enum (also in schema.py!)
- VulnCategory enum
- PROBE_CATEGORIES dict
- PROBE_MAP dict
- get_probes_for_agent()
- get_generations_for_approach()
- get_all_probe_names()
```

### Target State
```python
# config.py (~50 lines)
"""
Swarm service configuration.

Purpose: Define constants and enums
"""
from enum import Enum


class AgentType(str, Enum):
    SQL = "sql"
    AUTH = "auth"
    JAILBREAK = "jailbreak"


class ScanApproach(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    THOROUGH = "thorough"


# Default generations per approach
GENERATIONS = {
    ScanApproach.QUICK: 3,
    ScanApproach.STANDARD: 5,
    ScanApproach.THOROUGH: 10,
}
```

Probe configuration moves to each agent's `*_probes.py` file.

## 4. Final Directory Structure

```
services/swarm/
├── __init__.py
├── config.py                    # Simple enums and constants
├── schemas.py                   # Simplified schemas
├── entrypoint.py               # Thin HTTP layer
├── agents/
│   ├── __init__.py             # Agent registry
│   ├── base_agent.py           # Abstract base
│   ├── sql/
│   │   ├── __init__.py
│   │   ├── sql_agent.py
│   │   ├── sql_prompt.py
│   │   └── sql_probes.py
│   ├── auth/
│   │   └── ...
│   └── jailbreak/
│       └── ...
├── scanner/
│   ├── __init__.py
│   ├── executor.py             # Probe execution
│   ├── detectors.py            # Detection logic
│   ├── models.py               # Event types
│   └── generators/
│       ├── __init__.py
│       └── http.py
├── graph/
│   ├── __init__.py
│   ├── state.py
│   ├── nodes.py
│   └── swarm_graph.py
├── persistence/
│   └── s3_adapter.py           # Keep as-is
└── refactor/                    # Delete after complete
    └── *.md
```

## 5. Update Tests

### New Test Structure
```
tests/unit/services/swarm/
├── test_config.py
├── test_schemas.py
├── agents/
│   ├── test_base_agent.py
│   ├── test_sql_agent.py
│   ├── test_auth_agent.py
│   └── test_jailbreak_agent.py
├── scanner/
│   ├── test_executor.py
│   ├── test_detectors.py
│   └── test_http_generator.py
└── graph/
    ├── test_state.py
    ├── test_nodes.py
    └── test_swarm_graph.py
```

### Tests to Delete
```
tests/unit/services/swarm/
├── test_mapping.py          # Probe mapping no longer centralized
├── test_schema_intelligence.py  # Schema simplified
└── garak_scanner/           # Replaced by scanner/
```

## Migration Checklist

### Phase 4a: Schema Cleanup
- [ ] Create new simplified `schemas.py`
- [ ] Update all imports to use new schemas
- [ ] Delete old schema classes
- [ ] Update persistence to use new schemas

### Phase 4b: Config Cleanup
- [ ] Simplify `config.py`
- [ ] Move probe configs to agents
- [ ] Delete unused functions
- [ ] Update imports

### Phase 4c: Dead Code Removal
- [ ] Delete `agents/base_utils.py`
- [ ] Delete `agents/tools.py`
- [ ] Delete `agents/trinity.py`
- [ ] Delete old `garak_scanner/` directory
- [ ] Delete `core/` directory (merge into root)

### Phase 4d: Test Updates
- [ ] Update existing tests for new structure
- [ ] Add tests for new components
- [ ] Delete obsolete tests
- [ ] Verify coverage

## Verification

Run full test suite after each sub-phase:
```bash
python -m pytest tests/unit/services/swarm/ -v --tb=short
```

Expected outcome:
- Fewer files (9 → ~20 with new structure)
- Clearer responsibilities
- Same or better test coverage
- Faster import time
- Easier to navigate
