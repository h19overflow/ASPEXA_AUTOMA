# Persistence Layer

## Overview

Aspexa uses a two-tier persistence architecture:

| Tier | Technology | Purpose |
|------|------------|---------|
| **Local** | SQLite | Campaign tracking, stage flags, S3 key mappings |
| **Cloud** | S3 | Actual scan data (recon, garak, exploit results) |

This design provides fast local queries for campaign management while leveraging S3 for reliable scan data storage.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL (SQLite)                           │
│  ~/.aspexa/campaigns.db                                     │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ campaigns table                                       │  │
│  │  - campaign_id (PK)                                   │  │
│  │  - name, target_url, status                           │  │
│  │  - recon_complete, garak_complete, exploit_complete   │  │
│  │  - recon_scan_id, garak_scan_id, exploit_scan_id      │  │
│  │  - tags, description                                  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ scan_id → S3 key
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       S3 BUCKET                             │
│                                                             │
│  scans/                                                     │
│  ├── recon/                                                 │
│  │   └── {scan_id}.json    ← ReconResult                   │
│  ├── garak/                                                 │
│  │   └── {scan_id}.json    ← GarakResult                   │
│  └── exploit/                                               │
│      └── {scan_id}.json    ← ExploitResult                 │
│                                                             │
│  campaigns/                 (legacy audit artifacts)        │
│  └── {audit_id}/{phase}/{filename}.json                    │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
libs/persistence/
├── __init__.py              # Main exports (S3 + SQLite)
├── contracts.py             # Shared exceptions
├── s3.py                    # S3PersistenceAdapter
├── scan_models.py           # Pydantic models for scan results
└── sqlite/                  # Local campaign tracking
    ├── __init__.py          # SQLite exports
    ├── connection.py        # Connection management
    ├── models.py            # Campaign, Stage, ScanMapping
    └── repository.py        # CampaignRepository CRUD
```

---

## Quick Start

### 1. Create a Campaign

```python
from libs.persistence.sqlite import CampaignRepository

repo = CampaignRepository()

# Create campaign
campaign = repo.create_campaign(
    name="TechShop Agent Audit",
    target_url="http://localhost:8080/chat",
    description="Security audit of customer support chatbot",
    tags=["production", "high-priority"]
)

print(campaign.campaign_id)  # UUID
print(campaign.status)       # CampaignStatus.CREATED
```

### 2. Run a Scan and Link to Campaign

```python
from libs.persistence import save_scan, ScanType
from libs.persistence.sqlite import Stage
import json

# Load your scan data
with open("recon_results/my_scan.json") as f:
    recon_data = json.load(f)

# Save to S3
scan_id = "recon-20251125-001"
await save_scan(ScanType.RECON, scan_id, recon_data)

# Link to campaign and set stage flag
repo.set_stage_complete(campaign.campaign_id, Stage.RECON, scan_id)
```

### 3. Check Campaign Progress

```python
campaign = repo.get(campaign.campaign_id)

print(campaign.recon_complete)   # True
print(campaign.garak_complete)   # False
print(campaign.exploit_complete) # False
print(campaign.progress_summary) # "1/3 complete: Recon"
```

### 4. Retrieve Scan Data

```python
from libs.persistence import load_scan, ScanType

# Get S3 keys for completed stages
keys = repo.get_s3_keys(campaign.campaign_id)
# {'recon': 'scans/recon/recon-20251125-001.json'}

# Load typed scan result
recon_result = await load_scan(ScanType.RECON, campaign.recon_scan_id)
print(recon_result.intelligence.detected_tools)
```

---

## Campaign Lifecycle

### Stages

| Stage | Flag | S3 Key Pattern | Description |
|-------|------|----------------|-------------|
| `Stage.RECON` | `recon_complete` | `scans/recon/{scan_id}.json` | Reconnaissance results |
| `Stage.GARAK` | `garak_complete` | `scans/garak/{scan_id}.json` | Jailbreak scan results |
| `Stage.EXPLOIT` | `exploit_complete` | `scans/exploit/{scan_id}.json` | Exploit execution results |

### Status Transitions

```
CREATED → IN_PROGRESS → COMPLETE
    │                       │
    └───────→ FAILED ←──────┘
