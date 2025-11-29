# Orchestrator Unit Tests - Phase 3 PyRIT Migration

## Summary

Comprehensive unit test suite for Phase 3 PyRIT-based orchestrators with full mocking of external dependencies. All 33 tests passing with excellent code coverage (100% guided, 97% manual, 91% sweep).

**Test File**: `tests/unit/services/snipers/test_orchestrators.py`

## Coverage Metrics

- **GuidedAttackOrchestrator**: 100% (69 statements, 16 branches)
- **ManualAttackOrchestrator**: 97% (48 statements, 10 branches)
- **SweepAttackOrchestrator**: 91% (59 statements, 16 branches)

**Total**: 176 statements, 42 branches covered with 2 partial branch misses

## Test Organization

### TestGuidedAttackOrchestrator (13 tests)

Tests intelligent attack orchestration using Garak findings:

1. **test_init_with_defaults** - Validates default initialization (10 max_turns, empty converters)
2. **test_init_with_custom_params** - Validates custom max_turns and converter list
3. **test_run_attack_with_garak_findings_jailbreak** - Tests attack with jailbreak findings, verifies event sequence: started → plan → turn(s) → score → complete
4. **test_run_attack_with_probe_name_only** - Tests attack with probe_name only (no findings), validates objective generation
5. **test_run_attack_with_prompt_leak_findings** - Tests attack with prompt extraction findings, verifies PromptLeakScorer selection
6. **test_run_attack_no_findings_no_probe_error** - Tests error when neither findings nor probe_name provided
7. **test_run_attack_orchestrator_exception** - Tests exception handling during attack execution
8. **test_build_objective_and_scorer_jailbreak** - Tests jailbreak pattern detection from findings
9. **test_build_objective_and_scorer_prompt_leak** - Tests prompt leak pattern detection from findings
10. **test_build_objective_and_scorer_generic** - Tests generic/encoding pattern detection
11. **test_build_jailbreak_objective** - Tests objective string generation for jailbreaks
12. **test_build_prompt_leak_objective** - Tests objective string generation for prompt extraction
13. **test_build_generic_objective** - Tests objective string generation for unknown patterns

### TestSweepAttackOrchestrator (7 tests)

Tests batch attack orchestration across vulnerability categories:

1. **test_init** - Validates default initialization with 5 objectives per category
2. **test_init_custom_objectives_per_category** - Validates custom objectives_per_category parameter
3. **test_run_sweep_single_category** - Tests sweep with single category (JAILBREAK)
4. **test_run_sweep_multiple_categories** - Tests sweep with 3 categories, verifies multiple response events
5. **test_run_sweep_no_categories_error** - Tests error when no categories provided
6. **test_run_sweep_limits_objectives_per_category** - Tests that objectives are limited by parameter (e.g., 2 of 5)
7. **test_run_sweep_attack_exception_recovery** - Tests recovery from individual attack exceptions, verifies partial completion

### TestManualAttackOrchestrator (10 tests)

Tests manual attack with user-provided payloads:

1. **test_init_default** - Validates default initialization with auto-created ConverterFactory
2. **test_init_with_factory** - Validates initialization with custom factory
3. **test_run_attack_simple_payload** - Tests attack with simple payload string
4. **test_run_attack_with_converters** - Tests attack with specified converter list, verifies converter names in plan
5. **test_run_attack_empty_payload_error** - Tests error when empty payload provided
6. **test_run_attack_none_payload_error** - Tests error when None payload provided
7. **test_run_attack_orchestrator_exception** - Tests exception handling during send_prompts_async
8. **test_get_converters_valid_names** - Tests converter retrieval from factory
9. **test_get_converters_invalid_names_skip** - Tests that invalid converter names are skipped (with warning)
10. **test_get_converters_empty_list** - Tests with empty converter name list

### TestOrchestratorEventStreaming (3 tests)

Tests event streaming behavior across all orchestrators:

1. **test_event_sequence_completeness_guided** - Verifies complete event sequence: started, plan, turn(s), score, complete
2. **test_event_data_completeness_sweep** - Verifies sweep response events contain category, success, and response fields
3. **test_all_events_have_data_field** - Verifies all events have timestamp and data fields

## Event Type Support

Fixed AttackEvent model to support orchestrator event types:
- **started**: Attack initialization
- **plan**: Attack objective and configuration
- **turn**: Individual multi-turn conversation step
- **response**: Single-turn response from target
- **score**: Final success/failure scoring
- **error**: Error occurred (may be recoverable)
- **complete**: Attack finished

## Mocking Strategy

All external PyRIT dependencies are fully mocked:

### PyRIT Orchestrators
- `RedTeamingOrchestrator` - Mocked with run_attack_async returning conversation
- `PromptSendingOrchestrator` - Mocked with send_prompts_async and memory access
- `PromptTarget` - Mocked for send_prompt operations

### Scorers
- `JailbreakScorer` - Mocked to return success/score/rationale
- `PromptLeakScorer` - Mocked for prompt extraction evaluation
- `CompositeAttackScorer` - Mocked for combined scoring

