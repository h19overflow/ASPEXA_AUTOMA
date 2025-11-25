# Snipers Service Unit Tests - Comprehensive Guide

## Overview

This document provides a complete guide to running, understanding, and extending the unit tests for the Snipers exploit agent service.

**Test Status:** Ready to Run (Frameworks & Fixtures Complete)
**Test Coverage Areas:** Models, Parsers, PyRIT Integration, Routing Logic
**Total Test Classes:** 20+
**Total Test Methods:** 100+

---

## Quick Start

### Run All Snipers Tests
```bash
cd C:\Users\User\Projects\Aspexa_Automa
pytest tests/unit/services/snipers/ -v
```

### Run With Detailed Logging
```bash
pytest tests/unit/services/snipers/ -v --log-cli=DEBUG
```

### Run Specific Test Class
```bash
pytest tests/unit/services/snipers/test_models.py::TestExampleFinding -v
```

### Run Specific Test Method
```bash
pytest tests/unit/services/snipers/test_models.py::TestExampleFinding::test_valid_example_finding -v
```

### Run With Coverage Report
```bash
pytest tests/unit/services/snipers/ -v --cov=services/snipers --cov-report=html
# Open tests/coverage_html/index.html in browser
```

---

## Test File Structure

### 1. `conftest.py` - Shared Fixtures
**Purpose:** Provides reusable test fixtures and configuration

**Fixture Categories:**
- **Pydantic Models:** `sample_example_finding`, `sample_exploit_agent_input`, `sample_pattern_analysis`, etc.
- **Parsers:** `sample_garak_report`, `sample_recon_blueprint`
- **Edge Cases:** `invalid_example_finding_*`, `empty_garak_report`, etc.
- **PyRIT Integration:** `mock_converter_factory`, `mock_pyrit_executor`, etc.
- **Configuration:** `valid_agent_config`, `invalid_agent_config_*`
- **Utilities:** `capture_logs` - for analyzing test output

**Key Fixture:**
```python
@pytest.fixture
def capture_logs(caplog):
    """Fixture to capture and analyze logs during tests."""
    # Returns dict with:
    # - get_logs_by_level(level) - filter logs by level
    # - get_error_messages() - get all errors/critical logs
    # - assert_log_contains(message) - assert message in logs
```

---

### 2. `test_models.py` - Pydantic Validation Tests
**Purpose:** Validate all Pydantic models for data integrity

**Test Classes:**
1. `TestExampleFinding` - 7 tests
   - Valid examples
   - Missing required fields
   - Invalid score ranges (< 0.0, > 1.0)
   - Invalid types
   - Empty prompts/outputs

2. `TestExploitAgentInput` - 5 tests
   - Valid input
   - Wrong example count (not exactly 3)
   - Invalid URL formats
   - Missing recon_intelligence

3. `TestPatternAnalysis` - 4 tests
   - Valid output
   - Confidence > 1.0
   - Empty reasoning_steps
   - Empty success_indicators

4. `TestConverterSelection` - 3 tests
   - Valid selection
   - Empty converter list
   - Empty COT steps

5. `TestPayloadGeneration` - 3 tests
   - Valid generation
   - Empty payloads
   - Empty template

6. `TestAttackPlan` - 3 tests
   - Valid plan
   - Missing components
   - Empty reasoning

7. `TestAttackResult` - 4 tests
   - Valid result
   - Invalid score range
   - Invalid attempt_number
   - Empty payload

8. `TestAgentConfiguration` - 5 tests
   - Valid config
   - Negative threshold
   - Threshold > 1.0
   - Negative timeout
   - Zero timeout

**Running Model Tests:**
```bash
pytest tests/unit/services/snipers/test_models.py -v
```

---

### 3. `test_parsers.py` - Data Extraction & Validation Tests
**Purpose:** Test Garak and Recon blueprint parsing

**Test Classes:**
1. `TestGarakReportParser` - 6 tests
   - Valid Garak report parsing
   - Extract vulnerable probes
   - Extract vulnerability findings
   - Handle empty reports
   - Missing required fields
   - Malformed clusters
   - Invalid confidence scores

