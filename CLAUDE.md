# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Quick Reference

### Common Commands

```powershell
# Install dependencies
uv sync

# Run API Gateway (port 8081)
python -m uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8081

# Run all services (requires Test Target Agent on 8082 + Viper frontend)
.\start.ps1

# Run all tests
pytest tests/ -v

# Run tests for specific service (Cartographer example)
pytest tests/unit/services/cartographer/ -v --cov

# Run integration tests
pytest tests/integration/ -v

# Generate coverage report
pytest tests/ --cov=services --cov=libs --cov-report=html

# Run single test
pytest tests/unit/services/cartographer/test_intelligence_extractors.py::TestIntelligenceExtractor::test_valid_extraction -v

# Run tests matching pattern
pytest -k "test_cartographer" -v

# Format code (if using)
# (Project uses no explicit formatter config)

# Type check (via pytest + Pydantic V2)
pytest --mypy --cov
```

---

## Architecture Overview

### 3-Phase Red Teaming Pipeline

```
User/UI
  ├─ POST /api/recon/start/stream ──> Cartographer
  │                                    - LangGraph agent + Gemini 2.5 Flash
  │                                    - 11 attack vectors for intelligence gathering
  │                                    - Output: ReconBlueprint (IF-02)
  │
  ├─ POST /api/scan/start/stream ──> Swarm
  │                                    - Planning phase: LangChain agent selects probes
  │                                    - Execution phase: Garak 50+ probes + detectors
  │                                    - Trinity agents (SQL, Auth, Jailbreak)
  │                                    - Output: VulnerabilityCluster[] (IF-04)
  │
  ├─ POST /api/exploit/start/stream ──> Snipers (Automated)
  │                                      - LangGraph 7-stage pipeline
  │                                      - Pattern extraction + PyRIT converter selection
  │                                      - Human-in-loop gates (plan review, result review)
  │                                      - Output: ExploitResult (IF-06)
  │
  └─ WebSocket /ws/manual-sniping/session/{id} ──> Manual Sniping
                                                      - Session-based interactive testing
                                                      - Real-time converter chains
                                                      - Attack executor + persistence
                                                      - Output: ExploitResult (IF-06)
```

### Service Layer Structure

Each service follows consistent patterns:

```
service_name/
├── __init__.py
├── entrypoint.py           # HTTP handler (main entry from API Gateway)
├── core/                   # Business logic
│   ├── schema.py           # Pydantic models
│   ├── config.py           # Service-specific configuration
│   └── utils.py            # Helpers
├── agent/                  # LangChain/LangGraph logic (if applicable)
│   ├── core.py
│   ├── state.py
│   ├── prompts.py
│   └── nodes/              # LangGraph node implementations
├── components/             # Business logic components
│   ├── scanner.py
│   ├── executor.py
│   └── detectors.py
├── tools/                  # Tool implementations
│   ├── definitions.py
│   └── network.py
├── persistence/            # S3/DB adapters
│   └── s3_adapter.py
└── README.md              # Service-specific documentation
```

### Shared Kernel (libs)

```
libs/
├── config/
│   └── settings.py         # Centralized configuration (Pydantic BaseSettings)
├── contracts/              # 6 data contracts
│   ├── common.py           # Enums (DepthLevel, Aggressiveness)
│   ├── recon.py            # IF-01 ReconRequest, IF-02 ReconBlueprint
│   ├── scanning.py         # IF-03 ScanJobDispatch, IF-04 VulnerabilityCluster
│   └── attack.py           # IF-05 ExploitInput, IF-06 ExploitResult
├── connectivity/
│   ├── http_client.py      # Async HTTP with retry logic
│   └── websocket_client.py
├── monitoring/             # Structured logging, observability decorators
├── persistence/
│   ├── s3.py              # S3 interface
│   ├── sqlite/            # Campaign tracking
│   ├── scan_models.py     # SQLAlchemy models
│   └── repository.py      # Data access patterns
```

---

## Key Design Patterns

### 1. HTTP-First Architecture (No Message Queues)

**Why**: Direct request/response with streaming provides clearer debugging, easier testing, and simpler deployment.

**Pattern**:
- Synchronous REST endpoints in API Gateway
- SSE (Server-Sent Events) for streaming long operations
- WebSocket for bi-directional interactive sessions (Manual Sniping)
- Correlation IDs (audit_id, session_id, campaign_id) in all requests

**Example**: Cartographer reconnaissance streams events as they're discovered, UI updates in real-time without polling.

