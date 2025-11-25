# Swarm Scanning Service Integration Tests

This directory contains integration tests for the Swarm scanning service (Phase 3).

## Test Script: `test_swarm_scanning.py`

Comprehensive integration test for the Swarm scanning service that tests:

### 1. Reconnaissance Result Loading
- Loads all JSON files from `recon_results/` directory
- Validates against `ReconBlueprint` schema (IF-02)
- Reports loading status

### 2. Policy Mapping
- Tests probe configuration for all three Trinity agents
- Validates database-aware probe selection
- Verifies model-specific probe mappings

### 3. Scan Job Dispatch
- Creates `ScanJobDispatch` (IF-03) from `ReconBlueprint` (IF-02)
- Validates safety policy configuration
- Tests contract serialization

### 4. Trinity Agent Initialization
- Tests agent type validation
- Prepares scan inputs for SQL, Auth, and Jailbreak agents
- (Agent execution skipped by default - requires Garak + API key)

## Usage

### Basic Run
```bash
cd /path/to/Aspexa_Automa
python -m scripts.testing.test_swarm_scanning
```

### With Environment Variables
```bash
# For full Trinity agent testing (requires Garak + Google API key):
$env:GOOGLE_API_KEY = 'your-api-key'
python -m scripts.testing.test_swarm_scanning
```

## Output

The test script produces:
- ✅ Success indicators for passed tests
- ❌ Error indicators with detailed messages
- Summary of policy mappings and dispatch creation
- Detailed blueprint analysis

### Sample Output
```
╔════════════════════════════════════════════════════════════════════════════╗
║                 SWARM SCANNING SERVICE - INTEGRATION TEST                  ║
╚════════════════════════════════════════════════════════════════════════════╝

✅ Total Blueprints Tested: 1
✅ Policy Mapping Tests: 1
✅ Scan Dispatch Tests: 1

POLICY MAPPING RESULTS
test-recon-001:
  ✅ agent_sql: 3 probes
  ✅ agent_auth: 3 probes
  ✅ agent_jailbreak: 4 probes

SCAN DISPATCH RESULTS
✅ test-recon-001:
   Job ID: scan-test-recon-001-20251123232803
```

## Data Files

Recon results are loaded from `recon_results/` directory. The test script:
- Loads all `*.json` files
- Validates against data contracts
- Reports invalid files (e.g., extra fields)
- Tests the first 2 blueprints (configurable)

### Sample Blueprint Fields
```json
{
  "audit_id": "test-recon-001",
  "timestamp": "2025-11-23T14:23:43Z",
  "intelligence": {
    "system_prompt_leak": ["..."],
    "detected_tools": [{"name": "...", "arguments": [...]}],
    "infrastructure": {
      "vector_db": "pinecone",
      "model_family": "gpt-4",
      "rate_limits": "strict"
    },
    "auth_structure": {...}
  }
}
```

## Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Policy Mapping | Database detection, probe selection | ✅ 16/16 pass |
| Aggregator | JSONL parsing, deduplication | ✅ 13/13 pass |
| Scan Dispatch | IF-03 contract validation | ✅ Integrated |
| Trinity Agents | Initialization, prompt mapping | ✅ Integrated |

## Dependencies

- `ReconBlueprint`, `ScanJobDispatch` from `libs.contracts`
- `get_probe_config` from `services.swarm.policies.mapping`
- `run_scanning_agent` from `services.swarm.agent.worker`

## Next Steps

1. **Full Trinity Agent Testing**: Uncomment Trinity agent tests when Garak is installed
2. **Vulnerability Aggregation**: Test IF-04 (VulnerabilityCluster) generation
3. **Event Bus Integration**: Test actual FastStream consumption and publication
4. **Load Testing**: Test concurrent scans with fan-out pattern

## Troubleshooting

### Issue: `ReconBlueprint` validation errors
**Cause**: Extra fields in recon results not in schema
**Fix**: Remove extra fields from recon JSON or update schema

### Issue: `'NoneType' object has no attribute 'lower'`
**Cause**: Null infrastructure fields in policy mapping
**Fix**: Updated mapping.py to handle None values

### Issue: Trinity agents fail to initialize
**Cause**: Missing Garak or GOOGLE_API_KEY
**Fix**: Install Garak and set API key in environment

## Architecture Reference

```
ReconBlueprint (IF-02)
    ↓
Policy Mapping (agent-specific probes)
    ↓
ScanJobDispatch (IF-03)
    ↓
Trinity Agents (SQL, Auth, Jailbreak)
    ↓
Garak Scanning
    ↓
Aggregator (deduplication)
    ↓
VulnerabilityCluster (IF-04)
```