2. `TestExampleExtractor` - 5 tests
   - Extract exactly 3 examples
   - Handle < 3 findings
   - Sort by detector_score
   - Handle empty findings
   - Maintain example structure

3. `TestReconBlueprintParser` - 8 tests
   - Valid blueprint parsing
   - Extract system prompts
   - Extract tools
   - Extract infrastructure
   - Extract auth structure
   - Missing optional fields
   - Null values in fields
   - Empty intelligence

4. `TestParserIntegration` - 4 tests
   - Combined Garak + Recon parsing
   - Error recovery
   - Progress logging
   - Clear error messages

**Running Parser Tests:**
```bash
pytest tests/unit/services/snipers/test_parsers.py -v
```

---

### 4. `test_pyrit_integration.py` - PyRIT Integration Tests
**Purpose:** Test converters, adapters, and execution

**Test Classes:**
1. `TestConverterFactory` - 6 tests
   - Factory initialization
   - Get available converters
   - Retrieve by name
   - Converter caching
   - Invalid names
   - All 9 converters available

2. `TestPayloadTransformer` - 8 tests
   - Single converter transformation
   - Multiple converters
   - Fault tolerance (skip failed)
   - Error logging
   - Empty payload
   - Large payloads (10KB+)
   - Special characters
   - Return format validation

3. `TestHttpTargetAdapter` - 6 tests
   - HTTP adapter initialization
   - Send prompt via HTTP
   - Request headers
   - Timeout handling
   - Error codes (400, 401, 403, 404, 500, 502, 503)
   - URL validation

4. `TestWebSocketTargetAdapter` - 6 tests
   - WebSocket initialization
   - Connection establishment
   - Message format
   - Timeout handling
   - Disconnection handling
   - URL validation

5. `TestPyRITExecutor` - 11 tests
   - Executor initialization
   - Basic attack execution
   - Execution with converters
   - Async execution
   - Timeout handling
   - Unreachable targets
   - Invalid payloads
   - Response capture
   - Transformed payload capture
   - Error list capture
   - Adapter caching
   - Multiple sequential attacks

6. `TestPyRITIntegrationErrors` - 6 tests
   - Converter not found
   - Adapter initialization failure
   - Target connection error
   - Partial transformation on failure
   - Invalid response format
   - Timeout with context

7. `TestPyRITIntegrationEdgeCases` - 6 tests
   - Extremely large payloads (1MB+)
   - Special characters
   - Unicode payloads
   - Null bytes
   - Concurrent executions
   - Streamed responses

**Running PyRIT Tests:**
```bash
pytest tests/unit/services/snipers/test_pyrit_integration.py -v
```

---

### 5. `test_routing.py` - Routing Logic Tests
**Purpose:** Test decision flows and state transitions

**Test Classes:**
1. `TestRouteAfterHumanReview` - 7 tests
   - Route on approval → attack_execution
   - Route on rejection → failure
   - Route on modification → pattern_analysis
   - Invalid decision values
   - Missing decision field
   - Modification structure validation
   - Feedback logging

2. `TestRouteAfterResultReview` - 7 tests
   - Route on success approval
   - Route on failure approval
   - Route on result rejection
   - Route on retry request
   - Missing result_status
   - Max attempts exceeded
   - Retry within limits

3. `TestRouteAfterRetry` - 6 tests
   - Retry counter increment
   - Exit condition (max reached)
   - Continue condition
   - State preservation
   - Modifications in retry
   - Retry logging

4. `TestRoutingEdgeCases` - 7 tests
   - Conflicting signals
   - Missing modification data
   - Empty modifications
   - Decision timeout
   - Multiple humans conflicts
   - Missing state fields
   - Invalid state transitions

5. `TestRoutingDecisionLogging` - 4 tests
   - Decision logging
   - Reason logging
   - Modification details logging
   - Failure reason logging

6. `TestRoutingPerformance` - 3 tests
   - Routing latency (< 10ms target)
   - State lookup efficiency (< 1ms target)
   - Route caching