### 2. Intelligence-Driven Planning

**Why**: Avoid running all 50 Garak probes equally—use reconnaissance findings to guide probe selection.

**Pattern**:
- Phase 1 discovery → Phase 2 planning agent analyzes findings
- Planning filters by: target infrastructure (PostgreSQL → SQL probes), model type (GPT-4 → specific jailbreaks), discovered auth patterns
- Results in ScanPlan with selected probes

**Example**: "PostgreSQL found → prioritize SQL injection and encoding bypass probes"

### 3. Pattern-Learning Exploitation

**Why**: Static exploit templates fail against diverse AI systems—learn from probe results.

**Pattern**:
- Snipers extracts common patterns from successful Garak probes
- Identifies encodings (Base64, ROT13, Unicode) used across payloads
- Generates contextual attack strings (tone, domain language)
- PyRIT converters chain these patterns

**Example**: "3 successful probes used comment-injection + decimal encoding → build 7-turn exploit chain using these patterns"

### 4. Dependency Injection for Testability

**Why**: All services must be testable without external APIs (Redis, S3, Gemini).

**Pattern**:
- Components accept dependencies in `__init__`
- Interfaces define contracts (protocol classes, abstract base)
- Tests mock all external dependencies
- No global singletons or hardcoded API calls

**Example**:
```python
class Cartographer:
    def __init__(
        self,
        llm: LanguageModel,
        http_client: HttpClientInterface,
        s3_adapter: S3Interface
    ):
        self.llm = llm
        self.http = http_client
        self.s3 = s3_adapter
```

### 5. Pydantic V2 Data Contracts

**Why**: Runtime validation, serialization, schema generation, and strict typing.

**Pattern**:
- All inter-service data uses Pydantic models
- 6 contracts (IF-01 through IF-06) define service boundaries
- V2 features: `model_validate_json`, `model_dump_json`, custom validators
- Type hints on all functions

**Example**: `ReconBlueprint(IF-02)` contains system prompt leaks, tool signatures, infrastructure details—validated at service boundary.

### 6. Human-in-the-Loop Safety Gates

**Why**: Automated exploitation requires approval before execution.

**Pattern**:
- Gate #1 (Plan Review): Human reviews Snipers attack plan before execution
- Gate #2 (Result Review): Human confirms vulnerability proof before reporting
- Manual Sniping provides interactive control with real-time feedback

**Example**: Snipers generates 7-turn exploit chain → waits for human approval → executes only after approval.

---

## Testing Strategy

### Test Organization

```
tests/
├── conftest.py             # Shared fixtures (mock LLM, S3, HTTP client)
├── unit/
│   ├── libs/               # Shared kernel tests
│   └── services/
│       ├── cartographer/   # Unit tests (31/31 passing, 94-96% coverage)
│       ├── swarm/          # Scanner, planning agent, detectors
│       └── snipers/        # Agent nodes, PyRIT bridge, scorers
└── integration/
    ├── test_cartographer_flow.py   # Full end-to-end workflows
    └── test_swarm_flow.py
```

### Testing Patterns

**Unit Test Example**:
```python
def test_intelligence_extraction(self, mock_http_client):
    """Test extracting system prompt from errors."""
    extractor = IntelligenceExtractor(mock_http_client)
    result = extractor.extract_system_prompt(error_response)
    assert "system prompt" in result.lower()
```

**Integration Test Example**:
```python
@pytest.mark.asyncio
async def test_cartographer_flow(mock_llm, mock_s3):
    """Test full reconnaissance pipeline."""
    cartographer = Cartographer(mock_llm, mock_s3)
    blueprint = await cartographer.execute(recon_request)
    assert blueprint.tools is not None
    assert blueprint.infrastructure is not None
```

### Mocking Strategy

**Use fixtures from `conftest.py`**:
- `mock_llm`: Fake Gemini responses
- `mock_http_client`: Fake target HTTP responses
- `mock_s3_adapter`: In-memory S3 storage
- `mock_garak_scanner`: Pre-canned Garak results

**Never mock internal components**—test integration within the service.

---

## Code Quality Standards

### 1. File Size & Responsibility

- **Max 150 lines per file** (CLAUDE.md guideline, enforced at review)
- **One responsibility per file** (SRP)
- If file exceeds 150 lines, refactor into components/

### 2. Type Hints (Mandatory)

```python
# ❌ NO: Missing type hints
def process_response(result):
    return result['data']

# ✅ YES: Complete type hints
def process_response(result: dict[str, Any]) -> Any:
    return result['data']
```

