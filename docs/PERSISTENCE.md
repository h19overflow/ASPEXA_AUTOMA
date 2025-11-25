# 💾 Reconnaissance Persistence

## Overview

The Cartographer service automatically saves reconnaissance results in JSON format following the **IF-02 Reconnaissance Blueprint** standard defined in `docs/data_contracts.md`.

## Features

### Automatic Saving
- Every reconnaissance run automatically saves results to `recon_results/`
- Files are named: `{audit_id}_{timestamp}.json`
- Format: Pure JSON (UTF-8 encoded)
- Standard: IF-02 Reconnaissance Blueprint

### IF-02 Format Structure

```json
{
  "audit_id": "uuid-v4",
  "timestamp": "2025-11-23T12:00:00Z",
  "intelligence": {
    "system_prompt_leak": [
      "Extracted prompt fragments..."
    ],
    "detected_tools": [
      {
        "name": "tool_name",
        "arguments": ["param1", "param2"]
      }
    ],
    "infrastructure": {
      "vector_db": "pinecone",
      "model_family": "gpt-4",
      "rate_limits": "strict",
      "database": "PostgreSQL",
      "embeddings": "OpenAI"
    },
    "auth_structure": {
      "type": "RBAC",
      "rules": ["Authorization rules..."],
      "vulnerabilities": ["potential issues..."]
    }
  },
  "raw_observations": {
    "system_prompt": [...],
    "tools": [...],
    "authorization": [...],
    "infrastructure": [...]
  }
}
```

## Usage

### Automatic Persistence (Default)

Reconnaissance results are automatically saved when you run reconnaissance:

```python
from services.cartographer.agent.graph import run_reconnaissance

observations = await run_reconnaissance(
    audit_id="test-001",
    target_url="http://localhost:8080/chat",
    auth_headers={},
    scope={"depth": "standard", "max_turns": 10}
)
# Results automatically saved to: recon_results/test-001_20251123_115000.json
```

### Manual Saving

You can also manually save results:

```python
from services.cartographer.persistence import save_reconnaissance_result

filepath = save_reconnaissance_result(
    audit_id="manual-001",
    observations={
        "system_prompt": [...],
        "tools": [...],
        "authorization": [...],
        "infrastructure": [...]
    },
    output_dir="recon_results"  # Optional, defaults to "recon_results"
)
print(f"Saved to: {filepath}")
```

### Loading Results

Load previously saved reconnaissance results:

```python
from services.cartographer.persistence import load_reconnaissance_result

data = load_reconnaissance_result("recon_results/test-001_20251123_115000.json")
print(data["intelligence"]["detected_tools"])
```

### Listing All Results

```python
from services.cartographer.persistence.json_storage import list_reconnaissance_results

files = list_reconnaissance_results("recon_results")
for file in files:
    print(f"Found: {file}")
```

## File Naming Convention

```
{audit_id}_{timestamp}.json
```

**Examples:**
- `test-001_20251123_115000.json`
- `prod-recon-42_20251124_093045.json`
- `security-audit-001_20251125_140530.json`

## Data Transformation

The persistence layer automatically transforms raw observations into structured intelligence:

### Tool Extraction
**Input:** `"fetch_customer_balance(customer_id: str)"`  
**Output:**
```json
{
  "name": "fetch_customer_balance",
  "arguments": ["customer_id"]
}
```

### Infrastructure Detection
**Input:** Raw observations about tech stack  
**Output:**
```json
{
  "database": "PostgreSQL",
  "vector_db": "FAISS",
  "model_family": "gemini",
  "embeddings": "OpenAI"
}
```

### Authorization Parsing
**Input:** Authorization rules from observations  
**Output:**
```json
{
  "type": "RBAC",
  "rules": ["Refunds under $1000 auto-approved"],
  "vulnerabilities": []
}
```

## Storage Location

```
recon_results/
├── test-001_20251123_115000.json
├── test-002_20251123_120000.json
└── prod-audit-001_20251124_093000.json
```

**Note:** This directory is excluded from version control via `.gitignore`

## Testing

### Test Persistence Module

```bash
uv run python test_persistence.py
```

This creates a mock reconnaissance result and verifies:
- ✅ File creation
- ✅ IF-02 format compliance
- ✅ Data loading
- ✅ Structure validation

### Test with Real Reconnaissance

```bash
# Terminal 1: Start target agent
cd test_target_agent
uv run python main.py

# Terminal 2: Run reconnaissance
cd ..
uv run python test_reconnaissance.py
```

Check `recon_results/` for the saved output.

## Integration with Phase 3

The saved IF-02 files can be used to:

1. **Mock Reconnaissance Results**: During development, use saved files instead of live reconnaissance
2. **Feed to Swarm Service**: Load IF-02 data to inform vulnerability scanning
3. **Replay Attacks**: Use saved intelligence to reproduce scan conditions
4. **Audit Trail**: Keep historical record of reconnaissance findings

### Example: Loading for Swarm

```python
from services.cartographer.persistence import load_reconnaissance_result

# Load saved reconnaissance
blueprint = load_reconnaissance_result("recon_results/test-001_20251123_115000.json")

# Use in scan job (IF-03)
scan_job = {
    "job_id": "scan-001",
    "blueprint_context": blueprint,  # The IF-02 data
    "safety_policy": {
        "allowed_attack_vectors": ["injection", "jailbreak"],
        "aggressiveness": "medium"
    }
}
```

## Future Enhancements

### Planned Features
- [ ] Database persistence (PostgreSQL)
- [ ] Query interface for results
- [ ] Deduplication across audits
- [ ] Compression for large results
- [ ] Export to CSV/Excel
- [ ] Diff between reconnaissance runs

### Integration Points
- **Event Bus**: Publish IF-02 to `evt_recon_finished` topic
- **API Gateway**: Expose results via REST API
- **Dashboard**: Visualize intelligence trends
- **Reporting**: Generate PDF reports from IF-02 data

## Troubleshooting

### Permission Errors

If you get permission errors when saving:

```bash
# Ensure directory exists and is writable
mkdir recon_results
chmod 755 recon_results  # Linux/Mac
```

### Large Files

If reconnaissance produces very large files:

```python
# Limit observations in production
scope = {
    "max_turns": 5,  # Reduce turns
    "depth": "shallow"  # Use shallow depth
}
```

### JSON Parsing Errors

If tool parsing fails:
- Check that tool observations follow format: `tool_name(param1: type, param2: type)`
- Update `_parse_tool_observation()` in `json_storage.py` for custom formats

## API Reference

### `save_reconnaissance_result()`

```python
def save_reconnaissance_result(
    audit_id: str,
    observations: Dict[str, List[str]],
    output_dir: str = "recon_results"
) -> str
```

**Parameters:**
- `audit_id`: Unique identifier for the audit
- `observations`: Raw observations dictionary with categories
- `output_dir`: Output directory (default: "recon_results")

**Returns:** Path to saved file

### `load_reconnaissance_result()`

```python
def load_reconnaissance_result(filepath: str) -> Dict[str, Any]
```

**Parameters:**
- `filepath`: Path to JSON file

**Returns:** IF-02 formatted dictionary

### `list_reconnaissance_results()`

```python
def list_reconnaissance_results(output_dir: str = "recon_results") -> List[str]
```

**Parameters:**
- `output_dir`: Directory to scan

**Returns:** List of file paths

---

**Next Steps:** See `TEST_GUIDE.md` for testing the complete reconnaissance flow with persistence.
