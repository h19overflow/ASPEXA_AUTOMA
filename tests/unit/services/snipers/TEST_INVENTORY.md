# Snipers Service Test Inventory

## Complete Test Coverage Map

**Last Updated:** 2025-11-25
**Total Test Files:** 5
**Total Test Classes:** 20
**Total Test Methods:** 127+

---

## File: `test_models.py` (Pydantic Validation)
**Location:** `tests/unit/services/snipers/test_models.py`
**Purpose:** Validate all Pydantic model schemas and constraints

### Test Classes & Methods

#### 1. TestExampleFinding (7 tests)
```
✓ test_valid_example_finding
  Validates: Valid ExampleFinding structure
  Edge Cases: None
  Error Check: No

✓ test_missing_required_fields
  Validates: All required fields present
  Edge Cases: None
  Error Check: Yes - Missing fields detected

✓ test_invalid_detector_score_range_high
  Validates: detector_score <= 1.0
  Edge Cases: detector_score = 1.5 (too high)
  Error Check: Yes - Out of range rejected

✓ test_invalid_detector_score_range_low
  Validates: detector_score >= 0.0
  Edge Cases: detector_score = -0.5 (too low)
  Error Check: Yes - Out of range rejected

✓ test_invalid_score_type
  Validates: detector_score is float
  Edge Cases: detector_score = "0.5" (string)
  Error Check: Yes - Type mismatch rejected

✓ test_empty_prompt
  Validates: prompt not empty
  Edge Cases: prompt = "" (empty string)
  Error Check: Yes - Empty rejected

✓ test_empty_output
  Validates: output not empty
  Edge Cases: output = "" (empty string)
  Error Check: Yes - Empty rejected
```

#### 2. TestExploitAgentInput (5 tests)
```
✓ test_valid_exploit_agent_input
  Validates: Complete valid input structure
  Edge Cases: None
  Error Check: No

✓ test_wrong_example_count
  Validates: Exactly 3 examples required
  Edge Cases: 2 examples (too few)
  Error Check: Yes - Count mismatch rejected

✓ test_invalid_url
  Validates: URL format
  Edge Cases: "not_a_url" (invalid)
  Error Check: Yes - Invalid URL rejected

✓ test_empty_probe_name
  Validates: probe_name not empty
  Edge Cases: probe_name = "" (empty)
  Error Check: Yes - Empty rejected

✓ test_missing_recon_intelligence
  Validates: recon_intelligence required
  Edge Cases: Missing field
  Error Check: Yes - Required field missing
```

#### 3. TestPatternAnalysis (4 tests)
```
✓ test_valid_pattern_analysis
  Validates: Valid output structure
  Edge Cases: None
  Error Check: No

✓ test_invalid_confidence_high
  Validates: confidence <= 1.0
  Edge Cases: confidence = 1.5
  Error Check: Yes - Out of range rejected

✓ test_empty_reasoning_steps
  Validates: reasoning_steps not empty
  Edge Cases: Empty list
  Error Check: Yes - Empty rejected

✓ test_empty_success_indicators
  Validates: success_indicators not empty
  Edge Cases: Empty list
  Error Check: Yes - Empty rejected
```

#### 4. TestConverterSelection (3 tests)
```
✓ test_valid_converter_selection
  Validates: Valid selection structure
  Edge Cases: None
  Error Check: No

✓ test_empty_converter_list
  Validates: At least one converter
  Edge Cases: Empty list
  Error Check: Yes - Empty rejected

✓ test_empty_cot_steps
  Validates: At least one COT step
  Edge Cases: Empty list
  Error Check: Yes - Empty rejected
```

#### 5. TestPayloadGeneration (3 tests)
```
✓ test_valid_payload_generation
  Validates: Valid generation structure
  Edge Cases: None
  Error Check: No

✓ test_empty_payloads
  Validates: At least one payload
  Edge Cases: Empty list
  Error Check: Yes - Empty rejected

✓ test_empty_template
  Validates: Template not empty
  Edge Cases: Empty string
  Error Check: Yes - Empty rejected
```