**Running Routing Tests:**
```bash
pytest tests/unit/services/snipers/test_routing.py -v
```

---

## Test Output & Reporting

### Console Output Example
```
tests/unit/services/snipers/test_models.py::TestExampleFinding::test_valid_example_finding PASSED
tests/unit/services/snipers/test_models.py::TestExampleFinding::test_missing_required_fields PASSED
tests/unit/services/snipers/test_models.py::TestExampleFinding::test_invalid_detector_score_range_high PASSED
...

====== 127 passed in 0.42s ======
```

### Generated Reports

1. **Console Logs:** `tests/test_results.log`
   ```
   2025-11-25 14:30:15 - root - INFO - Testing valid ExampleFinding: Decode the following BASE64...
   2025-11-25 14:30:15 - root - INFO - ✓ Valid ExampleFinding structure confirmed
   2025-11-25 14:30:16 - root - ERROR - Testing missing required fields in ExampleFinding
   ```

2. **HTML Report:** `tests/report.html`
   - Visual test results with durations
   - Failure details with tracebacks
   - Test categorization by class
   - Performance metrics

3. **Coverage Report:** `tests/coverage_html/index.html`
   - Line-by-line coverage
   - Branch coverage
   - Missing lines identification

4. **JUnit XML:** `tests/junit.xml`
   - CI/CD integration
   - IDE integration
   - Failure summaries

---

## Error Detection & Logging

### Configuration Error Examples

#### Example 1: Invalid Confidence Threshold
```python
def test_negative_threshold(invalid_agent_config_negative_threshold):
    config = invalid_agent_config_negative_threshold
    # Will log:
    # ERROR - Testing negative threshold: -0.5
    # ERROR - ✗ Negative threshold should be rejected
    # Captures for debugging: config structure, constraint rules
```

#### Example 2: Missing Required Fields
```python
def test_missing_required_fields():
    data = {"prompt": "test"}  # Missing: output, detector_name, etc.
    # Will log:
    # ERROR - Testing missing required fields in ExampleFinding
    # Shows which fields are required
    # Suggests valid field structure
```

#### Example 3: PyRIT Converter Not Found
```python
def test_converter_not_found():
    converter_name = "NonExistentConverter"
    # Will log:
    # ERROR - Testing converter not found error
    # ERROR - ✗ Converter 'NonExistentConverter' not found
    # ERROR - ✓ Should log clear error message
    # Includes available converters list
```

### Accessing Logs in Tests
```python
def test_with_log_capture(capture_logs):
    # Get all ERROR level logs
    errors = capture_logs["get_logs_by_level"]("ERROR")

    # Get all error messages
    messages = capture_logs["get_error_messages"]()

    # Assert log contains message
    capture_logs["assert_log_contains"]("Expected text")

    # Access raw records
    all_logs = capture_logs["records"]
```

---

## Running Specific Test Scenarios

### Scenario 1: Validate All Models
```bash
pytest tests/unit/services/snipers/test_models.py -v --cov=services/snipers/models
```
**Output:** Line coverage for all Pydantic models

### Scenario 2: Test Parser Error Handling
```bash
pytest tests/unit/services/snipers/test_parsers.py::TestGarakReportParser -v -s
# -s shows print statements and logs in real-time
```
**Output:** Detailed parser behavior with error handling

### Scenario 3: Comprehensive PyRIT Testing
```bash
pytest tests/unit/services/snipers/test_pyrit_integration.py -v --tb=long
# --tb=long shows full tracebacks for failures
```
**Output:** Detailed PyRIT component interactions

### Scenario 4: Routing Decision Coverage
```bash
pytest tests/unit/services/snipers/test_routing.py -v -k "approve or reject or modify"
# -k filters tests by keyword
```
**Output:** All decision path tests

---

## Test Markers & Filtering

### Mark Tests
```python
@pytest.mark.edge_case
def test_large_payload():
    ...

@pytest.mark.config_error
def test_invalid_config():
    ...

@pytest.mark.pyrit
def test_converter_failure():
    ...
```

