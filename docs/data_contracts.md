# Data Contracts & Interface Control

Aspexa Automa uses standardized Pydantic models (Data Contracts) to ensure type safety and consistent data exchange between its microservices.

---

## 1. Protocol Standards
- **Serialization**: JSON
- **Date Format**: ISO 8601 (`YYYY-MM-DDThh:mm:ssZ`)
- **Validation**: Strict Pydantic V2 validation on all inputs/outputs.
- **Naming**: snake_case for fields, PascalCase for models.

---

## 2. Core Contracts (The IF-Series)

| Contract | Technical Name | Source | Destination | Purpose |
|----------|----------------|--------|-------------|---------|
| **IF-01** | [`ReconRequest`](../libs/contracts/recon.py) | User | Cartographer | Initiates reconnaissance on a target. |
| **IF-02** | [`ReconBlueprint`](../libs/contracts/recon.py) | Cartographer | Swarm | Delivers discovered intelligence (tools, auth, infra). |
| **IF-03** | [`ScanJobDispatch`](../libs/contracts/scanning.py) | User/Gateway | Swarm | Authorizes and configures a security scan. |
| **IF-04** | [`VulnerabilityCluster`](../libs/contracts/scanning.py) | Swarm | Snipers | Reports grouped vulnerabilities found during scanning. |
| **IF-05** | [`ExploitStreamRequest`](../services/snipers/models.py) | User/Gateway | Snipers | Initiates a multi-turn exploit attempt. |
| **IF-06** | [`ExploitJobResult`](../services/snipers/models.py) | Snipers | User/Gateway | Final outcome of an exploitation job. |

---

## 3. Contract Details

### IF-01: ReconRequest
- **Source**: [`libs/contracts/recon.py`](../libs/contracts/recon.py)
- **Key Fields**: `target` (URL, Auth), `scope` (Depth, Max Turns).
- **Usage**: Controls the intensity and boundary of the Cartographer agent.

### IF-02: ReconBlueprint
- **Source**: [`libs/contracts/recon.py`](../libs/contracts/recon.py)
- **Key Fields**: `intelligence` (System Prompt Leaks, Tools, Infrastructure, Auth Structure).
- **Usage**: Provides the "Attack Surface Map" for subsequent scanning phases.

### IF-03: ScanJobDispatch
- **Source**: [`libs/contracts/scanning.py`](../libs/contracts/scanning.py)
- **Key Fields**: `blueprint_context` (IF-02), `safety_policy`, `scan_config`.
- **Usage**: Directs Swarm on which probes to run and how aggressive the scan should be.

### IF-04: VulnerabilityCluster
- **Source**: [`libs/contracts/scanning.py`](../libs/contracts/scanning.py)
- **Key Fields**: `category`, `severity`, `evidence` (Payload, Response, Confidence).
- **Usage**: Groups similar vulnerability findings to prioritize exploitation.

### IF-05: ExploitStreamRequest
- **Source**: [`services/snipers/models.py`](../services/snipers/models.py)
- **Key Fields**: `mode` (Guided, Manual, Sweep), `target_url`, `require_plan_approval`.
- **Usage**: High-level command to start the Snipers exploitation engine.

### IF-06: ExploitJobResult
- **Source**: [`services/snipers/models.py`](../services/snipers/models.py)
- **Key Fields**: `successful_attacks`, `attack_results` (Full kill-chain transcripts).
- **Usage**: Final proof of impact and audit trail for the exploitation phase.

---

## 4. Design Principles

### Strict Base Models
All contracts inherit from `StrictBaseModel` (defined in [`libs/contracts/common.py`](../libs/contracts/common.py)), which prevents extra fields from being passed silently, ensuring that services only receive the data they expect.

### Polymorphism in Exploitation
Exploitation models in Phase 3 support different `AttackMode` enums (Guided vs. Manual), allowing the same contract to handle both automated discovery-based attacks and custom researcher-defined payloads.

### Streaming Events (SSE)
For long-running tasks, services emit `AttackEvent` or similar streaming models to provide real-time updates without waiting for the final IF-06/IF-02 result.