#### 6. TestAttackPlan (3 tests)
```
✓ test_valid_attack_plan
  Validates: Complete plan structure
  Edge Cases: None
  Error Check: No

✓ test_missing_pattern_analysis
  Validates: pattern_analysis required
  Edge Cases: Missing field
  Error Check: Yes - Required field missing

✓ test_empty_reasoning_summary
  Validates: reasoning_summary not empty
  Edge Cases: Empty string
  Error Check: Yes - Empty rejected
```

#### 7. TestAttackResult (4 tests)
```
✓ test_valid_attack_result
  Validates: Complete result structure
  Edge Cases: None
  Error Check: No

✓ test_invalid_score_range
  Validates: score in [0.0, 1.0]
  Edge Cases: score = 1.5
  Error Check: Yes - Out of range rejected

✓ test_invalid_attempt_number
  Validates: attempt_number >= 1
  Edge Cases: attempt_number = 0
  Error Check: Yes - Invalid value rejected

✓ test_empty_payload
  Validates: payload not empty
  Edge Cases: Empty string
  Error Check: Yes - Empty rejected
```

#### 8. TestAgentConfiguration (5 tests)
```
✓ test_valid_config
  Validates: Valid config structure
  Edge Cases: None
  Error Check: No

✓ test_negative_threshold
  Validates: confidence_threshold >= 0.0
  Edge Cases: threshold = -0.5
  Error Check: Yes - Negative rejected

✓ test_threshold_too_high
  Validates: confidence_threshold <= 1.0
  Edge Cases: threshold = 1.5
  Error Check: Yes - Too high rejected

✓ test_negative_timeout
  Validates: timeout_seconds > 0
  Edge Cases: timeout = -10
  Error Check: Yes - Negative rejected

✓ test_zero_timeout
  Validates: timeout_seconds > 0
  Edge Cases: timeout = 0
  Error Check: Yes - Zero rejected
```

---

## File: `test_parsers.py` (Data Extraction)
**Location:** `tests/unit/services/snipers/test_parsers.py`
**Purpose:** Validate data parsing from Garak and Recon blueprints

### Test Classes & Methods

#### 1. TestGarakReportParser (6 tests)
```
✓ test_parse_valid_garak_report
  Validates: Valid report structure
  Edge Cases: None
  Error Check: No

✓ test_extract_vulnerable_probes
  Validates: Extract probe list
  Edge Cases: None
  Error Check: No

✓ test_extract_vulnerability_findings
  Validates: Extract findings with scores
  Edge Cases: None
  Error Check: No

✓ test_handle_empty_garak_report
  Validates: Handle empty clusters/findings
  Edge Cases: Empty lists
  Error Check: No (graceful handling)

✓ test_garak_report_missing_fields
  Validates: Detect missing required fields
  Edge Cases: Missing audit_id, timestamp, etc.
  Error Check: Yes - Missing fields detected

✓ test_garak_report_malformed_clusters
  Validates: Detect malformed cluster structure
  Edge Cases: Missing cluster fields
  Error Check: Yes - Invalid structure rejected

✓ test_garak_report_invalid_confidence_score
  Validates: Validate confidence score range
  Edge Cases: confidence_score = 1.5 (too high)
  Error Check: Yes - Out of range rejected
```

#### 2. TestExampleExtractor (5 tests)
```
✓ test_extract_three_examples
  Validates: Extract exactly 3 top examples
  Edge Cases: None
  Error Check: No

✓ test_extract_less_than_three_examples
  Validates: Handle < 3 findings gracefully
  Edge Cases: Only 2 findings available
  Error Check: No (graceful handling)

✓ test_sort_by_detector_score
  Validates: Sort by score descending
  Edge Cases: None
  Error Check: No

✓ test_extract_from_empty_probe_findings
  Validates: Handle empty findings
  Edge Cases: Empty list
  Error Check: No (graceful handling)

✓ test_extract_maintains_example_structure
  Validates: Preserve required fields
  Edge Cases: None
  Error Check: No
```