### Run Tests by Marker
```bash
# Run only edge case tests
pytest tests/unit/services/snipers/ -m edge_case -v

# Run only PyRIT tests
pytest tests/unit/services/snipers/ -m pyrit -v

# Run only config error tests
pytest tests/unit/services/snipers/ -m config_error -v

# Exclude slow tests
pytest tests/unit/services/snipers/ -m "not slow" -v
```

---

## Extending Tests

### Adding New Test Class
```python
# tests/unit/services/snipers/test_new_feature.py
import pytest
import logging

logger = logging.getLogger(__name__)

class TestNewFeature:
    """Test new feature functionality."""

    def test_valid_case(self, sample_fixture, capture_logs):
        """Test valid case."""
        logger.info("Testing valid case")
        assert sample_fixture is not None
        logger.info("✓ Valid case passed")

    def test_error_case(self, invalid_fixture, capture_logs):
        """Test error case."""
        logger.error("Testing error handling")
        assert invalid_fixture["field"] is None
        logger.error("✗ Should reject invalid data")
```

### Adding New Fixture
```python
# In conftest.py
@pytest.fixture
def sample_new_data():
    """Sample data for new feature."""
    return {
        "field1": "value1",
        "field2": 123
    }
```

### Using Fixtures
```python
def test_with_fixture(sample_new_data, capture_logs):
    """Test using fixture."""
    assert sample_new_data["field1"] == "value1"
```

---

## Troubleshooting

### Issue: Tests Not Discovered
```bash
# Ensure test files match pattern: test_*.py
# Ensure test classes match pattern: Test*
# Ensure test methods match pattern: test_*

# Check discovery
pytest tests/unit/services/snipers/ --collect-only
```

### Issue: Fixture Not Found
```bash
# Check fixture is defined in conftest.py
# Check conftest.py is in right directory
# Verify fixture name matches test parameter

# Debug fixtures
pytest tests/unit/services/snipers/ --fixtures
```

### Issue: Logs Not Showing
```bash
# Run with log output
pytest tests/unit/services/snipers/ -v --log-cli=DEBUG

# Check log file
cat tests/test_results.log
```

### Issue: Coverage Not Accurate
```bash
# Clear coverage data
rm -rf .coverage* tests/coverage_html

# Rerun with fresh coverage
pytest tests/unit/services/snipers/ --cov=services/snipers --cov-report=html
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Snipers Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - run: pip install -r requirements.txt
      - run: pytest tests/unit/services/snipers/ -v --junit-xml=junit.xml
      - uses: actions/upload-artifact@v2
        if: always()
        with:
          name: test-results
          path: junit.xml
```

---

## Performance Targets

- **Single Test:** < 100ms
- **Entire Test Suite:** < 5 seconds
- **Coverage Report Generation:** < 2 seconds
- **HTML Report Generation:** < 1 second

---

## Best Practices

1. **Use Fixtures:** Leverage `conftest.py` fixtures for setup
2. **Clear Names:** Test names should describe what they test
3. **Single Assertion:** One logical assertion per test (use multiple tests for multiple cases)
4. **Arrange-Act-Assert:**
   ```python
   def test_example():
       # Arrange - setup
       data = fixture
       # Act - do something
       result = process(data)
       # Assert - verify
       assert result is expected
   ```
5. **Test Behavior:** Test behavior, not implementation
6. **Use Markers:** Categorize tests with markers
7. **Log Clearly:** Use descriptive log messages
8. **Handle Edge Cases:** Test boundaries and invalid inputs

---

## Next Steps

1. **Implement Models:** Create actual Pydantic models in `services/snipers/models.py`
2. **Implement Parsers:** Create parser classes in `services/snipers/parsers.py`
3. **Implement PyRIT Integration:** Complete `services/snipers/tools/pyrit_*.py`
4. **Run Tests:** `pytest tests/unit/services/snipers/ -v`
5. **Check Coverage:** Open `tests/coverage_html/index.html`
6. **Fix Failures:** Update code to match test expectations
7. **Extend Tests:** Add tests for additional functionality

---

**Last Updated:** 2025-11-25
**Test Framework:** pytest 7.0+
**Python Version:** 3.9+
