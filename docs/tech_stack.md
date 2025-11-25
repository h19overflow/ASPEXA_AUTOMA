# Technology Stack

Complete overview of technologies used in Aspexa Automa security testing framework.

## Core Framework & Event Bus

| Technology | Purpose | Version | Notes |
|-----------|---------|---------|-------|
| **FastStream** | Event-driven microservices framework | Latest | Replaces manual event handling |
| **Redis** | Message broker for event bus | 6.0+ | Enables async microservice communication |
| **Python** | Primary language | 3.11+ | Type hints, async/await support |
| **uv** | Package management | Latest | Faster dependency resolution |

**Event Bus Pattern**:
- Microservices communicate via Redis Streams
- Topics: `cmd_recon_start`, `evt_recon_finished`, `cmd_scan_start`, etc.
- Producer-Consumer pattern for decoupled services

## AI & LLM Framework

| Technology | Purpose | Version | Notes |
|-----------|---------|---------|-------|
| **LangChain** | Agent framework & orchestration | Latest | Multi-provider LLM support |
| **LangGraph** | Workflow graph orchestration | Latest | Stateful multi-turn agents |
| **Google Gemini** | Primary LLM provider | 2.5 Flash | Via `langchain-google-genai` |
| **Pydantic V2** | Data validation & schemas | 2.x | Structured agent outputs |

**Agent Architecture**:
- Cartographer: LangGraph agent with 11 attack vectors
- Swarm Trinity: 3 specialized LangChain agents
- Snipers: LangGraph workflow with HITL interrupts

## Security Testing & Scanning

| Technology | Purpose | Notes |
|-----------|---------|-------|
| **Garak** | Vulnerability scanning framework | 50+ security probes, detector system |
| **PyRIT** | Attack execution framework | 9 payload converters (6 native + 3 custom) |

**Garak Components**:
- Probes: 50+ security testing probes
- Generators: HTTP, WebSocket protocol support
- Detectors: Vulnerability detection + confidence scoring
- Models: ProbeResult data structures

**PyRIT Components**:
- Prompt Converters: Base64, ROT13, Caesar, URL, TextToHex, Unicode, etc.
- Custom Converters: HtmlEntity, JsonEscape, XmlEscape
- Target Adapters: HTTP and WebSocket endpoint support
- Orchestrator: Attack session management

## HTTP & Network Communication

| Technology | Purpose | Notes |
|-----------|---------|-------|
| **aiohttp** | Async HTTP client | Connection pooling, retry logic |
| **requests** | Synchronous HTTP client | Used in Swarm scanner |
| **websockets** | WebSocket communication | For WebSocket endpoint testing |
| **urllib3** | Retry strategy & connection pooling | Exponential backoff support |
| **asyncio** | Async event loop | Parallel probe execution |

**Network Patterns**:
- Cartographer: Exponential backoff retry (2^n seconds)
- Swarm: Connection pooling with semaphore controls
- Parallel: Max 10 concurrent probes, 5 concurrent generations

## Data & State Management

| Technology | Purpose | Version | Notes |
|-----------|---------|---------|-------|
| **Pydantic** | Data contracts | V2 | IF-01, IF-02, IF-04 schemas |
| **JSON** | Data persistence | Standard | Reconnaissance + scan results |
| **TypedDict** | Type hints for state | Built-in | LangGraph state definitions |

**Data Contracts**:
- **IF-01**: ReconRequest (input to Cartographer)
- **IF-02**: ReconBlueprint (output from Cartographer)
- **IF-03**: ScanJobDispatch (input to Swarm)
- **IF-04**: VulnerabilityCluster (output from Swarm)
- **IF-05/IF-06**: ExploitInput/ExploitResult (Snipers)

**Storage**:
- Reconnaissance results: `tests/recon_results/{audit_id}_{timestamp}.json`
- Garak reports: `garak_runs/{audit_id}_{agent_type}.jsonl`
- Decision logs: `logs/swarm_decisions_{audit_id}.json`

## Testing & Quality

| Technology | Purpose | Notes |
|-----------|---------|-------|
| **pytest** | Unit testing framework | Comprehensive test coverage |
| **asyncio.run** | Async test execution | For async function testing |
| **Mock objects** | Test isolation | Dependency injection via tools |

**Test Coverage**:
- Cartographer: 31/31 tests passing (94-96% coverage)
- Swarm: Integration tests for Trinity agents
- Snipers: Unit tests for core components

**Test Strategy**:
- Unit tests: Logic verification
- Integration tests: Service communication
- Mock targets: Pre-configured test systems

## Logging & Observability