```

- **CREATED**: Campaign initialized, no stages complete
- **IN_PROGRESS**: At least one stage complete (auto-computed)
- **COMPLETE**: All three stages complete (auto-computed)
- **FAILED**: Manually set when campaign fails

### Stage Management

```python
# Mark stage in progress (status → IN_PROGRESS)
repo.set_stage_in_progress(campaign_id, Stage.GARAK)

# Mark stage complete and link scan
repo.set_stage_complete(campaign_id, Stage.GARAK, "garak-scan-001")
# Sets: garak_complete=True, garak_scan_id="garak-scan-001"
# Auto-computes status based on all flags

# Mark campaign as failed
repo.set_failed(campaign_id, reason="Target unreachable")
```

---

## API Reference

### CampaignRepository

#### Create Operations

```python
repo.create_campaign(
    name: str,
    target_url: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    campaign_id: Optional[str] = None,  # Auto-generated if not provided
) -> Campaign
```

#### Read Operations

```python
repo.get(campaign_id: str) -> Optional[Campaign]
repo.get_by_target(target_url: str) -> List[Campaign]
repo.list_all(
    status: Optional[CampaignStatus] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Campaign]
repo.search(query: str, limit: int = 50) -> List[Campaign]
```

#### Stage Management

```python
repo.set_stage_complete(campaign_id: str, stage: Stage, scan_id: str) -> Campaign
repo.set_stage_in_progress(campaign_id: str, stage: Stage) -> Campaign
repo.set_failed(campaign_id: str, reason: Optional[str] = None) -> Campaign
```

#### Update Operations

```python
repo.update_name(campaign_id: str, name: str) -> Campaign
repo.add_tags(campaign_id: str, tags: List[str]) -> Campaign
```

#### Delete Operations

```python
repo.delete(campaign_id: str) -> bool  # Only removes local index, not S3 data
```

#### S3 Mapping

```python
repo.get_s3_keys(campaign_id: str) -> Dict[str, str]
# Returns: {'recon': 'scans/recon/scan-001.json', ...} for completed stages
```

---

### S3 Scan Functions

#### Save Scan

```python
from libs.persistence import save_scan, ScanType

summary = await save_scan(
    scan_type: ScanType,       # RECON, GARAK, or EXPLOIT
    scan_id: str,              # Unique identifier
    data: Union[Model, Dict],  # Pydantic model or dict
) -> ScanResultSummary
```

#### Load Scan

```python
from libs.persistence import load_scan

# With validation (returns typed model)
result = await load_scan(ScanType.RECON, scan_id, validate=True)
# result is ReconResult with full type hints

# Without validation (returns dict)
data = await load_scan(ScanType.RECON, scan_id, validate=False)
```

#### List Scans

```python
from libs.persistence import list_scans

# All scans
scans = await list_scans()

# Filter by type
recon_scans = await list_scans(scan_type=ScanType.RECON)

# Filter by audit ID
scans = await list_scans(audit_id_filter="exploit-2025")
```

#### Check/Delete

```python
from libs.persistence import scan_exists, delete_scan

exists = await scan_exists(ScanType.RECON, scan_id)
deleted = await delete_scan(ScanType.RECON, scan_id)
```

---

## Scan Data Models

### ReconResult

```python
class ReconResult:
    audit_id: str
    timestamp: str
    intelligence: ReconIntelligence
        - system_prompt_leak: List[str]
        - detected_tools: List[DetectedTool]
        - infrastructure: Dict[str, Any]
        - auth_structure: Optional[AuthStructure]
    raw_observations: Optional[RawObservations]
    structured_deductions: Optional[StructuredDeductions]
```

### GarakResult

```python
class GarakResult:
    summary: GarakSummary
        - total_results: int
        - pass_count: int
        - fail_count: int
        - probes_tested: List[str]
        - failing_probes: List[str]
    vulnerability_clusters: VulnerabilityClusters
    vulnerable_probes: VulnerableProbes
    vulnerability_findings: VulnerabilityFindings
    formatted_report: Optional[str]
    metadata: GarakMetadata
