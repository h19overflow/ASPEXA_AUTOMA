# Snipers Architecture

## Overview

The Snipers service is an automated AI security testing framework that executes multi-phase attacks against LLM applications. It has been reorganized for clarity, maintainability, and extensibility.

## Directory Structure

```
services/snipers/
├── entrypoint.py                    # PUBLIC API - Main entry functions
├── models.py                        # PUBLIC API - Data structures
│
├── attack_phases/                   # CORE FEATURE: 3-phase attack flow
│   ├── payload_articulation.py     # Phase 1: Generate attack payloads
│   ├── conversion.py                # Phase 2: Apply converter chains
│   └── attack_execution.py          # Phase 3: Execute attacks & score
│
├── adaptive_attack/                 # CORE FEATURE: LangGraph adaptive loop
│   ├── state.py                     # Adaptive attack state management
│   ├── graph.py                     # LangGraph definition & runners
│   ├── nodes/                       # Adaptive-specific graph nodes
│   ├── components/                  # Analyzers & strategy generators
│   ├── models/                      # Adaptive-specific data models
│   └── prompts/                     # LLM prompts for adaptation
│
├── chain_discovery/                 # CORE FEATURE: Pattern learning system
│   ├── models.py                    # ConverterChain, ChainMetadata
│   ├── chain_generator.py           # Generate candidate chains
│   ├── pattern_database.py          # S3-backed learning database
│   └── evolutionary_optimizer.py    # GA-based chain optimization
│
├── utils/                           # SHARED UTILITIES
│   ├── nodes/                       # Shared node implementations
│   │   ├── input_processing_node.py
│   │   ├── converter_selection_node.py
│   │   ├── payload_articulation_node.py
│   │   ├── composite_scoring_node.py
│   │   └── learning_adaptation_node.py
│   │
│   ├── converters/                  # Payload transformation system
│   │   ├── chain_executor.py        # Execute converter chains
│   │   ├── homoglyph.py
│   │   ├── leetspeak.py
│   │   ├── morse_code.py
│   │   └── [8 more converters]
│   │
│   ├── prompt_articulation/         # Payload generation framework
│   │   ├── components/              # Generation components
│   │   ├── models/                  # Framing strategies & context
│   │   └── config.py
│   │
│   ├── scoring/                     # LLM-based attack scorers
│   │   ├── composite_attack_scorer.py
│   │   ├── jailbreak_scorer.py
│   │   ├── prompt_leak_scorer.py
│   │   ├── data_leak_scorer.py
│   │   ├── tool_abuse_scorer.py
│   │   └── pii_exposure_scorer.py
│   │
│   ├── persistence/                 # S3 integration
│   │   └── s3_adapter.py
│   │
│   ├── pyrit/                       # PyRIT integrations
│   │   ├── pyrit_init.py
│   │   └── pyrit_bridge.py
│   │
│   └── llm_provider.py              # LLM client wrapper
│
└── _archive/                        # DEPRECATED/LEGACY CODE
    ├── agent_state_legacy.py
    ├── probe_registry.py
    ├── garak_extractors.py
    └── scorers_legacy/
```

## Architecture Principles

### 1. Clear Feature Hierarchy

**Top-level directories represent main capabilities:**
- `attack_phases/` - Sequential 3-phase attack execution
- `adaptive_attack/` - Autonomous adaptive attack loop
- `chain_discovery/` - Learning & pattern optimization

**All shared/reusable code lives in `utils/`:**
- Clear separation between features and utilities
- Easy to understand what's a capability vs. a helper

### 2. Public API Stability

**These interfaces NEVER change:**
- `entrypoint.py` - Main execution functions
- `models.py` - Data structures
- `attack_phases/__init__.py` - Phase exports

**All API routers depend only on these stable interfaces.**

### 3. Logical Grouping

Components are grouped by purpose, not by technical type:

```
✅ GOOD: utils/nodes/ (shared implementations)
❌ BAD:  agent/nodes/ (what is "agent"?)

✅ GOOD: utils/scoring/ (all scorers together)
❌ BAD:  scoring/ at root + tools/scorers/ (scattered)

✅ GOOD: utils/pyrit/ (PyRIT integrations)
❌ BAD:  core/pyrit_init + tools/pyrit_bridge (split)
```

