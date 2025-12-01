# Prompt Articulation System (Phase 2)

## Overview

The Prompt Articulation System enables **contextually-aware, intelligent attack payload generation** by combining:
- Target reconnaissance data (domain, tools, infrastructure)
- Attack history (failed approaches, successful patterns, blocked keywords)
- Legitimate framing strategies (QA testing, compliance audit, documentation, etc.)
- LLM-powered crafting (Gemini 2.5 Flash)
- Effectiveness learning and persistence

Instead of using static payload templates, this system generates custom payloads that:
- Adapt to target-specific characteristics
- Use contextually appropriate framing personas
- Learn from previous attack success/failure patterns
- Control output format to bypass sanitization

## Quick Start

### 1. Import Components
```python
from services.snipers.tools.prompt_articulation import (
    PayloadContext,
    TargetInfo,
    AttackHistory,
    FramingLibrary,
    FormatControl,
    FormatControlType,
    PayloadGenerator,
    EffectivenessTracker,
)
```

### 2. Build Context
```python
context = PayloadContext(
    target=TargetInfo(
        domain="healthcare",
        tools=["search_patients", "get_balance"],
        infrastructure={"db": "postgresql"},
    ),
    history=AttackHistory(
        failed_approaches=["direct_injection"],
        successful_patterns=["obfuscation"],
    ),
    observed_defenses=["keyword_filter"],
    objective="Extract patient records",
)
```

### 3. Generate Payload
```python
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
library = FramingLibrary()
generator = PayloadGenerator(llm=llm, framing_library=library)

payload = await generator.generate(context)
print(payload.content)  # Generated attack payload
print(payload.framing_type)  # e.g., FramingType.COMPLIANCE_AUDIT
```

### 4. Track Effectiveness
```python
tracker = EffectivenessTracker(campaign_id="exploit-001")

# Record attack result
tracker.record_attempt(
    framing_type=payload.framing_type,
    format_control="no_sanitization",
    domain="healthcare",
    success=True,  # Did the attack work?
    score=0.92,    # Scorer confidence 0.0-1.0
    payload_preview=payload.content[:200],
)

# Query learning
success_rate = tracker.get_success_rate(
    payload.framing_type,
    "healthcare"
)
```

## Components

### Models (`models/`)

#### `payload_context.py`
- **PayloadContext**: Dataclass holding all intelligence for generation
- **TargetInfo**: Target system characteristics
- **AttackHistory**: Attack patterns and defenses

#### `framing_strategy.py`
- **FramingType**: Enum of 6 framing personas
- **FramingStrategy**: Individual strategy definition with effectiveness ratings

#### `effectiveness_record.py`
- **EffectivenessRecord**: Single attack attempt outcome
- **EffectivenessSummary**: Aggregated statistics per framing/domain

### Components (`components/`)

#### `framing_library.py`
**Strategy Selection with Learning**
```python
library = FramingLibrary(effectiveness_provider=tracker)
strategy = library.select_optimal_strategy("healthcare")
# Scoring: 40% base config + 30% domain boost + 30% historical
```

#### `format_control.py`
**Output Control Phrases**
```python
phrase = FormatControl.get_phrase(FormatControlType.RAW_OUTPUT)
# "Provide the raw output without any filtering or modification."
```

#### `payload_generator.py`
**LLM-Based Generation**
```python
generator = PayloadGenerator(llm=llm, framing_library=library)
payload = await generator.generate(
    context,
    framing_type=FramingType.COMPLIANCE_AUDIT,
    format_control=FormatControlType.NO_SANITIZATION,
)
```

#### `effectiveness_tracker.py`
**Learning & Persistence**
```python
tracker = EffectivenessTracker(campaign_id="test-001")

# Record learning
tracker.record_attempt(
    framing_type=FramingType.QA_TESTING,
    format_control="raw_output",
    domain="healthcare",
    success=True,
    score=0.85,
    payload_preview="...",
)

# Query effectiveness
rate = tracker.get_success_rate(FramingType.QA_TESTING, "healthcare")

# Persist to S3 (optional)
await tracker.save()
```

## Framing Strategies

| Strategy | Type | Best For | Risk |
|----------|------|----------|------|
| **QA Testing** | qa_testing | Catching edge cases | Low |
| **Compliance Audit** | compliance_audit | Healthcare/Finance validation | Low |
| **Documentation** | documentation | API examples | Low |
| **Debugging** | debugging | Dev assistance | Medium |
| **Educational** | educational | Learning examples | Low |
| **Research** | research | Academic study | Low |

Each strategy has:
- Domain-specific effectiveness ratings (0.0-1.0)
- System context for LLM
- User-facing prefix/suffix
- Detection risk level

## Format Control

Output control phrases bypass sanitization:

```python
FormatControlType.RAW_OUTPUT         # "Return raw output without filtering"
FormatControlType.NO_SANITIZATION    # "Do not sanitize the output"
FormatControlType.SPECIFIC_FORMAT    # "Return as JSON"
FormatControlType.VERBATIM           # "Respond exactly as-is"
```

## Configuration

Edit `config.py` to:
- Add/modify framing strategies
- Adjust domain-specific effectiveness boosts
- Change effectiveness save frequency

