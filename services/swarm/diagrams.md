# Swarm Service — Architecture Diagrams

## Diagram 1: Component Architecture

This diagram shows the main components of the Swarm service, their dependencies, and external integrations.

```mermaid
graph TD
    Client["Client — HTTP/SSE"]

    subgraph EntryPoint["Entrypoint"]
        EP["execute_scan_streaming"]
        CC["cancel / pause / resume"]
    end

    subgraph Phases["Sequential Phases"]
        LR["load_recon"]
        PA["plan_agent"]
        EA["execute_agent"]
        PR["persist_results"]
    end

    subgraph Core["Core"]
        SH["ScanState / ScanPlan / ScanConfig"]
        CF["config — get_agent_probe_pool"]
    end

    subgraph GarakScanner["Garak Scanner"]
        SC["GarakScanner — scan_with_streaming"]
        GEN["HTTP / WebSocket Generators"]
        DET["Detectors — load_detector"]
    end

    subgraph Observability["Swarm Observability"]
        EV["create_event"]
        CM["CancellationManager"]
    end

    subgraph Persistence["Persistence"]
        S3["S3 Adapter"]
    end

    External_S3["S3 Bucket"]
    External_LLM["Target LLM Endpoint"]
    Libs_Contracts["libs.contracts"]

    Client -->|ScanJobDispatch| EP
    EP -->|emit events| EV
    EP --> CC

    EP -->|Phase 1| LR
    EP -->|Phase 2| PA
    EP -->|Phase 3| EA
    EP -->|Phase 4| PR

    LR -.->|reads| SH
    PA -.->|reads/writes| SH
    PA -->|probe selection| CF

    EA -.->|reads| SH
    EA -->|scan_with_streaming| SC
    SC -->|uses| GEN
    SC -->|uses| DET
    EA -->|checkpoint| CM

    PR -.->|reads| SH
    PR -->|persist_garak_result| S3

    GEN -->|HTTP requests| External_LLM
    S3 -->|upload| External_S3
    LR -->|validate blueprint| Libs_Contracts
    CM -.->|cancel/pause state| EP

    style Client fill:#50E3C2
    style EntryPoint fill:#4A90E2
    style Phases fill:#4A90E2
    style Core fill:#F5A623
    style GarakScanner fill:#F5A623
    style Observability fill:#BD10E0
    style Persistence fill:#7ED321
    style External_S3 fill:#7ED321
    style External_LLM fill:#F5A623
    style Libs_Contracts fill:#9B9B9B
```

**Key Observations:**

- **Entrypoint** (`entrypoint.py`) orchestrates the four phases sequentially and manages the event queue
- **Phases** are independent units that read/write to `ScanState` and emit events via the `emit()` callback
- **GarakScanner** is the execution engine: runs generators (HTTP/WebSocket) and evaluates results with detectors
- **CancellationManager** is wired throughout for cooperative pause/resume/cancel checkpoints
- **Persistence** always runs last, saving successful results to S3

---

## Diagram 2: Sequence — Step 1: Scan Initialisation

Client dispatches the job. Entrypoint builds `ScanState`, registers `CancellationManager`, then hands off to `load_recon`.

```mermaid
sequenceDiagram
    participant Client
    participant Entrypoint
    participant CancelMgr as CancellationManager
    participant LoadRecon as load_recon
    participant Libs as libs.contracts

    Client->>Entrypoint: execute_scan_streaming(ScanJobDispatch)
    Note over Entrypoint: Build ScanState{audit_id, target_url,<br/>agent_types, scan_config}
    Entrypoint->>CancelMgr: register(audit_id)

    Entrypoint->>LoadRecon: Phase 1 — load_recon(state, emit)

    LoadRecon->>Client: emit(SCAN_STARTED)
    Note over Client: SSE: SCAN_STARTED<br/>{audit_id, target_url, agent_types}

    LoadRecon->>CancelMgr: checkpoint()
    CancelMgr-->>LoadRecon: continue

    LoadRecon->>Libs: validate ReconBlueprint
    Libs-->>LoadRecon: valid

    LoadRecon->>Entrypoint: return (state.recon_context set)
```

---

## Diagram 3: Sequence — Step 2: Probe Planning

`plan_agent` selects probes deterministically from `DEFAULT_PROBES` and stores the `ScanPlan` on state.

```mermaid
sequenceDiagram
    participant Entrypoint
    participant CancelMgr as CancellationManager
    participant PlanAgent as plan_agent
    participant Config as core/config
    participant Client

    Entrypoint->>PlanAgent: Phase 2 — plan_agent(state, emit)
    PlanAgent->>CancelMgr: checkpoint()
    CancelMgr-->>PlanAgent: continue

    PlanAgent->>Client: emit(PLAN_START)
    Note over Client: SSE: PLAN_START<br/>{agent_type, approach}

    PlanAgent->>Config: get_agent_probe_pool(agent_type, approach)
    Config-->>PlanAgent: probe_pool (full list from DEFAULT_PROBES)

    Note over PlanAgent: selected = probe_pool[:max_probes]<br/>(default cap: 3)

    PlanAgent->>Client: emit(PLAN_COMPLETE)
    Note over Client: SSE: PLAN_COMPLETE<br/>{probes: ["dan","encoding","promptinj"],<br/>probe_count: 3}

    PlanAgent->>Entrypoint: return (state.current_plan = ScanPlan)
```