| Technology | Purpose | Format |
|-----------|---------|--------|
| **Structured Logging** | JSON-formatted logs | Correlation IDs (audit_id) |
| **Decision Logging** | Agent decision tracking | JSON Lines (audit_id_{timestamp}.json) |
| **Correlation IDs** | Request tracing | audit_id + agent_type |

**Logging Levels**:
- DEBUG: Detailed execution traces
- INFO: Operational milestones
- WARNING: Recoverable issues
- ERROR: Critical failures

## Dependencies by Service

### Cartographer
```
├── langchain
├── langchain-google-genai
├── faststream[redis]
├── aiohttp
├── pydantic
└── difflib (stdlib)
```

### Swarm
```
├── langchain
├── langchain-google-genai
├── garak
├── requests
├── faststream[redis]
├── asyncio (stdlib)
├── semaphore (asyncio)
└── pydantic
```

### Snipers
```
├── langchain
├── langchain-google-genai
├── langgraph
├── pyrit
├── pydantic
├── asyncio (stdlib)
└── importlib (stdlib)
```

## Development Environment

| Tool | Purpose | Configuration |
|------|---------|---------------|
| **uv** | Package management | Uses pyproject.toml |
| **pytest** | Test runner | pytest.ini configuration |
| **Python** | Runtime | 3.11+ (type hints, async) |
| **PowerShell** | Command execution | Native Windows support |

**Project Structure**:
```
aspexa-automa/
├── services/         # Microservices (Cartographer, Swarm, Snipers)
├── libs/            # Shared code (contracts, events, config)
├── scripts/         # Examples and utilities
├── tests/           # Test suite
├── docs/            # Documentation
└── pyproject.toml   # Project metadata & dependencies
```

## Architecture Patterns

### Event-Driven Microservices
- **Pattern**: Pub/Sub via Redis Streams
- **Framework**: FastStream
- **Topology**: 3 independent services communicating async

### Agent Framework
- **Pattern**: LangChain agents + LangGraph workflows
- **Reasoning**: Chain-of-Thought + Step-Back prompting
- **Execution**: Structured output with Pydantic validation

### Tool System
- **Pattern**: LangChain tools as callable functions
- **Integration**: Direct invocation from agent loop
- **State**: Instance-based (Cartographer) or workflow state (Snipers)

### Retry & Resilience
- **Network**: Exponential backoff (2^n seconds, max 3 attempts)
- **Parser**: Graceful degradation (skip failed operations)
- **Error Handling**: Try/except with logging, continue when possible

## Performance Characteristics

### Cartographer
- **Typical Duration**: 5-10 minutes per audit
- **Token Usage**: ~30,000-40,000 per full reconnaissance
- **Concurrency**: Unlimited audits (instance-based state)

### Swarm
- **Typical Duration**:
  - Quick: ~2 minutes
  - Standard: ~10 minutes
  - Thorough: ~30 minutes
- **Parallelism**: 3-5x faster with parallel execution
- **Concurrency**: Limited by target rate limits

### Snipers
- **Typical Duration**: 2-5 minutes per exploitation
- **Retry Attempts**: Up to 3 retries with payload modification
- **Concurrency**: Controlled via semaphores

## Extensibility Points

### Adding New Probes
- Edit: `services/swarm/core/config.py` (PROBE_MAP)
- Use: Garak probe classes directly

### Adding New Converters
- Implement: `pyrit.prompt_converter.PromptConverter`
- Register: `ConverterFactory` in `services/snipers/tools/pyrit_bridge.py`

### Adding New Detectors
- Implement: Custom detector class
- Register: In Garak probe or as fallback

### Adding New Attack Vectors
- Edit: `services/cartographer/prompts.py` (RECON_SYSTEM_PROMPT)
- Implement: New probing technique
- Document: Success criteria and indicators

## Security Considerations

- **API Keys**: Google API key required in environment
- **Authentication**: Target auth headers passed through payload
- **Rate Limiting**: Token bucket algorithm prevents DoS
- **Human-in-Loop**: HITL interrupts prevent autonomous escalation
- **Audit Trail**: All decisions logged with correlation IDs

## Summary

Aspexa Automa uses a **modern, scalable AI agent framework** built on:
1. **Event-driven architecture** (FastStream + Redis)
2. **LLM agents** (LangChain + Google Gemini)
3. **Security frameworks** (Garak + PyRIT)
4. **Async patterns** (asyncio, aiohttp, websockets)
5. **Type safety** (Pydantic V2, TypedDict)

This stack enables rapid security testing automation while maintaining extensibility, observability, and human control.