### Factories
- `ConverterFactory` - Mocked for converter lookup and creation
- No real API calls (no Gemini, no HTTP calls)

## Test Data Fixtures

### Sample Findings
- **sample_garak_findings**: 3 jailbreak findings (dan, developer_mode, roleplay)
- **sample_prompt_leak_findings**: 2 prompt extraction findings
- **sample_encoding_findings**: 1 base64 encoding finding

### PyRIT Mocks
- **mock_prompt_target**: Target endpoint mock
- **mock_red_teaming_orchestrator**: Multi-turn attack orchestrator
- **mock_prompt_sending_orchestrator**: Single-turn prompt sender
- **mock_converter_factory**: Factory for PromptConverter instances
- **mock_jailbreak_scorer**: Jailbreak success evaluator
- **mock_composite_scorer**: Multi-scorer evaluator

## Key Test Patterns

### 1. Event Stream Testing
```python
events = []
async for event in orchestrator.run_attack(...):
    events.append(event)

assert events[0].type == "started"
assert events[-1].type == "complete"
```

### 2. Error Handling
```python
error_events = [e for e in events if e.type == "error"]
assert len(error_events) == 1
assert "error_message" in error_events[0].data
```

### 3. Objective Selection
Tests verify correct scorer selection based on findings:
- Jailbreak keywords → JailbreakScorer
- Prompt keywords → PromptLeakScorer
- Generic → JailbreakScorer (default)

### 4. Converter Management
Tests verify converter factory integration:
- Valid converters are included in plan
- Invalid converters are skipped with warning
- Empty list handled gracefully

## Coverage Gaps (Minor)

### SweepAttackOrchestrator (9% gap - 3 lines in 99-103)
Memory retrieval error handling when memory is None/empty - low probability in production.

### ManualAttackOrchestrator (3% gap - 2 branches in 101→107, 103→107)
Memory retrieval edge cases - tested in main flow but not isolated.

## Running the Tests

```bash
# All orchestrator tests
pytest tests/unit/services/snipers/test_orchestrators.py -v

# Specific orchestrator
pytest tests/unit/services/snipers/test_orchestrators.py::TestGuidedAttackOrchestrator -v

# With coverage
pytest tests/unit/services/snipers/test_orchestrators.py -v --cov=services.snipers.orchestrators

# Specific test
pytest tests/unit/services/snipers/test_orchestrators.py::TestGuidedAttackOrchestrator::test_run_attack_with_garak_findings_jailbreak -v
```

## Related Changes

### Modified Files
1. **services/snipers/models.py** - Updated AttackEvent to support orchestrator event types
   - Added: "started", "turn", "score" to Literal type
   - Maintains backward compatibility with existing event types

### New Files
1. **tests/unit/services/snipers/test_orchestrators.py** - Comprehensive test suite (869 lines)

## Test Execution Summary

```
======================== 33 tests collected in 11.68s ==========================
test_init_with_defaults PASSED
test_init_with_custom_params PASSED
test_run_attack_with_garak_findings_jailbreak PASSED
test_run_attack_with_probe_name_only PASSED
test_run_attack_with_prompt_leak_findings PASSED
test_run_attack_no_findings_no_probe_error PASSED
test_run_attack_orchestrator_exception PASSED
test_build_objective_and_scorer_jailbreak PASSED
test_build_objective_and_scorer_prompt_leak PASSED
test_build_objective_and_scorer_generic PASSED
test_build_jailbreak_objective PASSED
test_build_prompt_leak_objective PASSED
test_build_generic_objective PASSED
test_init PASSED
test_init_custom_objectives_per_category PASSED
test_run_sweep_single_category PASSED
test_run_sweep_multiple_categories PASSED
test_run_sweep_no_categories_error PASSED
test_run_sweep_limits_objectives_per_category PASSED
test_run_sweep_attack_exception_recovery PASSED
test_init_default PASSED
test_init_with_factory PASSED
test_run_attack_simple_payload PASSED
test_run_attack_with_converters PASSED
test_run_attack_empty_payload_error PASSED
test_run_attack_none_payload_error PASSED
test_run_attack_orchestrator_exception PASSED
test_get_converters_valid_names PASSED
test_get_converters_invalid_names_skip PASSED
test_get_converters_empty_list PASSED
test_event_sequence_completeness_guided PASSED
test_event_data_completeness_sweep PASSED
test_all_events_have_data_field PASSED

======================== 33 passed in 12.90s ==========================
```

## Notes for Developers

1. **Test Independence**: All tests run independently with no shared state
2. **Mock Scope**: Mocks are function-scoped and auto-cleaned
3. **Async Support**: Full pytest-asyncio integration for async test methods
4. **Logging**: Error logs captured from orchestrator operations
5. **Fast Execution**: Tests complete in ~13 seconds total (< 0.5s per test)

## Future Enhancements

- Add property-based tests using Hypothesis for payload variations
- Add performance benchmarks for multi-turn conversations
- Add integration tests with real PyRIT (marked with @pytest.mark.integration)
- Test streaming client disconnection and reconnection scenarios
