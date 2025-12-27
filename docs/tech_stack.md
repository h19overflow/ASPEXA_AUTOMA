# Technology Stack

Complete overview of technologies used in Aspexa Automa security testing framework.

## Core Framework & Gateway

| Technology | Purpose | Version | Notes |
|-----------|---------|---------|-------|
| **FastAPI** | REST API Gateway & Microservices | Latest | High-performance async API framework |
| **Uvicorn** | ASGI Server | Latest | Production-ready server for FastAPI |
| **Python** | Primary language | 3.12+ | Type hints, async/await, modern stdlib |
| **uv** | Package management | Latest | Fast dependency resolution and environment management |

## AI & LLM Framework

| Technology | Purpose | Version | Notes |
|-----------|---------|---------|-------|
| **LangChain** | Agent framework & orchestration | Latest | Multi-provider LLM support |
| **LangGraph** | Workflow graph orchestration | Latest | Stateful multi-turn agents & workflows |
| **Google Gemini** | Primary LLM provider | 1.5 Flash | High speed, large context, via `langchain-google-genai` |
| **Pydantic V2** | Data validation & schemas | 2.x | Structured data contracts and agent outputs |

**Agent Architecture**:
- **Cartographer**: LangGraph agent with 11 adaptive attack vectors.
- **Swarm Trinity**: 3 specialized LangChain agents (SQL, Auth, Jailbreak).
- **Snipers**: LangGraph workflow with Human-in-the-Loop (HITL) interrupts.

## Security Testing & Scanning

| Technology | Purpose | Notes |
|-----------|---------|-------|
| **Garak** | Vulnerability scanning framework | 50+ security probes, detector system |
| **PyRIT** | Attack execution framework | 9 payload converters and adaptive attack orchestration |

**Garak Components**:
- Probes: 50+ security testing probes.
- Generators: HTTP and WebSocket protocol support.
- Detectors: Vulnerability detection + confidence scoring.

**PyRIT Components**:
- Prompt Converters: Base64, ROT13, Caesar, URL, TextToHex, Unicode, etc.
- Target Adapters: HTTP and WebSocket endpoint support.
- Orchestrator: Multi-turn attack session management.

## HTTP & Network Communication

| Technology | Purpose | Notes |
|-----------|---------|-------|
| **aiohttp** | Async HTTP client | Connection pooling, retry logic for probes |
| **websockets** | WebSocket communication | For WebSocket endpoint testing |
| **urllib3** | Retry strategy | Exponential backoff support |
| **asyncio** | Async event loop | Parallel probe and generation execution |

## Data & State Management

| Technology | Purpose | Version | Notes |
|-----------|---------|---------|-------|
| **PostgreSQL** | Primary Database | Latest | Persistence for scan results and vulnerability logs |
| **SQLAlchemy** | ORM | 2.0+ | Async database operations |
| **Pydantic** | Data contracts | V2 | IF-01 through IF-06 schemas |
| **S3 / Local** | Artifact storage | Standard | Storage for ReconBlueprints and large logs |

**Data Contracts**:
- **IF-01**: ReconRequest (input to Cartographer)
- **IF-02**: ReconBlueprint (output from Cartographer)
- **IF-03**: ScanJobDispatch (input to Swarm)
- **IF-04**: VulnerabilityCluster (output from Swarm)
- **IF-05**: ExploitInput (input to Snipers)
- **IF-06**: ExploitResult (output from Snipers)

## Testing & Quality

| Technology | Purpose | Notes |
|-----------|---------|-------|
| **pytest** | Unit testing framework | Comprehensive suite with `pytest-asyncio` |
| **pytest-cov** | Coverage reporting | Goal: >60% project-wide coverage |
| **Mock objects** | Test isolation | Extensive use of `unittest.mock` and `aioresponses` |

## Logging & Observability

| Technology | Purpose | Format |
|-----------|---------|--------|
| **Structured Logging** | Operational tracing | JSON-formatted logs with correlation IDs |
| **Audit Trails** | Decision tracking | Detailed logs for every agent decision |
| **Clerk** | Authentication | Identity management for the API Gateway |

## Architecture Patterns

### REST-Based Microservices
- **Pattern**: Centralized API Gateway (FastAPI) routing to specialized services.
- **Communication**: Direct HTTP/REST calls with streaming support (SSE).
- **Security**: Clerk authentication with role-based access control.

### Agentic Workflows
- **Pattern**: LangGraph state machines for complex, multi-step reasoning.
- **Reasoning**: Chain-of-Thought and recursive reflection.
- **Validation**: Strict Pydantic-based output parsing.

### Resilience & Reliability
- **Retries**: Exponential backoff for all network operations.
- **Persistence**: Reliable storage of every reconnaissance and scan result in PostgreSQL/S3.
- **Human-in-the-Loop**: Critical safety gates for high-impact actions.

## Summary

Aspexa Automa is built on a **modern, high-performance Python stack** optimized for AI orchestration and security engineering. The shift from event-driven to **REST-based architecture** simplifies the deployment model while maintaining the power of specialized agents and sophisticated security frameworks.