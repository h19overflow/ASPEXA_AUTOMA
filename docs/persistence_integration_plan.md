# Persistence Integration Plan

## Objective

Integrate the new two-tier persistence layer (SQLite + S3) across all three services:
- **Cartographer** (Phase 1: Reconnaissance)
- **Swarm** (Phase 2: Scanning)
- **Snipers** (Phase 3: Exploitation)

Each service will save its results to S3 and update campaign stage flags in SQLite.

---

## Current State Analysis

### Existing Persistence

| Service | Current Storage | Location |
|---------|-----------------|----------|
| Cartographer | Local JSON files | `services/cartographer/persistence/json_storage.py` |
| Swarm | None (publishes to event bus only) | - |
| Snipers | None (in-memory state) | - |

### New Persistence Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| `libs/persistence/sqlite/` | SQLite | Campaign tracking, stage flags |
| `libs/persistence/s3.py` | S3 | Scan data storage |

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Campaign Flow                                  │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │  API Gateway     │  Creates campaign via CampaignRepository
    │  or CLI          │  campaign_id = repo.create_campaign(...)
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐     ┌─────────────────────────────────────────┐
    │  Cartographer    │────▶│ 1. Run reconnaissance                   │
    │  (Phase 1)       │     │ 2. save_scan(RECON, scan_id, data)     │
    │                  │     │ 3. repo.set_stage_complete(RECON)       │
    └────────┬─────────┘     └─────────────────────────────────────────┘
             │
             ▼
    ┌──────────────────┐     ┌─────────────────────────────────────────┐
    │  Swarm           │────▶│ 1. Load recon from S3                   │
    │  (Phase 2)       │     │ 2. Run garak scanning                   │
    │                  │     │ 3. save_scan(GARAK, scan_id, data)      │
    └────────┬─────────┘     │ 4. repo.set_stage_complete(GARAK)       │
             │               └─────────────────────────────────────────┘
             ▼
    ┌──────────────────┐     ┌─────────────────────────────────────────┐
    │  Snipers         │────▶│ 1. Load recon + garak from S3           │
    │  (Phase 3)       │     │ 2. Run exploitation                     │
    │                  │     │ 3. save_scan(EXPLOIT, scan_id, data)    │
    └──────────────────┘     │ 4. repo.set_stage_complete(EXPLOIT)     │
                             │ 5. Campaign status → COMPLETE            │
                             └─────────────────────────────────────────┘
```

---

## Implementation Tasks

### Phase 1: Cartographer Integration

**File**: `services/cartographer/persistence/s3_adapter.py` (new)

**Tasks**:
1. Create S3 adapter wrapper for Cartographer
2. Modify `consumer.py` to save to S3 after reconnaissance
3. Update campaign stage flag after successful save
4. Keep local JSON storage as fallback/debug option

**Code Changes**:

```python
# services/cartographer/persistence/s3_adapter.py
from libs.persistence import save_scan, ScanType
from libs.persistence.sqlite import CampaignRepository, Stage

async def persist_recon_result(
    campaign_id: str,
    scan_id: str,
    blueprint: dict,
) -> None:
    """Save recon result to S3 and update campaign."""
    # Save to S3
    await save_scan(ScanType.RECON, scan_id, blueprint)

    # Update campaign stage flag
    repo = CampaignRepository()
    repo.set_stage_complete(campaign_id, Stage.RECON, scan_id)
```

**Integration Point** in `consumer.py`:
```python
# After building blueprint, before publishing to event bus
from services.cartographer.persistence.s3_adapter import persist_recon_result

# In handle_recon_request():
await persist_recon_result(
    campaign_id=request.audit_id,  # audit_id maps to campaign_id
    scan_id=f"recon-{request.audit_id}",
    blueprint=blueprint.model_dump(),
)
```

---

### Phase 2: Swarm Integration

**File**: `services/swarm/persistence/s3_adapter.py` (new)

**Tasks**:
1. Create S3 adapter wrapper for Swarm
2. Load recon data from S3 before scanning
3. Save garak results to S3 after scanning
4. Update campaign stage flag

**Code Changes**:

```python
# services/swarm/persistence/s3_adapter.py
from libs.persistence import save_scan, load_scan, ScanType
from libs.persistence.sqlite import CampaignRepository, Stage

async def load_recon_for_campaign(campaign_id: str) -> dict:
    """Load recon result from S3 for a campaign."""
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    if not campaign or not campaign.recon_scan_id:
        raise ValueError(f"No recon data for campaign {campaign_id}")

    return await load_scan(ScanType.RECON, campaign.recon_scan_id, validate=False)

