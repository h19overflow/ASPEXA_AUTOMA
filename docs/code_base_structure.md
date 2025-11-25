# Aspexa Automa: Complete Code Structure

This document provides a comprehensive overview of the Aspexa Automa codebase organization, component hierarchy, and module responsibilities.

---

## Overview

```
aspexa-automa/
├── Root Configuration    # Project setup and orchestration
├── libs/                 # Shared kernel (contracts, events, config)
├── services/            # The three core microservices (Cartographer, Swarm, Snipers)
├── scripts/             # Examples and utilities
└── tests/               # Test suite
```

---

## Root Configuration Files

| File | Purpose | Notes |
|------|---------|-------|
| `.env` | Secrets and API keys | Contains GOOGLE_API_KEY, REDIS_URL |
| `docker-compose.yml` | Service orchestration | Redis broker, optional PostgreSQL |
| `pyproject.toml` | Dependencies and metadata | Uses `uv` package manager |
| `Makefile` | Command shortcuts | Optional: development convenience |
| `.gitignore` | Git exclusions | Excludes .env, __pycache__, etc. |

---

## libs/ - Shared Kernel

**Purpose**: Centralized, reusable code shared across all services.

### libs/config/

**Module**: `settings.py`
- Centralized configuration management
- Environment variable loading
- Default values for Redis, API keys, timeout thresholds
- Accessed by all services via: `from libs.config import settings`

### libs/contracts/

**Purpose**: Data contracts (IF-01 through IF-06) defining service interfaces.

| Contract | Module | Purpose | Phase |
|----------|--------|---------|-------|
| **IF-01** | `recon.py` | ReconRequest input | Phase 1 |
| **IF-02** | `recon.py` | ReconBlueprint output | Phase 1 |
| **IF-03** | `scanning.py` | ScanJobDispatch input | Phase 2 |
| **IF-04** | `scanning.py` | VulnerabilityCluster output | Phase 2 |
| **IF-05** | `attack.py` | ExploitInput | Phase 3 |
| **IF-06** | `attack.py` | ExploitResult output | Phase 3 |

**Key Files**:
- `common.py` - Shared enums (DepthLevel, AgentType, ScanApproach, etc.)
- `recon.py` - Reconnaissance contracts
- `scanning.py` - Scanning and vulnerability contracts
- `attack.py` - Exploitation contracts

### libs/persistence/

**Module**: `storage.py`
- Abstract storage interface
- JSON file storage implementation
- Used by Cartographer for IF-02 transformation
- Extensible for S3, databases, etc.

### libs/events/

**Purpose**: Event bus abstraction for async microservice communication.

**Modules**:
- `publisher.py` - Publish events to Redis Streams
- `consumer.py` - Consume events and trigger handlers

**Event Topics**:
- `cmd_recon_start` → IF-01 ReconRequest
- `evt_recon_finished` → IF-02 ReconBlueprint
- `cmd_scan_start` → ScanJobDispatch
- `evt_scan_complete` → IF-04 VulnerabilityCluster
- `cmd_exploit_start` → ExploitInput
- `evt_exploit_complete` → ExploitResult

---

## services/ - The Three Microservices

### services/cartographer/ - Phase 1: Reconnaissance

**Role**: Autonomous agent that maps target systems using 11 attack vectors to extract system prompts, tools, auth structures, and infrastructure.

**Engine**: LangGraph + Google Gemini 2.5 Flash

**Key Modules**:

#### Core Entry Points
- `main.py` - FastStream service entry point
- `consumer.py` - Event handler for `cmd_recon_start` events

#### Agent & Logic
- `prompts.py` - System prompt with 11 attack vectors
  - Vector 1: Direct Enumeration
  - Vector 2: Error Elicitation
  - Vector 3: Feature Probing
  - Vector 4: Boundary Testing
  - Vector 5: Context Exploitation
  - Vector 6: Meta-Questioning
  - Vector 7: Indirect Observation
  - Vector 8: Infrastructure Probing
  - Vector 9: RAG Mining
  - Vector 10: Error Parsing
  - Vector 11: Behavior Analysis