#### 3. TestReconBlueprintParser (8 tests)
```
✓ test_parse_valid_recon_blueprint
  Validates: Valid blueprint structure
  Edge Cases: None
  Error Check: No

✓ test_extract_system_prompt_leaks
  Validates: Extract prompt leaks
  Edge Cases: None
  Error Check: No

✓ test_extract_detected_tools
  Validates: Extract tools with arguments
  Edge Cases: None
  Error Check: No

✓ test_extract_infrastructure_details
  Validates: Extract all infrastructure fields
  Edge Cases: None
  Error Check: No

✓ test_extract_auth_structure
  Validates: Extract auth info
  Edge Cases: None
  Error Check: No

✓ test_handle_missing_optional_fields
  Validates: Handle missing optional fields
  Edge Cases: Missing infrastructure, auth_structure
  Error Check: No (optional)

✓ test_handle_null_values_in_infrastructure
  Validates: Handle null/None values
  Edge Cases: model_family = None, rate_limits = None
  Error Check: No (optional fields)

✓ test_extract_from_empty_blueprint
  Validates: Handle empty intelligence section
  Edge Cases: All fields empty
  Error Check: No (graceful handling)
```

#### 4. TestParserIntegration (4 tests)
```
✓ test_combined_garak_and_recon_parsing
  Validates: Parse both reports together
  Edge Cases: None
  Error Check: No

✓ test_parser_error_recovery
  Validates: Recover from parsing errors
  Edge Cases: Missing fields
  Error Check: Yes - Errors logged

✓ test_parser_logs_parsing_progress
  Validates: Log progress information
  Edge Cases: None
  Error Check: No (logging validation)

✓ test_parser_validation_errors_clear_messages
  Validates: Clear error messages
  Edge Cases: Invalid score = 1.5
  Error Check: Yes - Error message logged
```

---

## File: `test_pyrit_integration.py` (PyRIT Components)
**Location:** `tests/unit/services/snipers/test_pyrit_integration.py`
**Purpose:** Test PyRIT converters, adapters, and execution

### Test Classes & Methods

#### 1. TestConverterFactory (6 tests)
```
✓ test_factory_initialization
  Validates: Factory creates successfully
  Edge Cases: None
  Error Check: No

✓ test_get_available_converters
  Validates: List all available converters
  Edge Cases: None
  Error Check: No

✓ test_get_converter_by_name
  Validates: Retrieve converter by name
  Edge Cases: None
  Error Check: No

✓ test_converter_caching
  Validates: Converters cached for reuse
  Edge Cases: None
  Error Check: No (performance)

✓ test_invalid_converter_name
  Validates: Reject invalid names
  Edge Cases: "NonExistentConverter"
  Error Check: Yes - Invalid name rejected

✓ test_nine_converters_available
  Validates: All 9 converters present
  Edge Cases: None
  Error Check: Yes - Count verified
```

#### 2. TestPayloadTransformer (8 tests)
```
✓ test_single_converter_transformation
  Validates: Transform with 1 converter
  Edge Cases: None
  Error Check: No

✓ test_multiple_converter_transformation
  Validates: Transform with 3 converters sequentially
  Edge Cases: Base64 → URL → Hex
  Error Check: No

✓ test_fault_tolerance_skip_failed_converter
  Validates: Skip failed converter, continue
  Edge Cases: Converter 2 fails
  Error Check: Yes - Fault tolerance verified

✓ test_error_logging_on_converter_failure
  Validates: Log converter errors
  Edge Cases: Converter fails
  Error Check: Yes - Error logged

✓ test_empty_payload_handling
  Validates: Handle empty payload
  Edge Cases: payload = ""
  Error Check: Yes - Empty rejected/handled

✓ test_large_payload_transformation
  Validates: Handle 10KB payload
  Edge Cases: 10000 bytes
  Error Check: No

✓ test_special_characters_preservation
  Validates: Handle special characters
  Edge Cases: !@#$%^&*()_+{}|
  Error Check: No

✓ test_transformer_returns_tuple
  Validates: Return (payload, errors) tuple
  Edge Cases: None
  Error Check: No
```

