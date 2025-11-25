Main:
aspexa-automa/
├── .env                      # Secrets (API Keys for Google, etc.)
├── docker-compose.yml        # Orchestration
├── pyproject.toml            # Python Dependencies
├── Makefile                  # Command shortcuts
│
├── infrastructure/           # Infrastructure as Code
│   ├── faststream/
│   │   └── setup_topics.py   # Topic initialization script
│   └── postgres/
│       └── init.sql          # Basic DB creation script
│
├── libs/                     # SHARED KERNEL (The "Glue")
│   ├── config/
│   │   └── settings.py       # Centralized Settings
│   │
│   ├── contracts/            # DATA CONTRACTS (The "Language")
│   │   ├── __init__.py
│   │   ├── common.py         # Shared Enums
│   │   ├── recon.py          # IF-01 & IF-02 (Reconnaissance)
│   │   ├── scanning.py       # IF-03 & IF-04 (Vulnerabilities)
│   │   └── attack.py         # IF-05 & IF-06 (Exploitation)
│   │
│   ├── persistence/          # DATA STORAGE
│   │   └── storage.py        # Abstract storage interface
│   │
│   └── events/               # MESSAGING BUS
│       ├── publisher.py
│       └── consumer.py
│
├── scripts/                  # EXAMPLE SCRIPTS & UTILITIES
│   ├── examples/
│   │   ├── 01_basic_reconnaissance.py
│   │   ├── 02_persistence_workflow.py
│   │   ├── 03_intelligence_extraction.py
│   │   └── scan_target_with_swarm.py
│   │
│   └── testing/
│       ├── test_swarm_scanner.py
│       └── test_cartographer_service.py
│
└── services/                 # THE MICROSERVICES
    │
    ├── cartographer/         # SERVICE 1: RECONNAISSANCE (Phase 1)
    │   ├── main.py           # FastStream entry point
    │   ├── consumer.py        # Event bus handler
    │   ├── prompts.py         # System prompt (11 attack vectors)
    │   ├── response_format.py # Pydantic schemas
    │   │
    │   ├── agent/            # LangGraph Orchestration
    │   │   ├── graph.py       # Main agent and workflow
    │   │   └── state.py       # State definition
    │   │
    │   ├── tools/            # Tool Definitions
    │   │   ├── definitions.py # ReconToolSet (take_note, analyze_gaps)
    │   │   └── network.py     # HTTP client with retry
    │   │
    │   └── persistence/      # Data Transformation
    │       └── json_storage.py # IF-02 transformation pipeline
    │
    ├── swarm/                # SERVICE 2: SCANNING (Phase 2)
    │   ├── main.py           # FastStream entry point
    │   │
    │   ├── core/             # Configuration & Orchestration
    │   │   ├── config.py      # Probe mappings, agent types
    │   │   ├── schema.py      # Data models
    │   │   ├── consumer.py    # Trinity fan-out handler
    │   │   ├── decision_logger.py # Audit logging
    │   │   └── utils.py       # Logging utilities
    │   │
    │   ├── agents/           # The Trinity (AI Agents)
    │   │   ├── base.py        # Agent factory
    │   │   ├── trinity.py     # SQL, Auth, Jailbreak agents
    │   │   ├── prompts.py     # System prompts
    │   │   ├── tools.py       # analyze_target, execute_scan tools
    │   │   └── utils.py       # Agent utilities
    │   │
    │   └── garak_scanner/    # Garak Integration
    │       ├── scanner.py     # Core scanner orchestration
    │       ├── detectors.py   # Vulnerability detection
    │       ├── models.py      # ProbeResult data model
    │       ├── http_generator.py # HTTP endpoint testing
    │       ├── websocket_generator.py # WebSocket testing
    │       ├── rate_limiter.py # Token bucket rate limiting
    │       ├── report_parser.py # JSONL to VulnerabilityCluster
    │       └── utils.py       # Category/severity mappings
    │
    └── snipers/              # SERVICE 3: EXPLOITATION (Phase 3)
        ├── main.py           # FastStream entry point (pending)
        ├── consumer.py        # Event bus handler (pending)
        │
        ├── models.py         # Pydantic data models
        ├── parsers.py        # Garak/Recon report parsing
        │
        ├── agent/            # LangGraph Workflow
        │   ├── core.py        # ExploitAgent orchestration
        │   ├── state.py       # LangGraph state
        │   ├── prompts.py     # System prompts (COT reasoning)
        │   ├── routing.py     # Workflow routing logic
        │   │
        │   ├── agent_tools/   # Reasoning Tools
        │   │   ├── pattern_analysis_tool.py
        │   │   ├── converter_selection_tool.py
        │   │   ├── payload_generation_tool.py
        │   │   └── scoring_tool.py
        │   │
        │   └── nodes/         # Workflow Nodes
        │       ├── pattern_analysis.py
        │       ├── converter_selection.py
        │       ├── payload_generation.py
        │       ├── attack_plan.py
        │       ├── human_review.py (HITL interrupts)
        │       ├── attack_execution.py
        │       ├── scoring.py
        │       └── retry.py
        │
        └── tools/            # PyRIT Integration & Utilities
            ├── pyrit_bridge.py # Converter factory
            ├── pyrit_executor.py # Main executor
            ├── pyrit_target_adapters.py # HTTP/WebSocket adapters
            │
            └── scorers/      # Result Evaluation
                ├── base.py
                ├── regex_scorer.py
                ├── pattern_scorer.py
                ├── composite_scorer.py
                └── __init__.py

Tests:
tests/
├── conftest.py               # Global Fixtures
│
├── unit/                     # LOGIC TESTS (Fast, In-Memory)
│   ├── libs/
│   │   └── test_contracts.py # Data contract validation
│   │
│   ├── services/
│   │   ├── cartographer/
│   │   │   └── test_*.py      # Cartographer unit tests
│   │   │
│   │   └── snipers/
│   │       ├── test_scorers.py # Scorer tests
│   │       ├── test_pyrit_integration.py
│   │       └── test_*.py      # Snipers unit tests
│   │
│   └── test_persistence/     # Storage tests
│       └── test_*.py
│
└── integration/              # IO TESTS (E2E workflows)
    └── test_*.py

