# API Architecture & Service Communication

Aspexa Automa follows a REST-based microservices architecture. Services communicate primarily through the central API Gateway using standardized data contracts.

---

## 1. Core Service Endpoints

The system is organized around four primary functional domains, exposed through the [API Gateway](../services/api_gateway/main.py).

### A. Reconnaissance (Cartographer)
- **Endpoint**: `POST /api/recon`
- **Input**: `ReconRequest` (IF-01)
- **Output**: `ReconBlueprint` (IF-02)
- **Description**: Triggers an autonomous agent to map the target's attack surface. Supports Server-Sent Events (SSE) for real-time progress.

### B. Vulnerability Scanning (Swarm)
- **Endpoint**: `POST /api/scan`
- **Input**: `ScanJobDispatch` (IF-03)
- **Output**: `VulnerabilityCluster[]` (IF-04)
- **Description**: Orchestrates the Trinity agents to execute specialized security probes based on reconnaissance intelligence.

### C. Exploitation (Snipers)
- **Endpoint**: `POST /api/snipers/attack`
- **Input**: `ExploitInput` (IF-05)
- **Output**: `ExploitResult` (IF-06)
- **Description**: Executes a multi-stage attack plan with human-in-the-loop (HITL) checkpoints.

### D. Persistence & Campaigns
- **Endpoints**: 
  - `GET /api/campaigns`: List all security audits.
  - `GET /api/scans/{scan_id}`: Retrieve detailed scan results from storage.
- **Description**: Provides access to metadata stored in PostgreSQL and structured results in S3.

---

## 2. Data Flow (The Contract Pipeline)

Aspexa Automa uses a "Contract Pipeline" where the output of one phase becomes the input for the next.

| Step | Producer | Contract | Consumer | Purpose |
|------|----------|----------|----------|---------|
| **1** | User | **IF-01** | Cartographer | Start reconnaissance |
| **2** | Cartographer | **IF-02** | Swarm | Blueprint for scanning |
| **3** | User | **IF-03** | Swarm | Configure and start scan |
| **4** | Swarm | **IF-04** | Snipers | Vulnerabilities to exploit |
| **5** | User | **IF-05** | Snipers | Approved exploit plan |
| **6** | Snipers | **IF-06** | User | Proof of exploitation |

---

## 3. Communication Patterns

### Synchronous Requests
Most administrative tasks (listing campaigns, checking health) are handled as standard synchronous Request-Response.

### Streaming Results (SSE)
For long-running tasks like reconnaissance, the Gateway uses **Server-Sent Events (SSE)**. This allows the frontend to receive real-time log updates and partial findings while the agent is still running.

### Polling / Persistence
Results are persisted to long-term storage (PostgreSQL and S3) upon completion. Users can retrieve these results later using the `scan_id`.

---

## 4. Security & Authentication

- **Provider**: Clerk
- **Mechanism**: JWT-based session tokens.
- **Access Control**: Endpoints are protected by the `require_friend` dependency, ensuring only authorized researchers can trigger scans or view results.