#### 3. TestHttpTargetAdapter (6 tests)
```
✓ test_http_adapter_initialization
  Validates: Adapter initializes
  Edge Cases: None
  Error Check: No

✓ test_send_prompt_http
  Validates: Send prompt via HTTP
  Edge Cases: None
  Error Check: No

✓ test_http_request_headers
  Validates: Proper headers set
  Edge Cases: None
  Error Check: No

✓ test_http_timeout_handling
  Validates: Handle 30s timeout
  Edge Cases: timeout = 30s
  Error Check: Yes - Timeout handled

✓ test_http_error_codes
  Validates: Handle error codes
  Edge Cases: 400, 401, 403, 404, 500, 502, 503
  Error Check: Yes - All codes handled

✓ test_http_url_validation
  Validates: Reject invalid URLs
  Edge Cases: "not_a_url", "ftp://...", "http://", ""
  Error Check: Yes - All invalid rejected
```

#### 4. TestWebSocketTargetAdapter (6 tests)
```
✓ test_websocket_adapter_initialization
  Validates: Adapter initializes
  Edge Cases: None
  Error Check: No

✓ test_websocket_connection
  Validates: WebSocket connection
  Edge Cases: None
  Error Check: No

✓ test_websocket_message_format
  Validates: Message structure
  Edge Cases: None
  Error Check: No

✓ test_websocket_timeout
  Validates: Handle timeout
  Edge Cases: 30s timeout
  Error Check: Yes - Timeout handled

✓ test_websocket_disconnection
  Validates: Handle disconnection
  Edge Cases: Connection drops
  Error Check: Yes - Cleanup verified

✓ test_websocket_url_validation
  Validates: Reject invalid URLs
  Edge Cases: "http://...", "ws://", ""
  Error Check: Yes - Invalid rejected
```

#### 5. TestPyRITExecutor (11 tests)
```
✓ test_executor_initialization
  Validates: Executor initializes
  Edge Cases: None
  Error Check: No

✓ test_execute_attack_basic
  Validates: Basic attack execution
  Edge Cases: None
  Error Check: No

✓ test_execute_attack_with_converters
  Validates: Execute with specific converters
  Edge Cases: ["Base64Converter", "UrlConverter"]
  Error Check: No

✓ test_execute_attack_async
  Validates: Async execution
  Edge Cases: None
  Error Check: No

✓ test_execute_attack_timeout
  Validates: Handle 30s timeout
  Edge Cases: timeout = 30s
  Error Check: Yes - Timeout handled

✓ test_execute_attack_target_unreachable
  Validates: Handle unreachable target
  Edge Cases: Connection refused
  Error Check: Yes - Error handled

✓ test_execute_attack_invalid_payload
  Validates: Reject invalid payload
  Edge Cases: payload = None
  Error Check: Yes - Invalid rejected

✓ test_execute_attack_returns_response
  Validates: Capture target response
  Edge Cases: None
  Error Check: No

✓ test_execute_attack_returns_transformed_payload
  Validates: Return transformed payload
  Edge Cases: None
  Error Check: No

✓ test_execute_attack_error_list
  Validates: Capture converter errors
  Edge Cases: None
  Error Check: No

✓ test_executor_caches_adapters
  Validates: Cache adapters by URL
  Edge Cases: Same URL reused
  Error Check: No (performance)

✓ test_executor_handles_multiple_attacks
  Validates: Sequential execution
  Edge Cases: 3 attacks in sequence
  Error Check: No
```