- `response_format.py` - Pydantic schemas for structured output

#### Orchestration
- `agent/graph.py` - LangGraph workflow definition
- `agent/state.py` - Agent state schema (observations, findings)

#### Tools (ReconToolSet)
- `tools/definitions.py` - Tool implementations:
  - `take_note(observation, category)` - Records findings with deduplication
  - `analyze_gaps()` - Self-reflection on intelligence gaps
- `tools/network.py` - HTTP client with retry logic (exponential backoff)

#### Intelligence Persistence
- `persistence/json_storage.py` - IF-02 transformation pipeline
  - Parses observations into structured format
  - Deduplicates findings (80% SequenceMatcher threshold)
  - Transforms to IF-02 ReconBlueprint contract

**Output**: IF-02 ReconBlueprint containing:
- System prompt leaks
- Detected tools with signatures
- Infrastructure details (DB, vector store, model)
- Authorization structures

**Test Coverage**: 31/31 tests passing, 94-96% coverage

---

### services/swarm/ - Phase 2: Intelligent Scanning

**Role**: Intelligent scanning service using Trinity agents (SQL, Auth, Jailbreak) guided by Phase 1 reconnaissance to find vulnerabilities.

**Engine**: LangChain agents + Garak framework (50+ probes)

**Key Modules**:

#### Core Entry Points
- `main.py` - FastStream service entry point
- `core/consumer.py` - Event handler for `cmd_scan_start`, fan-out to Trinity agents

#### Configuration & Orchestration
- `core/config.py` - PROBE_MAP (50+ Garak probes), PROBE_CATEGORIES
- `core/schema.py` - Data models (ScanConfig, AgentScanResult)
- `core/decision_logger.py` - Audit trail (JSON Lines format)
- `core/utils.py` - Logging utilities

#### The Trinity Agents
- `agents/base.py` - Agent factory and base class
- `agents/trinity.py` - Three specialized agents:
  - **SQL Agent**: Data surface attacker (SQL injection, encoding bypass)
  - **Auth Agent**: Authorization surface attacker (BOLA, privilege escalation)
  - **Jailbreak Agent**: Prompt surface attacker (DAN, jailbreak, leak)
- `agents/prompts.py` - System prompts per agent type
- `agents/tools.py` - Intelligence-driven probe selection:
  - `analyze_target()` - Recommends probes based on recon data
  - `execute_scan()` - Configures and executes Garak
- `agents/utils.py` - Agent utilities

#### Garak Integration
- `garak_scanner/scanner.py` - Core scanner orchestration
  - Singleton pattern for reuse
  - HTTP/WebSocket factory pattern
  - Sequential/parallel execution modes
  - Token bucket rate limiting

- `garak_scanner/http_generator.py` - HTTP endpoint testing
  - Extends `garak.generators.base.Generator`
  - Connection pooling with `requests.Session`
  - Exponential backoff retry (max 3 attempts)

