# Persistence Infrastructure

**Path:** `services/snipers/infrastructure/persistence`

The **Persistence** module handles all state and data storage operations for the Sniper pipeline. Because the pipeline operates asynchronously and might be paused or distributed, state must be reliably loaded and saved to an external data store (S3/MinIO).

---

## 🏗️ Storage Architecture

```mermaid
sequenceDiagram
    participant Articulation as Articulation Phase
    participant Tracker as Effectiveness Tracker
    participant S3Adapter as S3Adapter
    participant S3 as MinIO / S3 Bucket

    %% Loading Data
    Articulation->>S3Adapter: load_campaign_data(campaign_id)
    S3Adapter->>S3: GET /campaigns/{id}/intel.json
    S3-->>S3Adapter: Raw JSON Data
    S3Adapter-->>Articulation: Structured Campaign Intelligence

    %% Saving History
    Tracker->>S3Adapter: save_effectiveness_history(records)
    S3Adapter->>S3: PUT /history/{campaign_id}/effectiveness.json
    S3-->>S3Adapter: Success
    S3Adapter-->>Tracker: Acknowledged
```

### Purpose

The `S3Adapter` abstracts away the underlying `boto3` or `minio` client logic. When agents need to write failure analysis history or when the initial articulation phase needs to load target tools/domains, it routes through this adapter rather than directly calling database APIs.

### 📁 Files

- `s3_adapter.py`: Provides read/write access to S3-compatible blob storage, primarily managing `CampaignIntelligence` and historical `EffectivenessRecord` artifacts.