```

### ExploitResult

```python
class ExploitResult:
    audit_id: str
    target_url: str
    timestamp: str
    probes_attacked: List[ProbeAttack]
        - probe_name: str
        - pattern_analysis: PatternAnalysis
        - attempts: List[ExploitAttempt]
        - success_count: int
        - overall_success: bool
    total_attacks: int
    successful_attacks: int
    failed_attacks: int
    execution_time_seconds: float
```

---

## Configuration

### SQLite Database Location

Default: `~/.aspexa/campaigns.db`

Override:
```python
from pathlib import Path
from libs.persistence.sqlite import CampaignRepository

repo = CampaignRepository(db_path=Path("/custom/path/campaigns.db"))
```

### S3 Configuration

Set via environment variables:
```bash
S3_BUCKET_NAME=my-audit-bucket
AWS_REGION=ap-southeast-2
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

Or inject custom adapter:
```python
from libs.persistence import save_scan, S3PersistenceAdapter

adapter = S3PersistenceAdapter(
    bucket_name="my-bucket",
    region="us-east-1",
)
await save_scan(ScanType.RECON, "scan-001", data, adapter=adapter)
```

---

## Complete Workflow Example

```python
import asyncio
import json
from libs.persistence import save_scan, load_scan, ScanType
from libs.persistence.sqlite import CampaignRepository, Stage

async def main():
    repo = CampaignRepository()

    # 1. Create campaign
    campaign = repo.create_campaign(
        name="Q4 Security Audit",
        target_url="https://api.example.com/chat",
        tags=["production", "quarterly"]
    )
    print(f"Created campaign: {campaign.campaign_id}")

    # 2. Run recon and save results
    with open("recon_results/example.json") as f:
        recon_data = json.load(f)

    await save_scan(ScanType.RECON, "recon-001", recon_data)
    repo.set_stage_complete(campaign.campaign_id, Stage.RECON, "recon-001")
    print(f"Recon complete: {campaign.progress_summary}")

    # 3. Run garak scan and save results
    with open("garak_runs/example.json") as f:
        garak_data = json.load(f)

    await save_scan(ScanType.GARAK, "garak-001", garak_data)
    repo.set_stage_complete(campaign.campaign_id, Stage.GARAK, "garak-001")

    # 4. Run exploit and save results
    with open("exploit_results/example.json") as f:
        exploit_data = json.load(f)

    await save_scan(ScanType.EXPLOIT, "exploit-001", exploit_data)
    repo.set_stage_complete(campaign.campaign_id, Stage.EXPLOIT, "exploit-001")

    # 5. Campaign is now complete
    campaign = repo.get(campaign.campaign_id)
    print(f"Status: {campaign.status}")        # COMPLETE
    print(f"Progress: {campaign.progress_summary}")  # 3/3 complete

    # 6. Retrieve all S3 keys
    keys = repo.get_s3_keys(campaign.campaign_id)
    print(f"S3 Keys: {keys}")

    # 7. Load typed results
    recon = await load_scan(ScanType.RECON, campaign.recon_scan_id)
    print(f"Detected tools: {len(recon.intelligence.detected_tools)}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Error Handling

```python
from libs.persistence import (
    PersistenceError,
    ArtifactNotFoundError,
    ArtifactUploadError,
    ArtifactDownloadError,
)

try:
    result = await load_scan(ScanType.RECON, "nonexistent-scan")
except ArtifactNotFoundError:
    print("Scan not found in S3")

try:
    repo.get("nonexistent-campaign")  # Returns None, doesn't raise
    repo.set_stage_complete("bad-id", Stage.RECON, "scan")  # Raises ValueError
except ValueError as e:
    print(f"Campaign error: {e}")
```

---

## See Also

- **docs/main.md** - System overview
- **docs/data_contracts.md** - IF-01 through IF-06 contracts
- **services/cartographer/README.md** - Recon output format
- **services/swarm/README.md** - Garak scan output format
- **services/snipers/README.md** - Exploit result format