### 3. Comments (Why, Not What)

```python
# ❌ NO: Obvious comment
user_id = request.user.id  # Get user ID

# ✅ YES: Explain design decision
# Extract user_id here because auth middleware validates it's in session
user_id = request.user.id
```

### 4. Structured Logging with Correlation IDs

```python
import logging
logger = logging.getLogger(__name__)

async def execute_recon(request: ReconRequest):
    logger.info("Starting reconnaissance", extra={
        "audit_id": request.audit_id,
        "target_url": request.target_url,
        "depth": request.depth
    })
    # ... business logic ...
    logger.debug("Intelligence extracted", extra={
        "audit_id": request.audit_id,
        "tools_found": len(intelligence.tools)
    })
```

### 5. Error Handling

**Fail Fast**: Validate inputs immediately.

```python
# ✅ YES: Validate at boundaries
def create_reconnaissance_request(audit_id: str, target_url: str):
    if not audit_id:
        raise ValueError("audit_id required")
    if not target_url.startswith(("http://", "https://")):
        raise ValueError("target_url must be valid URL")
    return ReconRequest(audit_id=audit_id, target_url=target_url)
```

**Specific Exceptions**: Use context-rich exception types.

```python
# ❌ NO: Generic exception
raise Exception("HTTP request failed")

# ✅ YES: Specific exception with context
from aiohttp import ClientError
try:
    response = await http_client.get(url)
except ClientError as e:
    raise ReconError(f"Failed to reach target {url}: {e.reason}") from e
```

---

## Adding Features

### Adding New Attack Vectors (Cartographer)

1. Edit `services/cartographer/agent/prompts.py` (add technique to `RECON_SYSTEM_PROMPT`)
2. Implement probe logic in `services/cartographer/tools/definitions.py`
3. Add extraction logic in `services/cartographer/intelligence/extractors.py`
4. Write tests in `tests/unit/services/cartographer/`
5. Document expected indicators and success criteria

### Adding New Probes (Swarm)

1. Edit `services/swarm/core/config.py` (add to `PROBE_MAP`)
2. Specify target types (http, websocket), generator config
3. If new detection pattern needed: extend `services/swarm/garak_scanner/detectors.py`
4. Test via integration test in `tests/integration/`

### Adding New Converters (Snipers/Manual Sniping)

1. Implement `pyrit.prompt_converter.PromptConverter` subclass
2. Register in `ConverterFactory` (`services/snipers/tools/pyrit_bridge.py`)
3. Add to `services/manual_sniping/core/catalog.py`
4. Write unit test for converter behavior
5. Update `README.md` in manual_sniping service

### Adding New Detectors (Swarm)

1. Implement detector class in `services/swarm/garak_scanner/detectors.py`
2. Test with known vulnerable + safe outputs
3. Register in probe config or fallback detection
4. Tuning: aim for <10% false positives on benign targets

### Adding New Data Contract

1. Create model in `libs/contracts/` (follow IF-01 naming pattern)
2. Use Pydantic V2 with `ConfigDict(validate_assignment=True)`
3. Add validators for critical fields
4. Document in `docs/data_contracts.md`
5. Update all services that consume the contract

---

## Configuration & Environment

### Settings (Pydantic BaseSettings)

Located in `libs/config/settings.py`:

```python
class Settings(BaseSettings):
    google_api_key: str
    aws_access_key_id: str  # Optional for local testing
    aws_secret_access_key: str  # Optional
    s3_bucket_name: str = "aspexa-automa-results"
    redis_url: str = "redis://localhost:6379"
    max_target_timeout: int = 30
    garak_concurrency: int = 10

    model_config = ConfigDict(env_file=".env", case_sensitive=False)
```

**Load settings**:
```python
from libs.config import settings
# Access: settings.google_api_key
```

**Environment variables** (`.env`):
```
GOOGLE_API_KEY=your_key
AWS_ACCESS_KEY_ID=your_id
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=aspexa-automa-results
```

---

## Common Workflows

### Running Reconnaissance

```bash
curl -X POST http://localhost:8081/api/recon/start/stream \
  -H "Content-Type: application/json" \
  -d '{
    "audit_id": "test-001",
    "target_url": "https://target.local",
    "depth": "deep",
    "max_turns": 10
  }'
```

**Output**: SSE stream of events, then `ReconBlueprint` to S3.

### Running Scanning

