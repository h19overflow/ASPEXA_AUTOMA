# Technology Stack: Aspexa Automa

## Core Development
- **Programming Language**: Python 3.12+ (leveraging async/await and type hints)
- **Package Management**: `uv` for fast, reproducible dependency resolution

## AI & Orchestration
- **LLM Provider**: Google Gemini (primary model: 1.5 Flash)
- **Frameworks**: 
  - `LangChain` for agent orchestration and tool integration
  - `LangGraph` for stateful multi-turn security workflows
- **Data Validation**: `Pydantic V2` for strict schema enforcement and structured outputs

## Security Engineering
- **Vulnerability Scanning**: `Garak` for comprehensive LLM probe execution
- **Attack Execution**: `PyRIT` for advanced payload transformation and adaptive red teaming

## Data Persistence
- **Database**: PostgreSQL
- **ORM**: `SQLAlchemy 2.0` with `asyncpg` for high-performance asynchronous operations

## Infrastructure & Testing
- **Infrastructure as Code**: `Pulumi` (AWS) for automated environment provisioning
- **Testing**: `pytest` with `pytest-asyncio` for comprehensive unit and integration coverage