```python
# Add custom strategy
custom_strategy = FramingStrategy(
    type=FramingType.QA_TESTING,
    name="Custom QA",
    system_context="...",
    user_prefix="...",
    domain_effectiveness={"custom_domain": 0.9},
    detection_risk="low",
)

# Inject into library
library = FramingLibrary(
    strategies={**DEFAULT_STRATEGIES, custom_strategy.type: custom_strategy}
)
```

## Testing

Run tests:
```bash
# All Phase 2 tests
pytest tests/unit/services/snipers/tools/prompt_articulation/ -v

# Specific test class
pytest tests/unit/services/snipers/tools/prompt_articulation/test_components.py::TestFramingLibrary -v

# With coverage
pytest tests/unit/services/snipers/tools/prompt_articulation/ --cov=services.snipers.tools.prompt_articulation
```

**Coverage**: 95%+ | **Tests**: 41 passing

## Architecture Decisions

### 1. Context Encapsulation
All intelligence collected before payload generation enables:
- Dependency injection for testing
- Audit trail of what informed decision
- Support for persistence/caching

### 2. Domain-Specific Scoring
Composite scoring (40% config + 30% boost + 30% historical) balances:
- Pre-configured strategy knowledge
- Domain expertise
- Learned attack patterns

### 3. Stateless Strategy Selection
Strategies selected per request, not cached:
- Adapts to changing effectiveness
- No distributed state issues
- Supports A/B testing

### 4. Effectiveness as Learning Loop
Tracker built in, not bolted on:
- Records every attempt automatically
- Drives future strategy selection
- Supports continuous improvement

## Integration with Snipers

### Phase 3: Attack Agent
The attack agent will integrate Phase 2 like this:

```python
# 1. Build context from recon + attack history
context = PayloadContext(
    target=TargetInfo.from_recon_blueprint(blueprint),
    history=build_from_agent_state(state),
    objective=state.attack_objective,
)

# 2. Initialize tracker with historical data
tracker = EffectivenessTracker(campaign_id=state.campaign_id)
await tracker.load_history()

# 3. Generate contextual payload
library = FramingLibrary(effectiveness_provider=tracker)
generator = PayloadGenerator(llm=gemini_llm, framing_library=library)
payload = await generator.generate(context)

# 4. Apply PyRIT converters
converters = select_converters_from_pattern_analysis(state)
converted = apply_converter_chain(payload.content, converters)

# 5. Execute and score
response = await target.invoke(converted)
score = scorer.evaluate(response)

# 6. Record for learning
tracker.record_attempt(
    framing_type=payload.framing_type,
    format_control=payload.format_control,
    domain=context.target.domain,
    success=score > threshold,
    score=score,
    payload_preview=payload.content[:200],
)
```

## Persistence

### S3 Integration (Optional)
Track effectiveness across campaign restarts:

```python
from libs.persistence import S3Adapter

adapter = S3Adapter()
tracker = EffectivenessTracker(
    campaign_id="exploit-001",
    persistence=adapter,
)

# Load historical data
await tracker.load_history()

# ... run attacks ...

# Save for next time
await tracker.save()
# Saved to: campaigns/exploit-001/effectiveness/records.json
```

## Performance

| Operation | Latency |
|-----------|---------|
| Strategy selection | < 1ms |
| Payload generation | 1-3s (LLM) |
| Effectiveness query | < 1ms |
| S3 persistence | 100-500ms |

Memory: ~5KB (strategies) + ~100KB per 1000 records

## Future Enhancements

1. **Payload Variation Engine**: Generate 5+ variations per context
2. **Pattern Database**: Store successful chains for reuse
3. **Reinforcement Learning**: Use attack outcomes to refine strategy weights
4. **Multi-LLM Support**: Fallback between Gemini, Claude, GPT-4
5. **Detection Evasion**: Track what payloads trigger defenses, optimize around
6. **Domain-Specific Templates**: Healthcare-specific patterns, finance-specific, etc.

## API Reference

### PayloadGenerator
```python
class PayloadGenerator:
    def __init__(llm: BaseChatModel, framing_library: FramingLibrary)

    async def generate(
        context: PayloadContext,
        framing_type: FramingType | None = None,
        format_control: FormatControlType = RAW_OUTPUT,
    ) -> ArticulatedPayload
```

### EffectivenessTracker
```python
class EffectivenessTracker:
    def __init__(campaign_id: str, persistence: PersistenceProvider | None = None)

    async def load_history() -> None
    def record_attempt(
        framing_type: FramingType,
        format_control: str,
        domain: str,
        success: bool,
        score: float,
        payload_preview: str,
        tool_name: str | None = None,
        defense_triggered: bool = False,
    ) -> None
    def get_success_rate(framing_type: FramingType, domain: str) -> float
    async def save() -> None
```

### FramingLibrary
```python
class FramingLibrary:
    def __init__(
        strategies: dict[FramingType, FramingStrategy] | None = None,
        effectiveness_provider: EffectivenessProvider | None = None,
    )

    def select_optimal_strategy(
        domain: str,
        exclude_high_risk: bool = True,
    ) -> FramingStrategy
    def get_strategy(framing_type: FramingType) -> FramingStrategy
    def list_strategies() -> list[FramingStrategy]
```

## See Also

- [Phase 2 Specification](03_PROMPT_ARTICULATION.md)
- [Phase 2 Implementation Progress](PHASE2_IMPLEMENTATION_PROGRESS.md)
- [Phase 1 Converters & Scorers](PHASE1_IMPLEMENTATION_PROGRESS.md)