```bash
curl -X POST http://localhost:8081/api/scan/start/stream \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "test-001",
    "target_url": "https://target.local",
    "agent_types": ["sql", "auth", "jailbreak"],
    "approach": "standard"
  }'
```

**Output**: SSE stream of probe progress, then `VulnerabilityCluster[]` to S3.

### Running Interactive Manual Sniping

```bash
# 1. Create session
curl -X POST http://localhost:8081/api/manual-sniping/session/create \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": "test-001", "target_url": "https://target.local"}'

# 2. Connect WebSocket (in browser or wscat)
wscat -c ws://localhost:8081/ws/manual-sniping/session/{session_id}

# 3. Send attack commands via WebSocket
# See services/manual_sniping/README.md for payload format

# 4. Save session
curl -X POST http://localhost:8081/api/manual-sniping/session/{session_id}/save
```

---

## Technology Stack Reference

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Framework** | FastAPI | Latest | REST API server |
| **AI/LLM** | LangChain | 1.0.8 | Agent framework |
| | LangGraph | 1.0.1+ | Workflow orchestration |
| | Google Gemini 2.5 Flash | Latest | Primary LLM |
| **Testing** | Garak | 0.5.0+ | 50+ vulnerability probes |
| | PyRIT | 0.9.0+ | Exploitation (9 converters) |
| **Data** | Pydantic | 2.12.4+ | Validation & schemas |
| | SQLAlchemy | 2.0.44+ | ORM |
| | boto3 | 1.35.0+ | AWS S3 access |
| **Async** | aiohttp | 3.9.0+ | Async HTTP client |
| | asyncpg | 0.29.0+ | Async PostgreSQL |
| **Testing** | pytest | 8.3.4+ | Test runner |
| | pytest-asyncio | 0.24.0+ | Async test support |
| | pytest-cov | 6.0.0+ | Coverage |

---

## Debugging Tips

### Enable Debug Logging

```bash
LOGLEVEL=DEBUG python -m uvicorn services.api_gateway.main:app --reload
```

### Inspect Pydantic Models

```python
from libs.contracts.recon import ReconBlueprint

# Validate JSON
blueprint = ReconBlueprint.model_validate_json(json_string)

# Export to JSON
json_str = blueprint.model_dump_json(indent=2)
```

### Test a Single Service

```bash
# Cartographer only
pytest tests/unit/services/cartographer/ -v --pdb

# With print statements (add in code)
pytest tests/unit/services/cartographer/test_graph.py -v -s
```

### Check S3 Persistence (Local)

```python
from libs.persistence import S3Adapter
s3 = S3Adapter()
# List saved campaigns
campaigns = s3.list_campaigns()
# Load specific campaign
blueprint = s3.get_recon_blueprint("campaign_001")
```

---

## Red Flags to Avoid

1. **Classes named Manager/Handler/Orchestrator** → Rename to describe behavior
2. **More than 2 inheritance levels** → Use composition instead
3. **Abstract base class with only 1 implementation** → Delete the abstraction
4. **Config class with single field** → Inline the value
5. **Hardcoded values** → Use `libs.config.settings`
6. **No type hints** → Add them
7. **Comments explaining what code does** → Remove (code should be clear)
8. **Mocking internal service components** → Test full service flow
9. **Missing correlation IDs in logs** → Add audit_id/session_id/campaign_id
10. **Tests without dependency injection** → Use fixtures from conftest.py

---

## Decision Principles

- **Can a new dev understand this in 5 minutes?** → Yes = good code
- **Is this the simplest solution?** → Prefer KISS over clever
- **Would I debug this at 2 AM?** → No = refactor
- **Does this solve a real problem now?** → No = delete it (YAGNI)
- **Can it be tested without external APIs?** → No = refactor for testability

---

## References

- **Architecture**: See `docs/main.md` and `README.md`
- **Phase 1 (Cartographer)**: `docs/Phases/PHASE1_CARTOGRAPHER.md`
- **Phase 2 (Swarm)**: `docs/Phases/PHASE2_SWARM_SCANNER.md`
- **Phase 3a (Snipers)**: `docs/Phases/PHASE3_SNIPERS_EXPLOITATION.md`
- **Phase 3b (Manual Sniping)**: `docs/Phases/PHASE3B_MANUAL_SNIPING.md`
- **Data Contracts**: `docs/data_contracts.md`
- **Tech Stack**: `docs/tech_stack.md`
- **Code Structure**: `docs/code_base_structure.md`

---

**Last Updated**: November 2024 | **Version**: 1.0