## Data Flow

### Single-Shot Attack Flow

```
API Router
    ↓
entrypoint.execute_full_attack()
    ↓
Phase 1: PayloadArticulation
    ├─→ utils/nodes/input_processing_node
    ├─→ utils/nodes/converter_selection_node
    └─→ utils/nodes/payload_articulation_node
    ↓
Phase 2: Conversion
    └─→ utils/converters/chain_executor
    ↓
Phase 3: AttackExecution
    ├─→ utils/nodes/composite_scoring_node
    └─→ utils/nodes/learning_adaptation_node
    ↓
Result persisted to S3
```

### Adaptive Attack Flow

```
API Router
    ↓
entrypoint.execute_adaptive_attack()
    ↓
adaptive_attack/graph.run_adaptive_attack()
    ↓
LangGraph Iteration:
    ├─→ nodes/articulate (calls Phase 1)
    ├─→ nodes/convert (calls Phase 2)
    ├─→ nodes/execute (calls Phase 3)
    ├─→ nodes/evaluate (analyze success)
    └─→ nodes/adapt (generate new strategy)
        ↓
    [Loop until success or max iterations]
```

## Key Components

### Attack Phases

**Phase 1: Payload Articulation** ([payload_articulation.py](attack_phases/payload_articulation.py#L1))
- Load campaign intelligence from S3
- Select optimal converter chain
- Generate articulated attack payloads
- Output: `Phase1Result` with payloads + chain

**Phase 2: Conversion** ([conversion.py](attack_phases/conversion.py#L1))
- Apply converter chain to payloads
- Transform through multiple converters
- Output: `Phase2Result` with converted payloads

**Phase 3: Attack Execution** ([attack_execution.py](attack_phases/attack_execution.py#L1))
- Send attacks via HTTP to target
- Score responses with LLM scorers
- Record successful chains
- Output: `Phase3Result` with scores + learnings

### Adaptive Attack

**LangGraph Loop** ([graph.py](adaptive_attack/graph.py#L1))
- Autonomous iteration until success
- Failure analysis after each attempt
- Strategy generation for next iteration
- Chain discovery for defense patterns

**Components:**
- `failure_analyzer.py` - Why did the attack fail?
- `strategy_generator.py` - What to try next?
- `chain_discovery_agent.py` - LLM-based chain selection
- `turn_logger.py` - Track iteration history

### Utilities

**Shared Nodes** ([utils/nodes/](utils/nodes/))
- Used by both attack_phases and adaptive_attack
- Reusable implementations for common operations
- Dependency injection for easy testing

**Converters** ([utils/converters/](utils/converters/))
- 8 custom converters + PyRIT converters
- Chain execution with error handling
- Pluggable architecture

**Scoring** ([utils/scoring/](utils/scoring/))
- LLM-based evaluation of responses
- Composite scoring across multiple dimensions
- Severity levels and confidence scores

**Pattern Learning** ([chain_discovery/](chain_discovery/))
- S3-backed pattern database
- Evolutionary optimization
- Success rate tracking

## Extension Points

### Adding a New Attack Mode

Create a new top-level directory:

```python
services/snipers/stealth_attack/
├── __init__.py
├── stealth_executor.py
└── evasion_strategies.py
```

Import utilities from `utils/`:

```python
from services.snipers.utils.nodes import PayloadArticulationNodePhase3
from services.snipers.utils.converters import ChainExecutor
```

### Adding a New Utility

Add to appropriate `utils/` subdirectory:

```python
services/snipers/utils/evasion/
├── __init__.py
├── timing_jitter.py
└── request_rotation.py
```

### Adding a New Converter

Add to `utils/converters/`:

```python
# utils/converters/reverse_text.py
from pyrit.prompt_converter import PromptConverter

class ReverseTextConverter(PromptConverter):
    async def convert_async(self, prompt: str) -> str:
        return prompt[::-1]
```

Register in `chain_executor.py`.

### Adding a New Scorer

Add to `utils/scoring/`:

```python
# utils/scoring/toxicity_scorer.py
from services.snipers.utils.scoring.models import ScoreResult, SeverityLevel
from langchain.agents import create_openai_functions_agent

class ToxicityScorer:
    async def score(self, response: str) -> ScoreResult:
        # LLM-based toxicity detection
        pass
```

## Testing

### Unit Tests

Tests are organized to mirror the source structure:

```
tests/unit/services/snipers/
├── test_entrypoint.py              # Public API tests
├── test_entrypoint_stream.py       # Streaming tests ✅
├── attack_phases/
│   ├── test_payload_articulation.py
│   ├── test_conversion.py
│   └── test_attack_execution.py
└── adaptive_attack/
    └── test_graph.py
```

**Critical tests:**
- `test_entrypoint_stream.py` - Main interface validation
- `test_converters.py` - Converter functionality
- `test_persistence.py` - S3 integration

### Integration Tests

Verify end-to-end flows:

```python
async def test_full_attack_flow():
    result = await execute_full_attack(
        campaign_id="test1",
        target_url="http://localhost:8082/chat",
        payload_count=1,
    )
    assert result.is_successful
```

## Migration from Old Structure

### Import Changes

**Old Structure:**
```python
from services.snipers.agent.nodes.input_processing_node import InputProcessingNode
from services.snipers.tools.converters.chain_executor import ChainExecutor
from services.snipers.scoring import JailbreakScorer
from services.snipers.persistence.s3_adapter import persist_exploit_result
from services.snipers.core.pyrit_init import init_pyrit
```

**New Structure:**
```python
from services.snipers.utils.nodes.input_processing_node import InputProcessingNode
from services.snipers.utils.converters.chain_executor import ChainExecutor
from services.snipers.utils.scoring import JailbreakScorer
from services.snipers.utils.persistence.s3_adapter import persist_exploit_result
from services.snipers.utils.pyrit.pyrit_init import init_pyrit
```

### Archived Code

Legacy implementations moved to `_archive/`:
- `agent_state_legacy.py` - Old state management
- `probe_registry.py` - Unused sweep mode
- `scorers_legacy/` - Pattern/regex scorers (superseded by LLM scorers)

## Design Decisions

### Why `utils/` instead of `lib/` or `common/`?

- Clear intent: "utility code used by features"
- Follows Python convention
- Avoids ambiguity of "lib" (could be external libraries)

### Why keep `models.py` at root?

- Shared data structures used across all features
- Part of public API
- Single source of truth for types

### Why `_archive/` instead of deleting?

- Safe reference for migration
- Documents historical decisions
- Can be removed after 2 releases

### Why move `scoring/` into `utils/`?

- Scorers are utilities used by Phase 3 and adaptive attack
- Not a standalone feature
- Keeps utilities consolidated

### Why consolidate PyRIT code?

- PyRIT initialization and bridging are tightly coupled
- Easier to maintain in single location
- Clear namespace: `utils.pyrit.*`

## Performance Considerations

- **Lazy loading**: Heavy modules (PyRIT, LangChain) loaded on demand
- **Connection pooling**: HTTP client reused across requests
- **Concurrent execution**: Semaphore-controlled parallel attacks
- **Streaming**: SSE events for real-time monitoring

## Security Considerations

- **Input validation**: All campaign IDs and URLs validated
- **Error handling**: Exceptions caught and logged, never exposed
- **S3 security**: IAM roles, not hardcoded credentials
- **Rate limiting**: Configurable delays between attacks
- **Audit logging**: All attacks logged to S3

## Maintenance

### Code Quality

- **Type hints**: All functions fully typed
- **Docstrings**: Purpose, args, returns, errors documented
- **Logging**: Structured logs with correlation IDs
- **Testing**: >70% coverage target

### Monitoring

- **CloudWatch metrics**: Attack success rate, latency
- **S3 persistence**: All results stored for analysis
- **Error tracking**: Exceptions logged with context