async def persist_garak_result(
    campaign_id: str,
    scan_id: str,
    garak_report: dict,
) -> None:
    """Save garak result to S3 and update campaign."""
    await save_scan(ScanType.GARAK, scan_id, garak_report)

    repo = CampaignRepository()
    repo.set_stage_complete(campaign_id, Stage.GARAK, scan_id)
```

**Integration Point** in `services/swarm/core/consumer.py`:
```python
# Before running scan
from services.swarm.persistence.s3_adapter import load_recon_for_campaign, persist_garak_result

# In handle_scan_request():
# Load recon intelligence
recon_data = await load_recon_for_campaign(request.audit_id)

# After scan completes
await persist_garak_result(
    campaign_id=request.audit_id,
    scan_id=f"garak-{request.audit_id}",
    garak_report=report,
)
```

---

### Phase 3: Snipers Integration

**File**: `services/snipers/persistence/s3_adapter.py` (new)

**Tasks**:
1. Create S3 adapter wrapper for Snipers
2. Load recon + garak data from S3 before exploitation
3. Save exploit results to S3 after execution
4. Update campaign stage flag (marks campaign COMPLETE)

**Code Changes**:

```python
# services/snipers/persistence/s3_adapter.py
from libs.persistence import save_scan, load_scan, ScanType
from libs.persistence.sqlite import CampaignRepository, Stage

async def load_campaign_intel(campaign_id: str) -> dict:
    """Load all intelligence for a campaign."""
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    intel = {}

    if campaign.recon_scan_id:
        intel["recon"] = await load_scan(
            ScanType.RECON, campaign.recon_scan_id, validate=False
        )

    if campaign.garak_scan_id:
        intel["garak"] = await load_scan(
            ScanType.GARAK, campaign.garak_scan_id, validate=False
        )

    return intel

async def persist_exploit_result(
    campaign_id: str,
    scan_id: str,
    exploit_result: dict,
) -> None:
    """Save exploit result to S3 and complete campaign."""
    await save_scan(ScanType.EXPLOIT, scan_id, exploit_result)

    repo = CampaignRepository()
    repo.set_stage_complete(campaign_id, Stage.EXPLOIT, scan_id)
    # Campaign status auto-computes to COMPLETE when all stages done
```

**Integration Point** in `services/snipers/agent/core.py`:
```python
# In ExploitAgent.execute():
from services.snipers.persistence.s3_adapter import persist_exploit_result

# After workflow completes successfully
if result.get("success"):
    await persist_exploit_result(
        campaign_id=initial_state["campaign_id"],
        scan_id=f"exploit-{initial_state['campaign_id']}",
        exploit_result=result,
    )
```

---

## Event Bus Updates

### Current Flow (Events Only)
```
Cartographer → evt_recon_finished → Swarm → evt_scan_complete → Snipers
```

### New Flow (Events + Persistence)
```
Cartographer:
  1. Run recon
  2. Save to S3 + update SQLite
  3. Publish evt_recon_finished (includes scan_id reference)

Swarm:
  1. Receive evt_recon_finished
  2. Load recon from S3 using scan_id
  3. Run scan
  4. Save to S3 + update SQLite
  5. Publish evt_scan_complete (includes scan_id reference)

Snipers:
  1. Receive evt_scan_complete
  2. Load recon + garak from S3
  3. Run exploitation
  4. Save to S3 + update SQLite
  5. Publish evt_exploit_complete
```

### Event Payload Changes

Update event payloads to include persistence references:

```python
# evt_recon_finished payload
{
    "audit_id": "campaign-001",
    "recon_scan_id": "recon-campaign-001",  # NEW
    "blueprint": { ... }  # Can be trimmed since data is in S3
}

# evt_scan_complete payload
{
    "audit_id": "campaign-001",
    "garak_scan_id": "garak-campaign-001",  # NEW
    "summary": { ... }  # Trimmed summary, full data in S3
}
```

---

## Migration Path

### Step 1: Add Persistence Layer (Done)
- [x] Create `libs/persistence/sqlite/` module
- [x] Create `libs/persistence/scan_models.py`
- [x] Update `libs/persistence/s3.py` with scan methods
- [x] Document in `docs/persistence.md`

### Step 2: Cartographer Integration
- [ ] Create `services/cartographer/persistence/s3_adapter.py`
- [ ] Modify `consumer.py` to call persistence
- [ ] Test with existing integration tests
- [ ] Keep `json_storage.py` as fallback

### Step 3: Swarm Integration
- [ ] Create `services/swarm/persistence/s3_adapter.py`
- [ ] Modify `core/consumer.py` to load recon from S3
- [ ] Modify to save garak results to S3
- [ ] Test scan pipeline

### Step 4: Snipers Integration
- [ ] Create `services/snipers/persistence/s3_adapter.py`
- [ ] Modify `agent/core.py` to load intelligence
- [ ] Save exploit results to S3
- [ ] Test full pipeline

### Step 5: API Gateway Integration
- [ ] Add campaign management endpoints
- [ ] Add campaign status/progress endpoints
- [ ] Add scan result retrieval endpoints

---

## Configuration

### Environment Variables

```bash
# S3 Configuration
S3_BUCKET_NAME=aspexa-audit-lake
AWS_REGION=ap-southeast-2
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# SQLite (optional, defaults to ~/.aspexa/campaigns.db)
ASPEXA_DB_PATH=/path/to/campaigns.db

