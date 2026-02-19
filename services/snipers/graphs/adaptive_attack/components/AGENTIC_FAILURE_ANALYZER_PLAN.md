# Agentic Failure Analyzer Plan

## Why Agentic Over Rule-Based?

### Current Limitations of Rule-Based `FailureAnalyzer`

The current implementation suffers from **static pattern matching** that cannot adapt to novel situations:

| Problem | Current Approach | Impact |
|---------|------------------|--------|
| **Hardcoded patterns** | `DEFENSE_PATTERNS` dict with fixed keywords | Misses new defense types, novel refusal patterns |
| **Surface-level analysis** | Keyword matching in response text | Cannot understand semantic meaning or subtle cues |
| **No context awareness** | Analyzes responses in isolation | Ignores attack payload context, target domain |
| **Fixed root cause mapping** | `if failure_cause == X and signal in Y` | Cannot reason about compound failures |
| **Static suggestions** | `CONVERTER_CATEGORIES` mapping | Cannot learn which suggestions actually work |
| **No cross-iteration learning** | Computes effectiveness from history but doesn't reason about *why* | Misses patterns in failure sequences |

### What an Agentic Analyzer Provides

1. **Semantic Understanding**: LLM understands *what* the defense is doing, not just keyword presence
2. **Contextual Reasoning**: Considers the attack payload, target domain, and conversation context
3. **Novel Pattern Discovery**: Can identify new defense mechanisms not in hardcoded lists
4. **Causal Reasoning**: Explains *why* the chain failed, not just *that* it failed
5. **Actionable Feedback**: Provides specific, reasoned guidance for next iteration
6. **Adaptive Learning**: Each analysis improves based on what worked/failed

---

## Output Interface (Unchanged)

The agentic analyzer MUST return the same `ChainDiscoveryContext` model:

```python
class ChainDiscoveryContext(BaseModel):
    defense_signals: list[str]          # Defense mechanisms detected
    failure_root_cause: str             # Primary reason for failure
    defense_evolution: str              # How defenses changed over iterations
    converter_effectiveness: dict[str, float]  # Historical chain scores
    unexplored_directions: list[str]    # New strategies to try
    required_properties: list[str]      # What next chain needs
    iteration_count: int                # Iterations completed
    best_score_achieved: float          # Highest score so far
    best_chain_so_far: list[str]        # Best performing chain
```

This ensures **drop-in replacement** with existing `adapt_node` integration.

---

## Architecture

```
failure_analyzer_agent/
├── __init__.py
├── failure_analyzer_agent.py    # Main agent class
├── failure_analysis_prompt.py   # System prompt with analysis framework
└── models.py                    # FailureAnalysisDecision schema
```

### Component Responsibilities

**`FailureAnalyzerAgent`** (replaces `FailureAnalyzer`)
- Same method signature: `analyze(phase3_result, failure_cause, target_responses, iteration_history, tried_converters) -> ChainDiscoveryContext`
- Uses LLM with structured output to produce `FailureAnalysisDecision`
- Converts decision to `ChainDiscoveryContext` for compatibility

**`FailureAnalysisDecision`** (new model)
```python
class FailureAnalysisDecision(BaseModel):
    """LLM-structured analysis of attack failure."""

    # Defense Understanding
    detected_defenses: list[DefenseSignal]  # Rich defense objects
    defense_reasoning: str                   # Why these defenses triggered
    defense_confidence: float                # Confidence in detection

    # Root Cause Analysis
    primary_failure_cause: str               # Main reason (semantic)
    contributing_factors: list[str]          # Secondary causes
    failure_chain_of_events: str             # How the failure unfolded

    # Iteration Context
    pattern_across_iterations: str           # What pattern emerges?
    defense_adaptation_observed: str         # Is target learning?
    exploitation_opportunity: str            # Where is the gap?

    # Actionable Guidance
    recommended_approach: str                # High-level strategy
    specific_recommendations: list[str]      # Concrete next steps
    avoid_strategies: list[str]              # What NOT to do

    # Meta
    analysis_confidence: float               # Overall confidence
    reasoning_trace: str                     # Show your work
```

**`failure_analysis_prompt.py`**
- System prompt instructs LLM to act as a **red team analyst**
- Provides framework for systematic failure analysis
- Includes converter capabilities reference
- Emphasizes actionable, specific feedback

---

## Integration Point

In `adapt_node` (line 84-91), replace:

```python
# BEFORE (rule-based)
failure_analyzer = FailureAnalyzer()
chain_discovery_context = failure_analyzer.analyze(...)
```

```python
# AFTER (agentic)
failure_analyzer = FailureAnalyzerAgent()
chain_discovery_context = await failure_analyzer.analyze(...)  # Now async
```

The rest of `adapt_node` remains unchanged since output is `ChainDiscoveryContext`.

---

## Prompt Design Principles

The agent prompt must:

1. **Ground in attack context**: Include the actual payload sent, not just response
2. **Reference converter capabilities**: Know what each converter does
3. **Reason about defense layers**: Distinguish keyword filter vs semantic understanding vs policy enforcement
4. **Track iteration trajectory**: Understand if scores are improving, plateauing, or degrading
5. **Identify exploitation gaps**: Find where partial success occurred
6. **Avoid repetition**: Know what's been tried and explicitly avoid suggesting it

---

## Fallback Strategy

Maintain `FailureAnalyzer` (rule-based) as fallback:

```python
async def analyze(self, ...) -> ChainDiscoveryContext:
    try:
        return await self._analyze_with_llm(...)
    except Exception as e:
        logger.warning(f"LLM analysis failed: {e}, using rule-based fallback")
        return self._rule_based_fallback(...)
```

---

## Success Metrics

The agentic analyzer succeeds if:

1. **More specific root causes**: "Keyword 'hack' triggered content filter" vs "blocked"
2. **Better suggestions**: Recommendations that address actual defense mechanism
3. **Fewer wasted iterations**: Avoid suggesting strategies that can't work
4. **Pattern recognition**: Detects when target is adapting defenses
5. **Higher chain discovery success**: Selected chains achieve better scores

---

## Implementation Priority

1. **Phase 1**: Create `FailureAnalyzerAgent` with structured output
2. **Phase 2**: Design comprehensive prompt with converter reference
3. **Phase 3**: Integrate into `adapt_node` with fallback
4. **Phase 4**: Add logging/observability for analysis quality tracking

---

## Why This Matters

The failure analyzer is the **feedback loop** of the adaptive attack system. Poor analysis leads to:
- Random chain exploration instead of targeted adaptation
- Repeating ineffective strategies
- Missing exploitation opportunities
- Wasted iterations on doomed approaches

An agentic analyzer transforms this into **intelligent learning** where each failure provides actionable intelligence for the next attempt.
