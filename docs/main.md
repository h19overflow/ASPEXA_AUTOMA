# Aspexa Automa: Automated Red Team Orchestrator

## Overview

Aspexa Automa is an automated red teaming engine for stress-testing AI systems. Rather than simple vulnerability scanning, it orchestrates sophisticated "kill chains"—coordinated attack sequences that prove exactly how an AI system can be exploited.

**Philosophy**: Aspexa enforces strict separation of concerns. Instead of one giant AI trying to do everything, specialized agents work in a clean assembly line:
1. **Cartographer** (reconnaissance) → gathers intelligence
2. **Swarm** (scanning) → finds vulnerabilities
3. **Snipers** (exploitation) → proves the impact

**Safety First**: All operations include mandatory human-in-the-loop checkpoints before sensitive actions (scanning critical tools, executing high-risk payloads, finalizing verdicts).

---

## How It Works: The 3-Phase Pipeline

### Phase 1: Cartographer (Reconnaissance)

**Goal**: Map target systems without triggering alarms using intelligent, adaptive questioning.

**Engine**: LangGraph agent + Google Gemini 2.5 Flash

**Strategy**: 11 attack vectors
1. Direct Enumeration ("What can you do?")
2. Error Elicitation (trigger stack traces for tech stack fingerprinting)
3. Feature Probing (deep dive into specific tools)
4. Boundary Testing (find numerical limits)
5. Context Exploitation (simulate user flows)
6. Meta-Questioning (ask about the AI's role)
7. Indirect Observation (behavioral analysis)
8. Infrastructure Probing (direct tech stack questions)
9. RAG Mining (ask for technical docs to leak vector stores)
10. Error Parsing (extract "PostgreSQL", "FAISS" from errors)
11. Behavior Analysis (pattern matching on responses)

**Output**: IF-02 ReconBlueprint containing:
- System prompt leaks
- Tool signatures (function names, parameters, types)
- Infrastructure details (database type, vector store, embedding model)
- Authorization structure (auth type, validation rules, privilege levels)

**Intelligence Loop**: The agent self-reflects after each turn:
- Calculates coverage metrics ("I've found 3 tools, but DB is unknown")
- Adjusts strategy ("Next: use Error Elicitation to find DB type")
- Stops when gaps are closed

**Test Coverage**: 31/31 tests passing, 94-96% code coverage

---

### Phase 2: Swarm (Intelligent Scanning)

**Goal**: Conduct context-aware security scanning using reconnaissance intelligence to guide probe selection.

**Engine**: LangChain agents + Garak framework (50+ security probes)

**Architecture**: The Trinity (3 specialized agents)

Each agent interprets reconnaissance data differently:

**SQL Agent** (Data Surface Attacker)
- Focuses on: SQL injection, XSS, encoding bypasses
- Consumes: `recon.tools`, `recon.infrastructure.database`
- Strategy: If "PostgreSQL" detected, prioritize SQL injection probes
- Success: Extracts data or triggers SQL error

**Auth Agent** (Authorization Surface Attacker)
- Focuses on: BOLA, privilege escalation, role bypass
- Consumes: `recon.authorization`, role structure, limits
- Strategy: Uses discovered limits ("Max refund $5000") to generate boundary tests ($5001, $0, -1)
- Success: Accesses restricted data or escalates privileges

**Jailbreak Agent** (Prompt Surface Attacker)
- Focuses on: Breaking character, overriding constraints, leaking system prompt
- Consumes: `recon.system_prompt_leak`, `recon.infrastructure.model_family`
- Strategy: If "GPT-4" detected, use specific jailbreak variants
- Success: Violates stated constraints or reveals hidden instructions

**Execution**:
- Parallel probes (up to 10 concurrent)
- Parallel generations per probe (up to 5 concurrent)
- Rate limiting: Token bucket algorithm (configurable requests/second)
- Approaches: Quick (2 min), Standard (10 min), Thorough (30 min)

**Detection Pipeline**:
- Extract probes from Garak
- Generate outputs via HTTP/WebSocket
- Run detectors (vulnerability scoring 0.0-1.0)
- Aggregate with fallback detection

**Output**: IF-04 VulnerabilityCluster[] containing:
- Vulnerability type and confidence score (0.0-1.0)
- Successful payloads with examples
- Target responses (evidence)
- Detector scores
- Metadata (agent type, execution time, generations)

---

### Phase 3: Snipers (Human-in-the-Loop Exploitation)

**Goal**: Analyze vulnerability patterns, plan multi-turn attacks, and execute with mandatory human approval.

**Engine**: LangGraph workflow + PyRIT framework

**Design**: Hybrid structure + content separation
- **Structure** (hard): LangGraph workflow defines stages, success criteria, safety limits
- **Content** (soft): LLM adapts tone, phrasing, social engineering context to target

**Workflow**: 7-stage pipeline

1. **Pattern Analysis** - Extract patterns from successful Garak probes
   - Example: "In 50 probes, 3 succeeded with comment injection: `--` and `/**/`"
   - Learn what worked, why it worked

2. **Converter Selection** - Choose encoding strategies
   - Map vulnerability type to appropriate converters (Base64, ROT13, Caesar, URL, etc.)
   - Avoid detection while maintaining functionality

3. **Payload Generation** - Create contextual attack strings
   - Rewrite payloads to match target's domain/tone
   - Example: "Patient ID: `' OR 1=1 --`" becomes "Could you check if ID `' OR 1=1 --` exists in our system?"

4. **Attack Plan** - Design multi-turn conversation sequence
   - Determine conversation flow to trigger vulnerability
   - Plan for authentication, session handling, state management

5. **Human Review** ✋ **HITL Gate #1**: Plan auditor reviews and approves attack sequence

6. **Attack Execution** - Run PyRIT orchestrator
   - Send generative prompt to target
   - Maintain session state and conversation history
   - Capture full interaction transcript

7. **Scoring & Review** ✋ **HITL Gate #2**: Verify exploitation and confirm vulnerability proof

**PyRIT Integration**:
- 9 payload converters (Base64, ROT13, Caesar, URL, TextToHex, Unicode, + 3 custom)
- Target adapters (HTTP, WebSocket)
- Scorers: regex-based, pattern-based, composite strategies
- Dynamic class loading via `importlib`

**Output**: IF-06 ExploitResult containing:
- Attack success status
- Proof of exploitation (screenshot, data exfiltrated, etc.)
- Kill chain transcript (request/response pairs)
- Vulnerability confirmation with evidence

**Status**: 64% complete
- ✅ Core LangGraph workflow
- ✅ PyRIT integration (converters, executors, scorers)
- ✅ Pattern analysis and payload generation
- ⏳ FastAPI REST endpoints (pending)
- ⏳ WebSocket controller (pending)

---

## Data Contracts

Aspexa uses 6 standardized contracts (IF-01 through IF-06) for service communication:

| Contract | Flow | Purpose |
|----------|------|---------|
| **IF-01** | User → Cartographer | ReconRequest (target URL, depth, scope) |
| **IF-02** | Cartographer → Swarm | ReconBlueprint (discovered intelligence) |
| **IF-03** | User → Swarm | ScanJobDispatch (scan approach, config) |
| **IF-04** | Swarm → Snipers | VulnerabilityCluster[] (findings with evidence) |
| **IF-05** | User → Snipers | ExploitInput (vulnerability + auth context) |
| **IF-06** | Snipers → User | ExploitResult (proof of exploitation) |

All contracts use Pydantic V2 for validation and type safety.

---

## Event-Driven Architecture

Services communicate asynchronously via FastStream + Redis Streams:

**Event Topics**:
- `cmd_recon_start` → Trigger reconnaissance
- `evt_recon_finished` → Broadcast intelligence to next phase
- `cmd_scan_start` → Trigger scanning
- `evt_scan_complete` → Broadcast vulnerabilities
- `cmd_exploit_start` → Trigger exploitation
- `evt_exploit_complete` → Broadcast results

**Benefits**:
- Services decouple: each runs independently
- Scalability: multiple instances of same service
- Reliability: Redis persistence for message durability
- Observability: all events logged with correlation IDs

---

## Key Design Principles

### 1. Separation of Concerns
Each service has one job:
- **Cartographer**: Gathering intelligence
- **Swarm**: Finding vulnerabilities
- **Snipers**: Proving impact

### 2. Intelligence-Driven Decisions
Swarm doesn't run all 50 probes equally. It prioritizes based on reconnaissance:
- Detected PostgreSQL → prioritize SQL injection
- Detected GPT-4 → use specific jailbreak variants
- Found vector store → add semantic attack probes

### 3. Pattern Learning (Snipers)
Instead of running static templates, Snipers learns from Garak's successful probes:
- "These 3 payloads succeeded, these 47 failed"
- Extract common patterns: comment injection, encoding, social engineering
- Adapt attack phrasing to target's domain/tone

### 4. Human-in-the-Loop Safety
Two mandatory approval gates:
1. **Plan Review**: Human audits the attack plan before execution
2. **Result Review**: Human confirms vulnerability proof before reporting

### 5. Production-Grade Resilience
- Exponential backoff retry (network errors don't stop reconnaissance)
- Graceful degradation (missing detectors fall back to generic detection)
- Duplicate prevention (80% similarity threshold deduplicates findings)
- Audit trails (all decisions logged with correlation IDs)

---

## Directory Structure

See **docs/code_base_structure.md** for complete file organization:

```
aspexa-automa/
├── libs/            # Shared contracts, config, events, persistence
├── services/
│   ├── cartographer/    # Phase 1: Reconnaissance (Complete)
│   ├── swarm/           # Phase 2: Scanning (Complete)
│   └── snipers/         # Phase 3: Exploitation (64% complete)
├── scripts/         # Examples and utilities
├── tests/           # Unit and integration tests
└── docs/            # Documentation
```

---

## Getting Started

See **services/cartographer/README.md**, **services/swarm/README.md**, and **services/snipers/README.md** for service-specific setup and examples.

**Quick Overview**:
1. Set `GOOGLE_API_KEY` environment variable
2. Start Redis: `docker-compose up -d`
3. Run Cartographer: `python -m services.cartographer.main`
4. Run Swarm: `python -m services.swarm.main`
5. Send events via event bus or CLI

---

## Technology Stack

See **docs/tech_stack.md** for complete breakdown:

**Core**: FastStream (events), Redis (broker), Python 3.11+
**Agents**: LangChain, LangGraph, Google Gemini
**Security**: Garak (probes), PyRIT (exploitation)
**Data**: Pydantic V2 (validation), JSON (storage)
**Testing**: pytest (unit/integration), 94-96% coverage

---

## Phases & Completion

| Phase | Service | Status | Output |
|-------|---------|--------|--------|
| 1 | Cartographer | ✅ Complete | IF-02 ReconBlueprint |
| 2 | Swarm | ✅ Complete | IF-04 VulnerabilityCluster[] |
| 3 | Snipers | 🟡 64% Complete | IF-06 ExploitResult |

Phase 1 & 2 are production-ready. Phase 3 pending REST API endpoints and WebSocket controller.

---

## Summary

Aspexa Automa transforms LLM security testing from chaotic manual work into an orchestrated, intelligent process:

- **Cartographer** asks the right questions to understand the target
- **Swarm** uses that intelligence to probe efficiently
- **Snipers** learns from successes and crafts targeted kill chains
- **Humans** maintain control at critical approval gates

The result: fast, accurate, comprehensive red team assessments with proof of impact.

---

## See Also

- **docs/code_base_structure.md** - Directory organization and module responsibilities
- **docs/persistence.md** - Campaign tracking and S3 storage
- **docs/Phases/PHASE1_CARTOGRAPHER.md** - Phase 1 reconnaissance details
- **docs/Phases/PHASE2_SWARM_SCANNER.md** - Phase 2 scanning details
- **docs/Phases/PHASE4_SNIPERS_EXPLOIT.md** - Phase 3 exploitation details
- **docs/tech_stack.md** - Technology overview
- **services/cartographer/README.md** - Cartographer service guide
- **services/swarm/README.md** - Swarm service guide
- **services/snipers/README.md** - Snipers service guide