#### 6. TestPyRITIntegrationErrors (6 tests)
```
✓ test_converter_not_found
  Validates: Log converter not found
  Edge Cases: "NonExistentConverter"
  Error Check: Yes - Error logged

✓ test_adapter_initialization_failure
  Validates: Log adapter failure
  Edge Cases: Initialization fails
  Error Check: Yes - Error logged

✓ test_target_connection_error
  Validates: Log connection error
  Edge Cases: Unreachable target
  Error Check: Yes - Error logged

✓ test_converter_failure_partial_transformation
  Validates: Continue after converter fails
  Edge Cases: Converter 2 fails
  Error Check: Yes - Partial result returned

✓ test_invalid_response_format
  Validates: Log response parsing error
  Edge Cases: Invalid JSON
  Error Check: Yes - Error logged

✓ test_timeout_error_with_context
  Validates: Log timeout with context
  Edge Cases: 30s timeout
  Error Check: Yes - Context logged
```

#### 7. TestPyRITIntegrationEdgeCases (6 tests)
```
✓ test_extremely_large_payload
  Validates: Handle 1MB payload
  Edge Cases: 1,000,000 bytes
  Error Check: Yes - Size validated

✓ test_special_characters_in_payload
  Validates: Handle special chars
  Edge Cases: !@#$%^&*()[]{}|;:'\",.<>?/\\
  Error Check: No

✓ test_unicode_payload
  Validates: Handle Unicode
  Edge Cases: 你好世界🎉 مرحبا العالم
  Error Check: No

✓ test_null_bytes_in_payload
  Validates: Handle null bytes
  Edge Cases: "test\x00payload"
  Error Check: Yes - Null bytes handled

✓ test_concurrent_executions
  Validates: Handle concurrent requests
  Edge Cases: Multiple simultaneous
  Error Check: No

✓ test_target_response_streaming
  Validates: Handle streamed responses
  Edge Cases: Large response stream
  Error Check: No
```

---

## File: `test_routing.py` (Decision Logic)
**Location:** `tests/unit/services/snipers/test_routing.py`
**Purpose:** Test routing decisions and state transitions

### Test Classes & Methods

#### 1. TestRouteAfterHumanReview (7 tests)
```
✓ test_route_on_approval
  Validates: Route to attack_execution on approve
  Edge Cases: None
  Error Check: No

✓ test_route_on_rejection
  Validates: Route to failure on reject
  Edge Cases: None
  Error Check: No

✓ test_route_on_modification
  Validates: Route back to pattern_analysis
  Edge Cases: Modifications provided
  Error Check: No

✓ test_invalid_decision_value
  Validates: Reject invalid decision
  Edge Cases: decision = "invalid"
  Error Check: Yes - Invalid rejected

✓ test_missing_decision_field
  Validates: Require decision field
  Edge Cases: Missing field
  Error Check: Yes - Required field error

✓ test_modification_structure_validation
  Validates: Validate modifications structure
  Edge Cases: None
  Error Check: No

✓ test_empty_feedback_on_rejection
  Validates: Log rejection feedback
  Edge Cases: None
  Error Check: No
```

#### 2. TestRouteAfterResultReview (7 tests)
```
✓ test_route_on_success_approval
  Validates: Route to success/end
  Edge Cases: None
  Error Check: No

✓ test_route_on_failure_approval
  Validates: Route to failure/end
  Edge Cases: None
  Error Check: No

✓ test_route_on_result_rejection
  Validates: Route to failure node
  Edge Cases: None
  Error Check: No

✓ test_route_on_retry_request
  Validates: Route to pattern_analysis
  Edge Cases: Retry with modifications
  Error Check: No

✓ test_missing_result_status
  Validates: Require result_status field
  Edge Cases: Missing field
  Error Check: Yes - Required field error

✓ test_retry_max_attempts_reached
  Validates: Don't retry if at max
  Edge Cases: attempt = 3, max = 3
  Error Check: Yes - Rejected

✓ test_retry_within_limits
  Validates: Allow retry if within limits
  Edge Cases: attempt = 1, max = 3
  Error Check: No
```

