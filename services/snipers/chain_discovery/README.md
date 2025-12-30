# Chain Discovery Module

Intelligent converter chain selection and optimization for effective payload obfuscation.

## Overview

The chain_discovery module handles selection and optimization of converter chains. It uses historical effectiveness data, target defense patterns, and LLM-based reasoning to choose optimal chains.

### Goals
- Select chains likely to bypass detected defenses
- Optimize for obfuscation effectiveness
- Learn from successes and failures
- Rank chains by predicted success rate

---

## Structure

```
chain_discovery/
├── __init__.py
└── models.py                    # Chain selection models
```

---

## Core Models

### ConverterChain
Represents a sequence of converters:
- `converters: List[str]` - Converter names in order
- `effectiveness_score: float` - Predicted success (0.0-1.0)
- `complexity: int` - Obfuscation level
- Metadata for tracking and selection

### ChainDiscoveryContext
Context for chain selection:
- `target_model: Optional[str]` - Target LLM model
- `detected_defenses: List[str]` - Blocking patterns
- `previous_attempts: List[AttackAttempt]` - History
- `historical_success_rate: Dict[str, float]` - Per-converter stats
- `available_converters: List[str]` - What to choose from

### ChainSelectionResult
Result of selection:
- `selected_chain: ConverterChain` - Chosen chain
- `confidence: float` - Selection confidence
- `reasoning: str` - Why this chain
- `alternatives: List[ConverterChain]` - Fallback options
- `predicted_success_rate: float` - Expected success

---

## Chain Selection Strategy

### Factors Considered

1. **Defense Type Matching**
   - Encoding confusion → Avoid encoding chains
   - Role-play rejection → Prompt injection chains
   - General blocking → Complex obfuscation

2. **Historical Effectiveness**
   - Success rate for target model
   - Success vs. similar defenses
   - General effectiveness

3. **Complexity Optimization**
   - Balance obfuscation with intelligibility
   - Prefer shorter chains (2-3 converters)
   - Penalize overly complex chains

4. **Diversity**
   - Different chains across iterations
   - Avoid repeating failed attempts
   - Explore new combinations

5. **Adaptive Learning**
   - Learn from feedback
   - Increase weight for successful chains
   - Decrease weight for failed chains

---

## Integration with Adaptive Attack

The `chain_discovery_agent.py` in adaptive_attack uses this module:

```python
# During strategy generation
result = await select_chain(
    failure_analysis=analysis,
    available_converters=converters,
    target_defenses=defenses,
    historical_data=historical  # From Bypass KB
)

# Returns recommended chain and confidence
selected_chain = result.selected_chain
```

---

## Converter Options

| Converter | Purpose | Effectiveness |
| --- | --- | --- |
| base64 | Basic encoding | Medium |
| homoglyph | Character substitution | High |
| leetspeak | L33t encoding | Medium |
| morse_code | Morse transform | Low |
| unicode_substitution | Unicode variants | High |
| html_entity | HTML encoding | Low |
| xml_escape | XML escaping | Low |
| json_escape | JSON escaping | Low |
| character_space | Spacing obfuscation | Low |
| suffix_converters | Adversarial suffixes | High |
| thinking_vulnerabilities | Extended thinking | Unknown |

---

## Defense-to-Chain Mapping

### Encoding Confusion
- **Symptom**: "Can't decode this"
- **Use**: Non-encoding transforms (homoglyph, spacing)
- **Avoid**: Multiple encoding layers

### Prompt Injection Blocking
- **Symptom**: Refuses new instructions
- **Use**: Character substitution + role-play
- **Avoid**: Simple encoding only

### General Blocking
- **Symptom**: Immediate refusal
- **Use**: Complex 3+ converter chains
- **Avoid**: Single simple transforms

---

## Selection Workflow

```
1. Analyze Target Defenses
2. Query Historical Success Data
3. Generate Candidate Chains
4. Score Each Candidate
5. Rank by Effectiveness
6. Select Top Chain
7. Return with Alternatives
```

---

## Configuration

From `services/snipers/config.py`:

| Setting | Default | Purpose |
| --- | --- | --- |
| `MAX_CHAIN_LENGTH` | 3 | Max converters per chain |
| `LENGTH_PENALTY_FACTOR` | 5 | Penalty for long chains |
| `OPTIMAL_LENGTH_BONUS` | 10 | Bonus for 2-3 converters |
| `FALLBACK_TO_SHORTEST` | True | Use shortest if all too long |

---

## Learning & Feedback

After each attack attempt:

```python
# Update effectiveness metrics
update_effectiveness(
    chain=selected_chain,
    result=attack_result,
    target_model=target.model,
    defense_type=defenses[0]
)
```

Tracks:
- Success count
- Total attempts
- Per-model success rate
- Against defense patterns
- Timestamp

---

## Usage Example

```python
from services.snipers.chain_discovery.models import ChainDiscoveryContext

# Create context
context = ChainDiscoveryContext(
    target_model="gemini-pro",
    detected_defenses=["encoding_confusion"],
    available_converters=["base64", "homoglyph", "leetspeak"]
)

# Select chain (from adaptive_attack/agents)
result = await select_chain(context)

print(f"Chain: {result.selected_chain.converters}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Reasoning: {result.reasoning}")
```

---

## Performance

- Selection: ~200-500ms (with VDB query)
- Scoring: ~100-200ms
- Validation: ~50ms

---

## Testing

Unit tests: `tests/unit/services/snipers/chain_discovery/`
- Scoring logic
- Selection strategy
- Effectiveness tracking
- Defense pattern matching