# Feature Flags
PERSISTENCE_ENABLED=true
LOCAL_FALLBACK_ENABLED=true  # Save to local JSON if S3 fails
```

### Service Configuration

Each service should have a config option to enable/disable persistence:

```python
# services/cartographer/config.py
class CartographerConfig:
    persistence_enabled: bool = True
    local_fallback: bool = True
    s3_bucket: str = "aspexa-audit-lake"
```

---

## Error Handling

### S3 Failures

```python
async def persist_with_fallback(scan_type, scan_id, data, local_path):
    """Persist to S3 with local fallback."""
    try:
        await save_scan(scan_type, scan_id, data)
    except ArtifactUploadError as e:
        logger.warning(f"S3 upload failed, using local fallback: {e}")
        save_to_local_json(data, local_path)
        raise  # Re-raise to notify caller
```

### Campaign Not Found

```python
def get_campaign_or_create(campaign_id: str, target_url: str) -> Campaign:
    """Get existing campaign or create new one."""
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    if not campaign:
        campaign = repo.create_campaign(
            name=f"Auto-created: {campaign_id}",
            target_url=target_url,
            campaign_id=campaign_id,
        )

    return campaign
```

---

## Testing Strategy

### Unit Tests

```python
# tests/persistence/test_service_integration.py

async def test_cartographer_saves_to_s3(mock_s3, mock_sqlite):
    """Test Cartographer saves recon to S3 and updates campaign."""
    # Arrange
    campaign = mock_sqlite.create_campaign("Test", "http://target.com")

    # Act
    await persist_recon_result(campaign.campaign_id, "scan-001", recon_data)

    # Assert
    assert mock_s3.object_exists("scans/recon/scan-001.json")
    updated = mock_sqlite.get(campaign.campaign_id)
    assert updated.recon_complete is True
    assert updated.recon_scan_id == "scan-001"
```

### Integration Tests

```python
# tests/integration/test_full_pipeline.py

async def test_full_pipeline_with_persistence():
    """Test complete pipeline saves all stages."""
    repo = CampaignRepository(db_path=Path(":memory:"))

    # Create campaign
    campaign = repo.create_campaign("E2E Test", "http://target.com")

    # Run Cartographer
    await run_cartographer(campaign.campaign_id)
    assert repo.get(campaign.campaign_id).recon_complete

    # Run Swarm
    await run_swarm(campaign.campaign_id)
    assert repo.get(campaign.campaign_id).garak_complete

    # Run Snipers
    await run_snipers(campaign.campaign_id)
    campaign = repo.get(campaign.campaign_id)
    assert campaign.exploit_complete
    assert campaign.status == CampaignStatus.COMPLETE
```

---

## Rollout Checklist

- [ ] Deploy persistence layer (`libs/persistence/`)
- [ ] Deploy Cartographer with persistence
- [ ] Verify recon saves to S3
- [ ] Deploy Swarm with persistence
- [ ] Verify Swarm loads recon + saves garak
- [ ] Deploy Snipers with persistence
- [ ] Verify full pipeline
- [ ] Enable monitoring/alerting for S3 failures
- [ ] Document API changes

---

## Timeline Estimate

| Task | Complexity |
|------|------------|
| Cartographer Integration | Low |
| Swarm Integration | Medium |
| Snipers Integration | Medium |
| API Gateway Endpoints | Low |
| Testing | Medium |
| Documentation | Low |

---

## Success Criteria

1. **Campaigns persist across restarts** - SQLite tracks all campaign state
2. **Scan data retrievable** - All scan results accessible via S3
3. **Stage flags accurate** - Each stage completion updates flags correctly
4. **Campaign status auto-computed** - Status reflects actual progress
5. **Search works** - Can find campaigns by name, target, tags
6. **Graceful degradation** - Local fallback if S3 unavailable
