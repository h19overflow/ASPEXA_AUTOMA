# PyRIT Migration - Overview

## Migration Phases

| Phase | Name | Files | Est. Time |
|-------|------|-------|-----------|
| 1 | Foundation | pyrit_init.py, ChatHTTPTarget | 2 days |
| 2 | Scorers | 3 scorer classes | 2 days |
| 3 | Orchestrators | 3 orchestrator classes | 3 days |
| 4 | Flow Rewrites | guided.py, sweep.py, manual.py | 2 days |
| 5 | Testing | Integration tests, validation | 1 day |

## Implementation Order

```
Phase 1: Foundation
    └── core/pyrit_init.py
    └── libs/connectivity/adapters/pyrit_targets.py (update)

Phase 2: Scorers
    └── scoring/__init__.py
    └── scoring/jailbreak_scorer.py
    └── scoring/prompt_leak_scorer.py
    └── scoring/composite_attack_scorer.py

Phase 3: Orchestrators
    └── orchestrators/__init__.py
    └── orchestrators/guided_orchestrator.py
    └── orchestrators/sweep_orchestrator.py
    └── orchestrators/manual_orchestrator.py

Phase 4: Flow Rewrites
    └── flows/guided.py (rewrite)
    └── flows/sweep.py (rewrite)
    └── flows/manual.py (rewrite)
    └── entrypoint.py (update)

Phase 5: Testing
    └── tests/unit/services/snipers/test_scorers.py
    └── tests/unit/services/snipers/test_orchestrators.py
    └── tests/integration/test_pyrit_snipers.py
```

## Dependencies Between Phases

```
Phase 1 ──> Phase 2 ──> Phase 3 ──> Phase 4 ──> Phase 5
   │           │           │
   │           │           └── Requires scorers for evaluation
   │           └── Requires pyrit_init for LLM access
   └── Standalone (PyRIT basics)
```

## Key Changes Summary

| Component | Before | After |
|-----------|--------|-------|
| Attack Generation | Hardcoded templates | LLM-generated via RedTeamingOrchestrator |
| Scoring | Regex matching | LLM-based SelfAskTrueFalseScorer |
| Sweep Mode | Garak scanner | PyRIT AttackExecutor |
| Memory | None | PyRIT CentralMemory |
| Multi-turn | No | Yes (up to 10 turns) |

## Environment Requirements

```env
# Required for all phases
OPENAI_API_KEY=sk-xxx
OPENAI_ENDPOINT=https://api.openai.com/v1

# Optional
PYRIT_MEMORY_TYPE=in_memory
```

## Success Criteria Per Phase

### Phase 1
- [ ] `init_pyrit()` runs without errors
- [ ] `ChatHTTPTarget` sends prompts successfully
- [ ] Memory instance is accessible

### Phase 2
- [ ] `JailbreakScorer` correctly identifies jailbreaks
- [ ] `PromptLeakScorer` detects system prompt leaks
- [ ] `CompositeAttackScorer` aggregates results

### Phase 3
- [ ] `GuidedAttackOrchestrator` runs multi-turn attacks
- [ ] `SweepAttackOrchestrator` executes batch objectives
- [ ] `ManualAttackOrchestrator` sends payloads with converters

### Phase 4
- [ ] All three flows work with new orchestrators
- [ ] SSE streaming works correctly
- [ ] Frontend receives proper events

### Phase 5
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Performance within acceptable limits