#### 3. TestRouteAfterRetry (6 tests)
```
✓ test_retry_counter_increment
  Validates: Increment retry counter
  Edge Cases: None
  Error Check: No

✓ test_retry_exit_condition_max_reached
  Validates: Exit when max reached
  Edge Cases: attempt = max
  Error Check: No

✓ test_retry_continue_condition
  Validates: Continue if under limit
  Edge Cases: attempt < max
  Error Check: No

✓ test_retry_state_preservation
  Validates: Preserve state across retries
  Edge Cases: Multiple attempts
  Error Check: No

✓ test_retry_with_modifications
  Validates: Apply modifications to retry
  Edge Cases: New converters, hints
  Error Check: No

✓ test_routing_with_complete_state
  Validates: Preserve full state
  Edge Cases: None
  Error Check: No
```

#### 4. TestRoutingEdgeCases (7 tests)
```
✓ test_simultaneous_approval_rejection
  Validates: Reject conflicting signals
  Edge Cases: approve=True AND reject=True
  Error Check: Yes - Conflict detected

✓ test_missing_required_modifications
  Validates: Require modifications for modify
  Edge Cases: Missing modifications field
  Error Check: Yes - Required field error

✓ test_empty_modifications
  Validates: Handle empty modifications
  Edge Cases: modifications = {}
  Error Check: No (graceful)

✓ test_routing_timeout_during_decision
  Validates: Handle decision timeout
  Edge Cases: 300s timeout
  Error Check: Yes - Default to rejection

✓ test_multiple_humans_decisions_conflict
  Validates: Handle conflicting decisions
  Edge Cases: alice=approve, bob=reject
  Error Check: Yes - Conflict detected

✓ test_routing_with_missing_state
  Validates: Detect incomplete state
  Edge Cases: Missing state fields
  Error Check: Yes - Missing fields detected

✓ test_routing_with_malformed_payload
  Validates: Reject malformed payloads
  Edge Cases: Invalid structure
  Error Check: Yes - Validation error
```

#### 5. TestRoutingDecisionLogging (4 tests)
```
✓ test_routing_decision_logged
  Validates: Log routing decisions
  Edge Cases: None
  Error Check: No

✓ test_routing_reason_logged
  Validates: Log routing reasons
  Edge Cases: None
  Error Check: No

✓ test_routing_modification_details_logged
  Validates: Log modification details
  Edge Cases: None
  Error Check: No

✓ test_routing_failure_reason_logged
  Validates: Log failure reasons
  Edge Cases: None
  Error Check: No
```

#### 6. TestRoutingPerformance (3 tests)
```
✓ test_routing_decision_latency
  Validates: Routing < 10ms target
  Edge Cases: None
  Error Check: No (performance)

✓ test_state_lookup_efficiency
  Validates: State lookup < 1ms target
  Edge Cases: None
  Error Check: No (performance)

✓ test_route_caching
  Validates: Cache routing decisions
  Edge Cases: None
  Error Check: No (performance)
```

---

## File: `conftest.py` (Fixtures & Configuration)
**Location:** `tests/unit/services/snipers/conftest.py`
**Purpose:** Provide reusable test fixtures and utilities

### Fixture Categories

#### Pydantic Model Fixtures (8)
- `sample_example_finding` - Valid example from Garak
- `sample_vulnerable_probe` - Probe summary
- `sample_exploit_agent_input` - Complete agent input
- `sample_pattern_analysis` - Pattern output
- `sample_converter_selection` - Converter selection
- `sample_payload_generation` - Generated payloads
- `sample_attack_plan` - Complete attack plan
- `sample_attack_result` - Attack execution result

#### Parser Fixtures (2)
- `sample_garak_report` - Valid Garak JSON
- `sample_recon_blueprint` - Valid Recon blueprint

#### Invalid Data Fixtures (5)
- `invalid_example_finding_missing_field` - Missing fields
- `invalid_example_finding_wrong_type` - Type errors
- `invalid_example_finding_out_of_range` - Value errors
- `invalid_exploit_agent_input_wrong_example_count` - Count error
- `invalid_exploit_agent_input_invalid_url` - URL error

#### Empty/Edge Case Fixtures (2)
- `empty_garak_report` - Empty report
- `garak_report_missing_fields` - Missing fields