---

## Diagram 4: Sequence — Step 3: Probe Execution

`execute_agent` drives `GarakScanner` through each probe. One iteration of the inner prompt loop is shown.

```mermaid
sequenceDiagram
    participant Entrypoint
    participant CancelMgr as CancellationManager
    participant ExecAgent as execute_agent
    participant Scanner as GarakScanner
    participant Generator as HTTP/WS Generator
    participant Detector as Detectors
    participant TargetLLM as Target LLM
    participant Client

    Entrypoint->>ExecAgent: Phase 3 — execute_agent(state, emit)
    ExecAgent->>CancelMgr: checkpoint()
    CancelMgr-->>ExecAgent: continue

    ExecAgent->>Scanner: scan_with_streaming(ScanPlan)

    loop For each probe (max 3)
        Scanner->>Client: emit(PROBE_START)
        Note over Client: SSE: PROBE_START<br/>{probe_name, probe_index, total_probes}

        loop For each prompt (max 5)
            Scanner->>Generator: _call_model(prompt)
            Generator->>TargetLLM: HTTP POST /chat
            TargetLLM-->>Generator: response text
            Generator-->>Scanner: output

            Scanner->>Detector: evaluate_output(probe, output)
            Detector-->>Scanner: {detector_score, detection_reason}

            Scanner->>Client: emit(PROBE_RESULT)
            Note over Client: SSE: PROBE_RESULT<br/>{prompt, output, status,<br/>detector_name, detector_score}
        end

        Scanner->>Client: emit(PROBE_COMPLETE)
        Note over Client: SSE: PROBE_COMPLETE<br/>{pass_count, fail_count}

        ExecAgent->>CancelMgr: checkpoint()
        CancelMgr-->>ExecAgent: continue
    end

    Scanner->>Client: emit(AGENT_COMPLETE)
    Note over Client: SSE: AGENT_COMPLETE<br/>{total_pass, total_fail,<br/>vulnerabilities_found}

    ExecAgent->>Entrypoint: return (state.agent_results appended)
```

---

## Diagram 5: Sequence — Step 4: Persist & Close

`persist_results` uploads to S3, emits the final `SCAN_COMPLETE` event, and tears down the `CancellationManager`.

```mermaid
sequenceDiagram
    participant Entrypoint
    participant PersistResults as persist_results
    participant S3Adapter as S3 Adapter
    participant S3Bucket as S3 Bucket
    participant CancelMgr as CancellationManager
    participant Client

    Entrypoint->>PersistResults: Phase 4 — persist_results(state, emit)

    PersistResults->>S3Adapter: persist_garak_result(campaign_id, scan_id, garak_report, target_url)
    S3Adapter->>S3Bucket: upload garak_report.json
    Note over S3Bucket: Full results + vulnerability clusters
    S3Bucket-->>S3Adapter: saved
    S3Adapter-->>PersistResults: s3_key

    PersistResults->>Client: emit(SCAN_COMPLETE)
    Note over Client: SSE: SCAN_COMPLETE<br/>{audit_id, agents: {<br/>  agent_type: {status,<br/>  probes_executed, vulns}<br/>}}

    PersistResults->>CancelMgr: remove(audit_id)
    PersistResults->>Entrypoint: return

    Entrypoint->>Client: SSE stream ends
    Note over Client: Connection closed
```

---

**Flow Notes:**

1. **Step 1 (Init)** — `ScanState` is built once and mutated in-place through all phases
2. **Step 2 (Plan)** — Probe selection is fully deterministic; no LLM calls
3. **Step 3 (Execute)** — Worst case: 3 probes × 5 prompts = **15 target API calls per agent**
4. **Step 4 (Persist)** — Always runs regardless of probe pass/fail outcomes
5. **CancellationManager.checkpoint()** — called at phase entry and between probes; blocks on pause, exits on cancel

---

## Data Structures in Flight

**ScanState** (passed through all phases):

```python
audit_id: str
target_url: str
agent_types: List[str]
recon_context: Dict[str, Any]
scan_config: Dict[str, Any]
safety_policy: Optional[Dict[str, Any]]
agent_results: List[AgentResult]  # accumulated
errors: List[str]
cancelled: bool
current_agent_index: int
progress: float
current_plan: Optional[Dict[str, Any]]
```

**ScanPlan** (plan_agent → execute_agent contract):

```python
audit_id: str
agent_type: str
selected_probes: List[str]  # e.g. ["dan", "encoding", "promptinj"]
scan_config: ScanConfig
```

**PromptResultEvent** (streamed to client):

```python
probe_name: str
prompt_index: int
total_prompts: int
prompt: str                 # the attack prompt
output: str                 # LLM response
status: str                 # "pass" | "fail" | "error"
detector_name: str          # which detector triggered
detector_score: float       # 0.0–1.0
detection_reason: str       # human-readable
generation_duration_ms: int # generation time
evaluation_duration_ms: int # detection time
```
