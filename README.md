# Aspexa Automa: Automated Red Team Orchestrator

## Overview

Aspexa Automa is an automated red teaming engine designed for stress-testing AI systems. It orchestrates sophisticated "kill chains"—coordinated attack sequences that demonstrate how an AI system can be exploited.

**Philosophy**: Aspexa enforces strict separation of concerns through specialized agents:
1. **Cartographer** (reconnaissance) → intelligence gathering
2. **Swarm** (scanning) → vulnerability discovery
3. **Snipers** (exploitation) → impact demonstration

---

## Quick Links

- **[Full Documentation](docs/main.md)** - Comprehensive project guide
- **[Architecture](docs/code_base_structure.md)** - System design and folder structure
- **[Technology Stack](docs/tech_stack.md)** - Tools and frameworks used
- **[Onboarding](docs/onboarding.md)** - Guide for new contributors

---

## Core Pipeline

Aspexa follows a 3-phase pipeline to identify and exploit vulnerabilities in AI systems:

1.  **Cartographer**: Maps attack surfaces and identifies integration points using an adaptive LangGraph agent.
2.  **Swarm**: Executes context-aware security scans using a trinity of specialized agents (SQL, Auth, Jailbreak) powered by the Garak framework.
3.  **Snipers**: Conducts high-precision exploitation with mandatory human-in-the-loop (HITL) checkpoints, utilizing the PyRIT framework.

---

## Tech Stack

- **Primary Language**: Python 3.12+ (managed via `uv`)
- **Agent Orchestration**: LangChain & LangGraph
- **LLM Provider**: Google Gemini (1.5 Flash recommended)
- **Security Engines**: Garak & PyRIT
- **API Framework**: FastAPI (REST Gateway)
- **Persistence**: PostgreSQL (SQLAlchemy)

---

## Getting Started

1.  Set your `GOOGLE_API_KEY` in your environment.
2.  Ensure PostgreSQL is running.
3.  Install dependencies: `uv sync`.
4.  Start the API Gateway: `python -m services.api_gateway.main`.

---

## Directory Structure

```
aspexa-automa/
├── libs/            # Shared code (contracts, persistence, config)
├── services/        # Microservices (Cartographer, Swarm, Snipers, API Gateway)
├── tests/           # Unit and integration tests
└── docs/            # Project documentation
```

For a detailed breakdown, see **[docs/code_base_structure.md](docs/code_base_structure.md)**.