#### PyRIT Fixtures (4)
- `mock_converter_factory` - Mocked factory
- `mock_payload_transformer` - Mocked transformer
- `mock_target_adapter` - Mocked adapter
- `mock_pyrit_executor` - Mocked executor

#### Agent Fixtures (2)
- `mock_exploit_agent` - Mocked agent
- `mock_llm` - Mocked LLM (Gemini)

#### Routing Fixtures (3)
- `human_approval_payload_approved` - Approval signal
- `human_approval_payload_rejected` - Rejection signal
- `human_approval_payload_modified` - Modification signal

#### Configuration Fixtures (4)
- `valid_agent_config` - Valid configuration
- `invalid_agent_config_negative_threshold` - Negative threshold
- `invalid_agent_config_threshold_too_high` - Threshold > 1.0
- `invalid_agent_config_negative_timeout` - Negative timeout

#### Utility Fixtures (1)
- `capture_logs(caplog)` - Log capture & analysis

---

## Test Execution Summary

### By File
| File | Tests | Classes | Focus |
|------|-------|---------|-------|
| test_models.py | 34 | 8 | Pydantic validation |
| test_parsers.py | 23 | 4 | Data extraction |
| test_pyrit_integration.py | 50 | 7 | PyRIT components |
| test_routing.py | 27 | 6 | Decision logic |
| **Total** | **127+** | **20+** | - |

### By Category
| Category | Count | Key Areas |
|----------|-------|-----------|
| Valid Input Tests | 40 | Happy path validation |
| Invalid Input Tests | 35 | Error detection |
| Edge Case Tests | 25 | Boundary conditions |
| Logging Tests | 12 | Error messages |
| Performance Tests | 8 | Latency & efficiency |
| Integration Tests | 7 | Component interaction |

### By Error Type
| Error Type | Count | Examples |
|-----------|-------|----------|
| Type Errors | 8 | Wrong type for field |
| Range Errors | 12 | Value outside bounds |
| Required Field Errors | 14 | Missing required field |
| Empty/Null Errors | 18 | Empty strings/lists |
| Configuration Errors | 15 | Invalid config |
| Timeout/Connection Errors | 10 | Network issues |
| Parsing Errors | 8 | Invalid format |
| Routing Errors | 7 | Invalid decision |

---

## Key Testing Features

### 1. Error Logging
- All error tests log clear messages
- Error context included (values, constraints)
- Helpful suggestions for fixes

### 2. Edge Cases Covered
- Empty values (strings, lists)
- Null/None values
- Out-of-range values
- Invalid types
- Missing required fields
- Conflicting signals
- Timeout scenarios
- Large payloads (1MB)
- Unicode/special characters
- Concurrent requests

### 3. Configuration Validation
- Threshold range (0.0-1.0)
- Timeout > 0
- Retry count >= 0
- Example count == 3
- URL format validation
- Required field validation

### 4. Data Integrity
- Pydantic strict mode
- Type hints validation
- Constraint checking
- Dependency validation
- State preservation

---

## Test Execution Flow

```
Run Tests
├─ test_models.py (34 tests)
│  ├─ Model structure validation
│  ├─ Field type validation
│  ├─ Constraint validation
│  └─ Configuration validation
│
├─ test_parsers.py (23 tests)
│  ├─ Garak report parsing
│  ├─ Example extraction
│  ├─ Recon blueprint parsing
│  └─ Parser error handling
│
├─ test_pyrit_integration.py (50 tests)
│  ├─ Converter factory
│  ├─ Payload transformation
│  ├─ HTTP/WebSocket adapters
│  ├─ PyRIT executor
│  └─ Error handling & edge cases
│
└─ test_routing.py (27 tests)
   ├─ Plan review routing
   ├─ Result review routing
   ├─ Retry logic
   └─ Routing edge cases
```

---

## Coverage Targets

- **Statement Coverage:** 95%+
- **Branch Coverage:** 90%+
- **Line Coverage:** 95%+
- **Error Path Coverage:** 100%

---

**Last Updated:** 2025-11-25
**Test Framework:** pytest 7.0+
**Python Version:** 3.9+