- `garak_scanner/websocket_generator.py` - WebSocket endpoint testing
  - Auto-detects WebSocket from URL (ws://, wss://)
  - Same response format handling as HTTP

- `garak_scanner/detectors.py` - Vulnerability detection
  - Load probe-specific detectors
  - Fallback to MitigationBypass detector
  - Scoring: 0.0 (safe) to 1.0 (vulnerable)
  - Custom detectors: DAN, PromptInjection, EncodingBypass

- `garak_scanner/models.py` - ProbeResult data model
- `garak_scanner/rate_limiter.py` - Token bucket algorithm
- `garak_scanner/report_parser.py` - JSONL to VulnerabilityCluster transformation
- `garak_scanner/utils.py` - Category and severity mappings

**Execution Strategy**:
- Parallel execution: Probe-level (max 10) + Generation-level (max 5)
- Rate limiting: Configurable requests per second
- Approaches: Quick (2 min), Standard (10 min), Thorough (30 min)

**Output**: IF-04 VulnerabilityCluster[] containing:
- Vulnerability type and confidence score
- Successful payloads
- Target responses (evidence)
- Detector scores
- Agent type and metadata

---

### services/snipers/ - Phase 3: Human-in-the-Loop Exploitation

**Role**: Stateful exploitation engine using pattern learning and human approval to execute targeted attacks and prove vulnerabilities.

**Engine**: LangGraph workflow + PyRIT framework

**Key Modules**:

#### Core Entry Points
- `main.py` - FastStream service entry point
- `consumer.py` - Event handler for `cmd_exploit_start` (pending implementation)

#### Data Processing
- `models.py` - Pydantic data models (ExploitInput, ExploitResult, AttackPlan)
- `parsers.py` - Report parsing:
  - Parse Garak vulnerability reports
  - Parse reconnaissance intelligence
  - Extract actionable patterns

#### LangGraph Workflow (agent/)
- `agent/core.py` - ExploitAgent orchestration
  - Initializes workflow nodes
  - Manages state transitions
  - Handles HITL approval gates

- `agent/state.py` - LangGraph TypedDict state definition
  - Input: vulnerability, recon data
  - State: patterns, converters, payloads, score
  - Output: results

- `agent/prompts.py` - System prompts
  - Pattern analysis (chain-of-thought reasoning)
  - Converter selection rationale
  - Payload generation context

- `agent/routing.py` - Workflow routing logic
  - Conditional node routing
  - HITL interrupt conditions
  - Retry logic

#### Reasoning Tools (agent/agent_tools/)
- `pattern_analysis_tool.py` - Analyze vulnerability patterns from Garak output
- `converter_selection_tool.py` - Select appropriate PyRIT converters
- `payload_generation_tool.py` - Generate contextual payloads
- `scoring_tool.py` - Evaluate exploitation success

#### Workflow Nodes (agent/nodes/)
- `pattern_analysis.py` - Extract patterns from successful probes
- `converter_selection.py` - Choose encoding strategies
- `payload_generation.py` - Create customized payloads
- `attack_plan.py` - Plan multi-turn attack sequence
- `human_review.py` - HITL approval checkpoint #1 (plan review)
- `attack_execution.py` - Execute via PyRIT
- `scoring.py` - Evaluate results
- `retry.py` - Retry with payload modifications

#### PyRIT Integration (tools/)
- `pyrit_bridge.py` - Converter factory
  - 9 converters: Base64, ROT13, Caesar, URL, TextToHex, Unicode, + 3 custom
  - Maps vulnerability types to appropriate converters

- `pyrit_executor.py` - Main execution orchestrator
  - Manages PyRIT sessions
  - Handles target communication
  - Captures kill chain evidence

- `pyrit_target_adapters.py` - Target communication
  - HTTP adapter
  - WebSocket adapter
  - Request/response handling

#### Scorers (tools/scorers/)
- `base.py` - Abstract scorer interface
- `regex_scorer.py` - Pattern-based scoring
- `pattern_scorer.py` - Behavioral pattern detection
- `composite_scorer.py` - Multi-strategy scoring
- `__init__.py` - Scorer registry

**Workflow**: 7-stage pipeline
1. Pattern Analysis (extract from examples)
2. Converter Selection (choose encoding)
3. Payload Generation (create attack)
4. Attack Plan (multi-turn sequence)
5. Human Review (HITL Gate #1)
6. Attack Execution (PyRIT session)
7. Scoring & Result Review (HITL Gate #2)

**Output**: IF-06 ExploitResult containing:
- Attack success status
- Proof of exploitation
- Kill chain transcript
- Vulnerability confirmation

**Status**: 64% complete
- ✅ Core agent structure
- ✅ PyRIT integration
- ⏳ FastAPI endpoints (pending)
- ⏳ WebSocket controller (pending)

---

## scripts/ - Examples and Utilities

### scripts/examples/

**Purpose**: Runnable examples demonstrating service workflows.

| File | Purpose | Phase |
|------|---------|-------|
| `01_basic_reconnaissance.py` | Simple recon workflow | Phase 1 |
| `02_persistence_workflow.py` | Persistence layer example | Phase 1 |
| `03_intelligence_extraction.py` | Extract and analyze intelligence | Phase 1 |
| `scan_target_with_swarm.py` | Full scanning workflow | Phase 2 |

### scripts/testing/

**Purpose**: Testing utilities and integration tests.

| File | Purpose |
|------|---------|
| `test_swarm_scanner.py` | Garak scanner integration tests |
| `test_cartographer_service.py` | Cartographer agent tests |
| `README_SWARM.md` | Swarm testing documentation |

---

## tests/ - Test Suite

### tests/conftest.py
- Global pytest fixtures
- Mock targets and fixtures
- Shared test utilities

### tests/unit/ - Fast, In-Memory Tests

#### tests/unit/libs/
- `test_contracts.py` - Data contract validation

#### tests/unit/services/cartographer/
- `test_*.py` - Agent, tool, and persistence tests
- Coverage: 31/31 tests passing, 94-96% coverage

#### tests/unit/services/snipers/
- `test_scorers.py` - Scorer implementations
- `test_pyrit_integration.py` - PyRIT bridge tests
- `test_*.py` - Additional unit tests

#### tests/unit/test_persistence/
- `test_*.py` - Storage implementation tests

### tests/integration/ - E2E Workflow Tests

#### tests/integration/test_*.py
- Full workflow tests
- Service-to-service communication
- Event bus integration

---

## File Organization Principles

### Module Size Limits
- **Max 150 lines per file** (CLAUDE.md guideline)
- **One responsibility per file** (Single Responsibility Principle)
- Break into smaller modules if exceeding limit

### Naming Conventions
- **Service roots**: PascalCase (Cartographer, Swarm, Snipers)
- **Modules**: snake_case (prompts.py, network.py)
- **Classes**: PascalCase (ReconToolSet, GarakScanner)
- **Functions**: snake_case (take_note, analyze_gaps)

### Import Organization
1. Standard library imports
2. Third-party imports (langchain, garak, pyrit)
3. Local imports (libs, services)
4. Type hints at end if needed

---

## Data Flow

### Phase 1 (Cartographer) → Phase 2 (Swarm)
```
IF-01 ReconRequest
  ↓
[Cartographer Agent] (11 attack vectors)
  ↓
IF-02 ReconBlueprint (tools, infrastructure, auth)
  ↓
[Swarm Trinity Agents] (use recon to select probes)
```

### Phase 2 (Swarm) → Phase 3 (Snipers)
```
IF-04 VulnerabilityCluster[] (successful probes)
  ↓
[Snipers] (analyze patterns, plan exploits)
  ↓
IF-06 ExploitResult (proof of exploitation)
```

---

## Configuration Hierarchy

1. **Default values** in `libs/config/settings.py`
2. **Environment variables** override defaults
3. **Runtime parameters** passed to services

**Example**:
```python
# Default: 10 concurrent probes
# Override: SWARM_MAX_CONCURRENT_PROBES=20
# Runtime: GarakScanner(max_concurrent_probes=20)
```

---

## Key Dependencies

| Dependency | Purpose | Used By |
|------------|---------|---------|
| **FastStream** | Event-driven microservices | All services |
| **Redis** | Message broker | Event bus |
| **LangChain** | Agent framework | Cartographer, Swarm |
| **LangGraph** | Workflow orchestration | Snipers |
| **Garak** | Security probes | Swarm |
| **PyRIT** | Attack framework | Snipers |
| **Pydantic V2** | Data validation | All contracts |
| **aiohttp** | Async HTTP | Cartographer |
| **requests** | Sync HTTP | Swarm |
| **websockets** | WebSocket comm | Swarm, Snipers |

---

## Summary

Aspexa Automa is organized as:

**Kernel** (`libs/`): Contracts, configuration, events, persistence
**Services** (`services/`): Three independent microservices with distinct responsibilities
**Examples** (`scripts/`): Runnable workflows demonstrating each phase
**Tests** (`tests/`): Comprehensive unit and integration test coverage

Each service is modular, independently testable, and communicates via standardized contracts and event bus.
