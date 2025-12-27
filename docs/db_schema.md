# Database Schema & Persistence

This document outlines the data model and persistence strategy for Aspexa Automa, detailing how structured agent outputs are stored and tracked.

---

## 1. Persistence Strategy

Aspexa Automa uses a dual-layer persistence strategy:
- **Metadata Layer (PostgreSQL)**: Tracks campaigns, audits, and scan metadata for fast querying and reporting.
- **Structured Result Layer (S3 / Local)**: Stores the large, detailed JSON outputs from each phase (Blueprints, Vulnerability Reports, Exploit Records).

---

## 2. Core Data Models (Pydantic)

The system uses standardized Pydantic models defined in [`libs/persistence/scan_models.py`](../libs/persistence/scan_models.py) to ensure type safety across all storage operations.

| Phase | Model Name | Description | Link |
|-------|------------|-------------|------|
| **Phase 1** | `ReconResult` | Structured intelligence from reconnaissance | [View Model](../libs/persistence/scan_models.py#L65) |
| **Phase 2** | `GarakResult` | Clustered vulnerabilities and probe results | [View Model](../libs/persistence/scan_models.py#L143) |
| **Phase 3** | `ExploitResult` | Full record of exploitation attempts and success | [View Model](../libs/persistence/scan_models.py#L182) |
| **Adaptive** | `CheckpointResult` | State for pause/resume functionality | [View Model](../libs/persistence/scan_models.py#L236) |

---

## 3. Database Schema (PostgreSQL)

### A. `campaigns`
Tracks the high-level security audit session.
- `id` (UUID): Primary key.
- `name` (String): Human-readable name.
- `target_url` (String): The base URL of the AI system.
- `status` (Enum): `active`, `completed`, `failed`.
- `created_at` (Timestamp).

### B. `scans`
Individual execution records for each service.
- `id` (UUID): Primary key.
- `campaign_id` (UUID): Foreign key to `campaigns`.
- `scan_type` (Enum): `recon`, `garak`, `exploit`.
- `s3_key` (String): Path to the full JSON result in the structured result layer.
- `summary` (JSONB): High-level stats extracted from the result for listing.

### C. `vulnerabilities`
Flattened view of findings for quick analysis.
- `id` (UUID).
- `scan_id` (UUID): Foreign key to `scans`.
- `category` (String): e.g., `injection.sql`, `jailbreak`.
- `severity` (Enum): `critical`, `high`, `medium`, `low`.
- `confidence` (Float): 0.0 to 1.0 score from detectors.

---

## 4. Audit Trail & Integrity

For enterprise security, every significant action is recorded:
- **Digital Signatures**: Exploitation plans (IF-05) are hashed before human approval. If the hash changes before execution, the system aborts.
- **Correlation IDs**: All logs and results are linked via a unique `audit_id` (also referred to as `campaign_id`).

---

## 5. Summary

By separating metadata (SQL) from structured artifacts (JSON), Aspexa Automa achieves:
1. **Searchability**: Fast lookups of past campaigns and vulnerability trends.
2. **Flexibility**: The ability to change detailed schema (e.g., adding new Garak probes) without complex SQL migrations.
3. **Auditability**: A clear, tamper-evident trail of what was scanned, what was found, and how it was exploited.