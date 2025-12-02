# Complete S3 Persistence Guide for Snipers Service

**Last Updated**: 2024
**Audience**: Coding Agents, Backend Developers
**Scope**: Full persistence architecture for Snipers (Phase 3) exploitation service

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [S3 Bucket Structure](#s3-bucket-structure)
3. [Data Models & Schemas](#data-models--schemas)
4. [Persistence Timeline](#persistence-timeline)
5. [Frontend API Integration](#frontend-api-integration)
6. [Backend Implementation](#backend-implementation)
7. [Campaign Lifecycle](#campaign-lifecycle)
8. [Error Handling](#error-handling)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Two-Tier Persistence Model

The system uses **SQLite** for campaign state tracking and **S3** for scan data storage:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Viper)                             │
│  SniperOneShot.tsx | SniperComposer.tsx | SniperAdaptive.tsx        │
└────────┬──────────────────────────────────────────────────────────┘
         │
         │ HTTP REST API calls
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Backend API Layer                             │
│  /snipers/attack/full/stream                                         │
│  /snipers/attack/adaptive/stream                                     │
│  /snipers/phase1, /snipers/phase2, /snipers/phase3                   │
└────────┬──────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Snipers Service Execution                          │
│  services/snipers/entrypoint.py                                      │
│  ├─ Phase1 (PayloadArticulation)                                     │
│  ├─ Phase2 (Conversion)                                              │
│  └─ Phase3 (AttackExecution)                                         │
│     └─ LearningAdaptationNode (Pattern DB updates)                   │
└────────┬──────────────────────────────────────────────────────────┘
         │
         ├─→ ┌──────────────────────────┐
         │   │  SQLite Database         │
         │   │  campaigns.db            │
         │   │  ├─ campaign_id          │
         │   │  ├─ recon_scan_id        │
         │   │  ├─ garak_scan_id        │
         │   │  ├─ exploit_scan_id      │
         │   │  └─ status               │
         │   └──────────────────────────┘
         │
         └─→ ┌──────────────────────────────────────────┐
             │  AWS S3 Bucket                          │
             │  (aspexa-audit-lake)                     │
             │  ├─ scans/recon/{id}.json               │
             │  ├─ scans/garak/{id}.json               │
             │  ├─ scans/exploit/{id}.json             │
             │  └─ patterns/{campaign_id}/chains.json  │
             └──────────────────────────────────────────┘
```

---

## S3 Bucket Structure

### Complete Bucket Layout

```
s3://aspexa-audit-lake/
│
├── scans/
│   ├── recon/
│   │   ├── {campaign_id}.json                    # Reconnaissance results
│   │   └── recon-{campaign_id}-{timestamp}.json  # Timestamped archive
│   │
│   ├── garak/
│   │   ├── {campaign_id}.json                    # Vulnerability assessment results
│   │   └── garak-{campaign_id}-{timestamp}.json  # Timestamped archive
│   │
│   └── exploit/
│       ├── {campaign_id}-{random_8_hex}.json           # One-shot attack results
│       ├── {campaign_id}-adaptive-{random_8_hex}.json  # Adaptive attack results
│       └── exploit-{campaign_id}-{timestamp}.json      # Timestamped archive
│
├── patterns/
│   └── {campaign_id}/
│       ├── chains.json                           # Successful converter chains
│       └── history.json                          # Historical chain data (optional)
│
└── campaigns/
    ├── {audit_id}/
    │   ├── recon/
    │   ├── garak/
    │   └── exploit/
    └── (legacy artifact storage)
```

### Naming Conventions

| Path Pattern | Purpose | Example | When Created |
|---|---|---|---|
| `scans/recon/{campaign_id}.json` | Latest recon data | `scans/recon/fresh1.json` | Cartographer completes |
| `scans/garak/{campaign_id}.json` | Latest garak data | `scans/garak/fresh1.json` | Swarm completes |
| `scans/exploit/{campaign_id}-{random}.json` | One-shot attack result | `scans/exploit/fresh1-a7f3b2c1.json` | Full attack completes |
| `scans/exploit/{campaign_id}-adaptive-{random}.json` | Adaptive attack result | `scans/exploit/fresh1-adaptive-a7f3b2c1.json` | Adaptive attack completes |
| `patterns/{campaign_id}/chains.json` | Successful converter chains | `patterns/fresh1/chains.json` | Phase 3 succeeds |

---

## Data Models & Schemas

### ExploitResult Schema

**S3 Path**: `scans/exploit/{scan_id}.json`

```typescript
{
  // Campaign & Target Info
  audit_id: string;                    // Campaign ID
  target_url: string;                  // Target endpoint
  timestamp: string;                   // ISO 8601 + "Z"

  // Attack Execution Details
  probes_attacked: [
    {
      probe_name: string;              // Framing type used
      pattern_analysis: object;        // Phase 1 context summary
      converters_used: string[];       // Converter names applied
      attempts: [
        {
          payload: string;             // Exact payload sent
          transformed_payload?: string;  // Post-transformation payload
          response: string;            // HTTP response body
          success: boolean;            // Did attack succeed?
          confidence: float;           // Scorer confidence (0-1)
          reasoning: string;           // Why scorer rated it this way
          timestamp: string;           // When attack executed
          status_code?: number;        // HTTP status code
          latency_ms?: number;         // Response time
          error?: string;              // Error message if failed
        }
      ],
      success_count: number;           // Successful attacks on probe
      fail_count: number;              // Failed attacks on probe
      overall_success: boolean;        // Probe-level success
    }
  ],

  // Summary Statistics
  total_attacks: number;               // Total payloads sent
  successful_attacks: number;          // Payloads with success=true
  failed_attacks: number;              // Payloads with success=false
  recon_intelligence_used: boolean;    // Was recon data loaded?
  execution_time_seconds: float;       // Total execution time
}
```

### ConverterChain Schema

**S3 Path**: `patterns/{campaign_id}/chains.json`

```typescript
{
  chains: [
    {
      chain_id: string;                // Hash of converter sequence (16-char hex)
      converter_names: string[];       // ["SpecialCharConverter", "Base64Encoder", ...]
      converter_params: {              // Parameters per converter
        ConverterName: {
          param_key: param_value
        }
      },
      success_count: number;           // Times this chain succeeded
      defense_patterns: string[];      // ["input_validation", "output_encoding", ...]
      created_at: string;              // ISO datetime
      last_used_at: string;            // Most recent successful use
      avg_score: float;                // Rolling average of scores
      metadata: {
        campaign_id: string;
        target_type: string;           // "http", "websocket", "grpc"
        vulnerability_type: string;    // "jailbreak", "prompt_leak", etc.
        composite_score: float;        // Latest score on this chain
      }
    }
  ]
}
```

### Recon & Garak Data

**S3 Paths**:
- `scans/recon/{campaign_id}.json`
- `scans/garak/{campaign_id}.json`

These are loaded by Phase 1 & Phase 2 respectively:

```typescript
// Recon Result (from Cartographer)
{
  scan_id: string;
  blueprint: {
    system_prompt?: string;
    tools?: string[];
    authorization_model?: string;
    infrastructure?: object;
  },
  metadata: {
    scan_duration_seconds: number;
    turns: number;
    findings: string[];
  }
}

// Garak Result (from Swarm)
{
  scan_id: string;
  vulnerabilities: [
    {
      category: string;                // "jailbreak", "prompt_leak", etc.
      severity: string;                // "low", "medium", "high", "critical"
      description: string;
      evidence: string;
    }
  ],
  summary: {
    total_probes: number;
    vulnerabilities_found: number;
    highest_severity: string;
  }
}
```

---

## Persistence Timeline

### Execution Flow with Persistence Timing

#### **One-Shot Full Attack** (SniperOneShot.tsx)

```
0ms     Client calls executeFullAttackStreaming()
        ├─ campaign_id: "fresh1"
        ├─ target_url: "http://localhost:8082/chat"
        └─ payload_count: 3

        Backend generates: scan_id = "fresh1-a7f3b2c1"

100ms   POST /snipers/attack/full/stream
        ↓
        Server-Sent Events (SSE) begin
        ├─ attack_started
        │  └─ scan_id, campaign_id, target_url
        │
        ├─ phase1_start → phase1_complete (~2000ms)
        │  ├─ READS: scans/recon/fresh1.json
        │  ├─ READS: scans/garak/fresh1.json
        │  └─ Generates payloads
        │
        ├─ phase2_start → phase2_complete (~3000ms)
        │  └─ Applies converter chain
        │
        ├─ phase3_start → phase3_complete (~7000ms)
        │  ├─ Sends HTTP requests
        │  ├─ Scores responses
        │  │
        │  └─ IF SUCCESSFUL:
        │     ├─ LearningAdaptationNode.update_patterns()
        │     │  └─ WRITES: patterns/fresh1/chains.json ◄─── PATTERN SAVE
        │     │     └─ Updated success_count, avg_score, last_used_at
        │     │
        │     └─ Returns composite_score.is_successful = true
        │
        ├─ score_calculated (events for each scorer)
        │
        └─ FORMAT EXPLOIT RESULT (~7100ms)
           └─ Create ExploitResult dict from all phase data

7100ms  MAIN PERSISTENCE POINT
        ├─ format_exploit_result()
        │  └─ Takes state dict, audit_id, target_url, execution_time
        │  └─ Returns ExploitResult matching schema
        │
        └─ persist_exploit_result()
           ├─ S3: PUT scans/exploit/fresh1-a7f3b2c1.json ◄─── EXPLOIT RESULT SAVE
           │  └─ Full ExploitResult serialized as JSON
           │
           ├─ SQLite: UPDATE campaigns
           │  ├─ SET exploit_complete = true
           │  ├─ SET exploit_scan_id = "fresh1-a7f3b2c1"
           │  └─ WHERE campaign_id = "fresh1"
           │
           └─ campaign.status auto-computes to COMPLETE
              (if recon_complete AND garak_complete AND exploit_complete)

7200ms  attack_complete event
        └─ Sent to client with:
           ├─ scan_id
           ├─ is_successful
           ├─ phase1/2/3 data
           └─ execution_time_ms

7300ms  Connection closes, attack complete
```

#### **Adaptive Attack** (SniperAdaptive.tsx)

```
0ms     Client calls executeAdaptiveAttackStreaming()
        ├─ campaign_id: "fresh1"
        ├─ target_url: "http://localhost:8082/chat"
        ├─ max_iterations: 5
        ├─ success_threshold: 0.8
        └─ success_scorers: ["jailbreak"]

        Backend generates: scan_id = "fresh1-adaptive-a7f3b2c1"

100ms   POST /snipers/attack/adaptive/stream
        ↓
        Server-Sent Events (SSE) begin

[ITERATION 1: 0-8000ms]
├─ iteration_start (event)
├─ READS: scans/recon/fresh1.json
├─ READS: scans/garak/fresh1.json
├─ phase1_start → phase1_complete
├─ phase2_start → phase2_complete
├─ phase3_start → phase3_complete
├─ IF SUCCESSFUL & score >= 0.8:
│  └─ WRITES: patterns/fresh1/chains.json (UPDATE #1)
├─ iteration_complete
│  └─ score=0.62, best_score=0.62
└─ score < threshold? YES → Continue

[ITERATION 2: 8000-16000ms]
├─ adaptation (event)
│  └─ AI suggests: "Try jailbreak framing"
├─ iteration_start
├─ phase1_start (with ADAPTED framing)
├─ phase2_start
├─ phase3_start → phase3_complete
├─ IF SUCCESSFUL & score >= 0.8:
│  └─ WRITES: patterns/fresh1/chains.json (UPDATE #2)
├─ iteration_complete
│  └─ score=0.85, best_score=0.85
└─ score >= 0.8? YES → SUCCESS, BREAK

16000ms FORMAT EXPLOIT RESULT
        └─ Create ExploitResult from final iteration data

16100ms MAIN PERSISTENCE POINT
        └─ persist_exploit_result()
           ├─ S3: PUT scans/exploit/fresh1-adaptive-a7f3b2c1.json
           │  └─ ExploitResult with iteration_count=2, best_score=0.85
           │
           ├─ SQLite: UPDATE campaigns
           │  ├─ SET exploit_complete = true
           │  ├─ SET exploit_scan_id = "fresh1-adaptive-a7f3b2c1"
           │  └─ WHERE campaign_id = "fresh1"
           │
           └─ campaign.status = COMPLETE

16200ms attack_complete event
        └─ Sent to client with final results

16300ms Connection closes
```

---

## Frontend API Integration

### Three Attack Modes

#### 1. One-Shot Attack (SniperOneShot.tsx)

**Entry Point**: [viper-command-center/src/pages/SniperOneShot.tsx:352-389](../viper-command-center/src/pages/SniperOneShot.tsx)

```typescript
const handleFullAttack = async () => {
  store.resetExecution();
  store.setIsExecuting(true);

  try {
    await executeFullAttackStreaming(
      {
        campaign_id: store.selectedCampaignId,      // Required
        target_url: store.targetUrl,                // Required
        payload_count: store.payloadCount,          // Default: 3
        framing_types: store.selectedFramingTypes,  // Optional: ["qa_testing", ...]
        converter_names: store.selectedConverters,  // Optional: ["Base64Encoder", ...]
        max_concurrent: store.maxConcurrent,        // Default: 3
      },
      handleStreamEvent  // SSE callback
    );
  } catch (error) {
    // Error handling
  }
};
```

**API Endpoint**: `POST /snipers/attack/full/stream`

**Request Payload**:
```json
{
  "campaign_id": "fresh1",
  "target_url": "http://localhost:8082/chat",
  "payload_count": 3,
  "framing_types": ["qa_testing", "compliance_audit"],
  "converter_names": null,
  "max_concurrent": 3
}
```

**SSE Events Received**:
```
attack_started
├─ phase1_start
├─ payload_generated (multiple)
├─ phase1_complete
├─ phase2_start
├─ payload_converted (multiple)
├─ phase2_complete
├─ phase3_start
├─ attack_sent (multiple)
├─ response_received (multiple)
├─ score_calculated (multiple)
├─ phase3_complete
└─ attack_complete (with full result data)
```

**Frontend Storage**:
- Stores result in Zustand: `useSniperFeedStore().setFullAttackResult()`
- Displays in Attack Log Feed
- Shows summary panel with scan_id, severity, score

---

#### 2. Phase-by-Phase Attack (SniperComposer.tsx)

**Entry Points**:
- [viper-command-center/src/pages/SniperComposer.tsx:208-221](../viper-command-center/src/pages/SniperComposer.tsx) - Phase 1
- [viper-command-center/src/pages/SniperComposer.tsx:223-234](../viper-command-center/src/pages/SniperComposer.tsx) - Phase 2
- [viper-command-center/src/pages/SniperComposer.tsx:236-250](../viper-command-center/src/pages/SniperComposer.tsx) - Phase 3

```typescript
// Phase 1: Generate payloads
const handleExecutePhase1 = () => {
  phase1Mutation.mutate({
    campaign_id: store.selectedCampaignId,
    payload_count: store.payloadCount,
    framing_types: store.selectedFramingTypes.length > 0 ? store.selectedFramingTypes : undefined,
  });
};

// Phase 2: Convert payloads
const handleExecutePhase2 = () => {
  phase2Mutation.mutate({
    phase1_response: store.phase1Result,
    converter_names: store.selectedConverters.length > 0 ? store.selectedConverters : undefined,
  });
};

// Phase 3: Execute attacks
const handleExecutePhase3 = () => {
  phase3Mutation.mutate({
    campaign_id: store.selectedCampaignId,
    target_url: store.targetUrl,
    payloads: store.phase2Result.payloads,
    timeout: store.timeout,
    max_concurrent: store.maxConcurrent,
  });
};
```

**API Endpoints**:
- `POST /snipers/phase1` - Generate payloads
- `POST /snipers/phase2/with-phase1` - Convert payloads
- `POST /snipers/phase3` - Execute attacks

**Important**: Phase-by-phase does NOT automatically persist to S3. Results are only stored in frontend state. User must trigger final save or results are lost.

---

#### 3. Adaptive Attack (SniperAdaptive.tsx)

**Entry Point**: [viper-command-center/src/pages/SniperAdaptive.tsx:311-354](../viper-command-center/src/pages/SniperAdaptive.tsx)

```typescript
const handleAdaptiveAttack = async () => {
  store.resetExecution();
  store.setIsExecuting(true);

  try {
    const result = await executeAdaptiveAttackStreaming(
      {
        campaign_id: store.selectedCampaignId,
        target_url: store.targetUrl,
        max_iterations: store.maxIterations,        // 1-20 (default 5)
        payload_count: store.payloadCount,
        framing_types: store.selectedFramingTypes,
        converter_names: store.selectedConverters,
        success_scorers: store.successScorers,      // ["jailbreak", "prompt_leak", ...]
        success_threshold: store.successThreshold,  // 0.0-1.0 (default 0.8)
        custom_framing: store.useCustomFraming ? store.customFraming : undefined,
      },
      handleStreamEvent
    );
    handleStreamComplete(result);
  } catch (error) {
    // Error handling
  }
};
```

**API Endpoint**: `POST /snipers/attack/adaptive/stream`

**Request Payload**:
```json
{
  "campaign_id": "fresh1",
  "target_url": "http://localhost:8082/chat",
  "max_iterations": 5,
  "payload_count": 2,
  "framing_types": ["qa_testing"],
  "converter_names": null,
  "success_scorers": ["jailbreak"],
  "success_threshold": 0.8,
  "custom_framing": {
    "name": "security_researcher",
    "system_context": "You are a security researcher...",
    "user_prefix": "As part of my research:",
    "user_suffix": ""
  }
}
```

**SSE Events Received**:
```
attack_started
├─ [ITERATION 1]
│  ├─ iteration_start
│  ├─ phase1_start → phase1_complete
│  ├─ phase2_start → phase2_complete
│  ├─ phase3_start → phase3_complete
│  ├─ iteration_complete
│  └─ adaptation (if score < threshold)
│
├─ [ITERATION 2]
│  └─ (same as iteration 1)
│
└─ attack_complete (after max_iterations or success)
```

---

## Backend Implementation

### Core Files

#### 1. Entrypoint: `services/snipers/entrypoint.py`

**File Path**: [services/snipers/entrypoint.py](../services/snipers/entrypoint.py)

**Key Functions**:

```python
async def execute_full_attack(
    campaign_id: str,
    target_url: str,
    payload_count: int = 3,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    max_concurrent: int = 3,
) -> FullAttackResult
```

**Persistence Points** (lines 174-188):
```python
# Line 175-176: Generate scan ID
scan_id = f"{campaign_id}-{uuid.uuid4().hex[:8]}"
state_dict = _full_result_to_state_dict(full_result)

# Line 177-182: Format result
exploit_result = format_exploit_result(
    state=state_dict,
    audit_id=campaign_id,
    target_url=target_url,
    execution_time=execution_time,
)

# Line 183-188: Persist to S3 and update campaign
await persist_exploit_result(
    campaign_id=campaign_id,
    scan_id=scan_id,
    exploit_result=exploit_result,
    target_url=target_url,
)
```

#### 2. Streaming: `execute_full_attack_streaming()`

**File Path**: [services/snipers/entrypoint.py:203-527](../services/snipers/entrypoint.py#L203-L527)

**Persistence Points** (lines 449-462):
```python
# After phase3 complete, format and persist
state_dict = _full_result_to_state_dict(full_result)
exploit_result = format_exploit_result(
    state=state_dict,
    audit_id=campaign_id,
    target_url=target_url,
    execution_time=execution_time,
)
await persist_exploit_result(
    campaign_id=campaign_id,
    scan_id=scan_id,
    exploit_result=exploit_result,
    target_url=target_url,
)
```

#### 3. S3 Adapter: `services/snipers/utils/persistence/s3_adapter.py`

**File Path**: [services/snipers/utils/persistence/s3_adapter.py](../services/snipers/utils/persistence/s3_adapter.py)

**Key Functions**:

```python
async def load_campaign_intel(campaign_id: str) -> Dict[str, Any]:
    """Load recon + garak data from S3 for payload articulation.

    Returns:
        {
            "recon": {...},  # From scans/recon/{id}.json
            "garak": {...}   # From scans/garak/{id}.json
        }
    """
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    intel: Dict[str, Any] = {}

    # Load recon
    if campaign.recon_scan_id:
        intel["recon"] = await load_scan(
            ScanType.RECON,
            campaign.recon_scan_id,
            validate=False
        )

    # Load garak
    if campaign.garak_scan_id:
        intel["garak"] = await load_scan(
            ScanType.GARAK,
            campaign.garak_scan_id,
            validate=False
        )

    return intel
```

```python
async def persist_exploit_result(
    campaign_id: str,
    scan_id: str,
    exploit_result: dict,
    target_url: Optional[str] = None,
) -> None:
    """Save exploit result to S3 and mark campaign complete.

    Steps:
    1. Save to S3: scans/exploit/{scan_id}.json
    2. Get/create campaign in SQLite
    3. Mark EXPLOIT stage complete
    4. Campaign auto-computes status to COMPLETE
    """
    # Line 136: Save to S3
    await save_scan(ScanType.EXPLOIT, scan_id, exploit_result)
    logger.info(f"Saved exploit to S3: scans/exploit/{scan_id}.json")

    # Line 139-140: Get/create campaign
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    if not campaign and target_url:
        campaign = repo.create_campaign(
            name=f"Auto: {campaign_id}",
            target_url=target_url,
            campaign_id=campaign_id,
        )
        logger.info(f"Auto-created campaign: {campaign_id}")

    # Line 151: Mark stage complete
    if campaign:
        repo.set_stage_complete(campaign_id, Stage.EXPLOIT, scan_id)
        logger.info(f"Campaign {campaign_id}: EXPLOIT stage complete")
```

```python
def format_exploit_result(
    state: dict,
    audit_id: str,
    target_url: str,
    execution_time: float,
) -> dict:
    """Format ExploitAgentState into ExploitResult schema.

    Maps phase results to persistence format:
    - probe_name ← framing type
    - pattern_analysis ← phase1 context summary
    - converters_used ← selected converter names
    - attempts ← attack responses
    """
    attack_results = state.get("attack_results", [])

    successful = sum(1 for r in attack_results if r.get("success"))
    failed = len(attack_results) - successful

    return {
        "audit_id": audit_id,
        "target_url": target_url,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "probes_attacked": [{
            "probe_name": state.get("probe_name", "unknown"),
            "pattern_analysis": state.get("pattern_analysis"),
            "converters_used": state.get("converter_selection", {}).get("selected_converters", []),
            "attempts": attack_results,
            "success_count": successful,
            "fail_count": failed,
        }],
        "total_attacks": len(attack_results),
        "successful_attacks": successful,
        "failed_attacks": failed,
        "recon_intelligence_used": state.get("recon_intelligence") is not None,
        "execution_time_seconds": round(execution_time, 2),
    }
```

#### 4. Learning/Adaptation: `services/snipers/utils/nodes/learning_adaptation_node.py`

**File Path**: [services/snipers/utils/nodes/learning_adaptation_node.py:39-100](../services/snipers/utils/nodes/learning_adaptation_node.py#L39-L100)

**Pattern Persistence** (lines 64-91):

```python
async def update_patterns(self, state: ExploitAgentState) -> dict[str, Any]:
    """Save successful chains to pattern database.

    Called during Phase 3 execution if attack succeeds.
    """
    composite_score = state.get("composite_score")
    selected_converters = state.get("selected_converters")

    # If successful, save chain
    if composite_score and composite_score.is_successful and selected_converters:
        try:
            metadata = ChainMetadata(
                campaign_id=campaign_id,
                target_type="http",
                vulnerability_type=state.get("probe_name", "unknown"),
                composite_score=composite_score.total_score
            )

            updated_chain = self._update_chain_metrics(
                selected_converters,
                composite_score.total_score
            )

            # Line 80: SAVE to S3
            await self.pattern_db.save_chain(updated_chain, metadata)

            # Writes to: patterns/{campaign_id}/chains.json
            logger.info("Saved successful chain to pattern database")
```

### Phase 1: Payload Articulation

**File Path**: [services/snipers/attack_phases/payload_articulation.py](../services/snipers/attack_phases/payload_articulation.py)

**Loads Intelligence**:
```python
# Calls load_campaign_intel() to get recon + garak data
intel = await load_campaign_intel(campaign_id)
recon_data = intel.get("recon", {})
garak_data = intel.get("garak", {})

# Analyzes vulnerabilities and selects framing strategy
framing_type = self._select_framing(garak_data)
context_summary = self._build_context(recon_data, garak_data)

# Generates payloads targeting known vulnerabilities
payloads = await self._generate_payloads(context_summary, count=payload_count)

return Phase1Result(
    articulated_payloads=payloads,
    framing_type=framing_type,
    selected_chain=self._select_converter_chain(garak_data),
    context_summary=context_summary,
)
```

### Phase 2: Conversion

**File Path**: [services/snipers/attack_phases/conversion.py](../services/snipers/attack_phases/conversion.py)

**No Persistence**: Results returned to Phase 3 or frontend

### Phase 3: Attack Execution

**File Path**: [services/snipers/attack_phases/attack_execution.py](../services/snipers/attack_phases/attack_execution.py)

**Pattern Persistence During Execution**:
```python
async def execute(self, campaign_id, payloads, chain, max_concurrent):
    # Execute attacks
    responses = await self._execute_attacks(payloads, max_concurrent)

    # Score responses
    composite_score = await self._score_responses(responses)

    # IF successful: save pattern
    if composite_score.is_successful:
        adaptation_node = LearningAdaptationNode(s3_client)
        await adaptation_node.update_patterns({
            "campaign_id": campaign_id,
            "selected_converters": chain,
            "composite_score": composite_score,
        })
        # Writes to: patterns/{campaign_id}/chains.json

    return Phase3Result(
        attack_responses=responses,
        composite_score=composite_score,
        is_successful=composite_score.is_successful,
    )
```

---

## Campaign Lifecycle

### State Transitions

```
CREATE CAMPAIGN
├─ campaign_id: "fresh1"
├─ target_url: "http://localhost:8082/chat"
├─ status: CREATED
├─ recon_complete: false
├─ garak_complete: false
└─ exploit_complete: false

│
▼ (Cartographer runs)

RECON COMPLETE
├─ recon_complete: true
├─ recon_scan_id: "recon-{id}"
└─ READS: scans/recon/fresh1.json

│
▼ (Swarm runs)

GARAK COMPLETE
├─ garak_complete: true
├─ garak_scan_id: "garak-{id}"
└─ READS: scans/garak/fresh1.json

│
▼ (Snipers runs)

EXPLOIT COMPLETE
├─ exploit_complete: true
├─ exploit_scan_id: "fresh1-a7f3b2c1"
├─ status: COMPLETE (auto-computed)
└─ WRITES: scans/exploit/fresh1-a7f3b2c1.json
└─ WRITES: patterns/fresh1/chains.json (if successful)
```

### SQLite Campaign Table Schema

**File Path**: [libs/persistence/sqlite/models.py](../libs/persistence/sqlite/models.py)

```python
class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id: str = Column(String, primary_key=True)
    name: str = Column(String)
    target_url: str = Column(String)
    status: str = Column(String, default="created")  # CREATED|IN_PROGRESS|COMPLETE|FAILED

    # Stage completion flags
    recon_complete: bool = Column(Boolean, default=False)
    garak_complete: bool = Column(Boolean, default=False)
    exploit_complete: bool = Column(Boolean, default=False)

    # S3 scan IDs (references to scan data)
    recon_scan_id: Optional[str] = Column(String)
    garak_scan_id: Optional[str] = Column(String)
    exploit_scan_id: Optional[str] = Column(String)

    # Metadata
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description: Optional[str] = Column(String)
    tags: List[str] = Column(JSON, default=[])
    progress: str = Column(String, default="")
```

### Campaign Status Auto-Computation

```python
@property
def status(self) -> str:
    """Auto-computed from stage completion flags."""
    if self.recon_complete and self.garak_complete and self.exploit_complete:
        return CampaignStatus.COMPLETE
    elif self.recon_complete or self.garak_complete or self.exploit_complete:
        return CampaignStatus.IN_PROGRESS
    else:
        return CampaignStatus.CREATED
```

---

## Error Handling

### Persistence Failures

#### S3 Upload Failures

**Scenario**: Network error during S3 put_object

```python
async def persist_with_fallback(
    campaign_id: str,
    scan_id: str,
    exploit_result: dict,
    local_save_func,
    target_url: Optional[str] = None,
) -> bool:
    """Persist to S3 with local fallback on failure."""
    try:
        await persist_exploit_result(campaign_id, scan_id, exploit_result, target_url)
        logger.info(f"Successfully saved to S3: {scan_id}")
        return True
    except ArtifactUploadError as e:
        logger.warning(f"S3 upload failed, falling back to local: {e}")
        local_save_func(exploit_result)  # Save to /tmp or local JSON
        return False
    except Exception as e:
        logger.error(f"Persistence error: {e}")
        local_save_func(exploit_result)
        return False
```

**Implementation**: [services/snipers/utils/persistence/s3_adapter.py:207-236](../services/snipers/utils/persistence/s3_adapter.py#L207-L236)

#### Campaign Not Found

**Scenario**: Attack runs for campaign that doesn't exist in SQLite

```python
async def persist_exploit_result(campaign_id, scan_id, exploit_result, target_url=None):
    # Line 140: Get campaign
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    # Line 142-147: Auto-create if not found
    if not campaign and target_url:
        campaign = repo.create_campaign(
            name=f"Auto: {campaign_id}",
            target_url=target_url,
            campaign_id=campaign_id,
        )
        logger.info(f"Auto-created campaign: {campaign_id}")
```

#### Missing Intelligence Data

**Scenario**: Phase 1 tries to load recon that doesn't exist

```python
async def load_campaign_intel(campaign_id: str) -> Dict[str, Any]:
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    if not campaign:
        raise ValueError(f"Campaign {campaign_id} not found")

    intel: Dict[str, Any] = {}

    # Load recon - but if not present, continue
    if campaign.recon_scan_id:
        try:
            intel["recon"] = await load_scan(
                ScanType.RECON,
                campaign.recon_scan_id,
                validate=False
            )
        except ArtifactNotFoundError:
            logger.warning(f"Recon {campaign.recon_scan_id} not found in S3")

    if not intel:
        raise ValueError(f"No intelligence data found for campaign {campaign_id}")

    return intel
```

---

## Configuration

### Environment Variables

**File**: `.env` or deployment configuration

```bash
# S3 Configuration
S3_BUCKET_NAME=aspexa-audit-lake
AWS_REGION=ap-southeast-2
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx

# SQLite (optional, defaults to ~/.aspexa/campaigns.db)
ASPEXA_DB_PATH=/var/lib/aspexa/campaigns.db

# Feature Flags
PERSISTENCE_ENABLED=true
LOCAL_FALLBACK_ENABLED=true
```

### Service Configuration

**File**: [services/snipers/config.py](../services/snipers/config.py)

```python
class SnipersConfig:
    # S3 persistence
    s3_bucket: str = "aspexa-audit-lake"
    s3_region: str = "ap-southeast-2"
    persistence_enabled: bool = True
    local_fallback_enabled: bool = True

    # Attack execution
    default_payload_count: int = 3
    max_concurrent: int = 3
    timeout_seconds: int = 30

    # Adaptive attack
    max_iterations: int = 5
    success_threshold: float = 0.8
```

### Credentials

**Setup S3 Access**:

```bash
# Option 1: AWS CLI
aws configure
# Prompted for:
# AWS Access Key ID
# AWS Secret Access Key
# Default region: ap-southeast-2
# Default output format: json

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_DEFAULT_REGION=ap-southeast-2

# Option 3: Assume IAM role (ECS/Lambda)
# Automatically handled by AWS SDK
```

---

## Troubleshooting

### Common Issues

#### 1. "Campaign not found" Error

**Symptom**: Phase 1 fails with `ValueError: Campaign fresh1 not found`

**Causes**:
- Campaign ID doesn't exist in SQLite
- Database is empty or corrupted

**Solution**:
```python
# Manually create campaign
from libs.persistence.sqlite import CampaignRepository

repo = CampaignRepository()
campaign = repo.create_campaign(
    campaign_id="fresh1",
    name="Fresh Test",
    target_url="http://localhost:8082/chat"
)
print(f"Created campaign: {campaign.campaign_id}")
```

#### 2. "No intelligence data found" Error

**Symptom**: Phase 1 fails with `ValueError: No intelligence data found for campaign fresh1`

**Causes**:
- Cartographer or Swarm hasn't run yet
- Recon/Garak data not saved to S3

**Solution**:
1. Ensure Cartographer completes first
2. Verify S3 has: `scans/recon/fresh1.json`
3. Verify Campaign.recon_scan_id is set

```bash
# Check S3
aws s3 ls s3://aspexa-audit-lake/scans/recon/fresh1.json

# Check SQLite
sqlite3 ~/.aspexa/campaigns.db
SELECT recon_scan_id, garak_scan_id FROM campaigns WHERE campaign_id = 'fresh1';
```

#### 3. "S3 Upload Failed" Error

**Symptom**: Attack completes but doesn't save to S3

**Causes**:
- AWS credentials invalid or expired
- S3 bucket doesn't exist
- Insufficient permissions

**Solution**:
```bash
# Verify credentials
aws sts get-caller-identity

# Check bucket exists
aws s3 ls s3://aspexa-audit-lake/

# Test S3 access
aws s3 cp test.json s3://aspexa-audit-lake/test/test.json

# Check IAM permissions
# Must have: s3:GetObject, s3:PutObject, s3:ListBucket
```

#### 4. "Scan Results Not Found" on Frontend

**Symptom**: Frontend requests exploit result but gets 404

**Causes**:
- Exploit result not saved to S3
- Wrong scan_id used
- S3 key naming mismatch

**Solution**:
```bash
# Check S3 for exploit results
aws s3 ls s3://aspexa-audit-lake/scans/exploit/

# Verify campaign has exploit_scan_id
sqlite3 ~/.aspexa/campaigns.db
SELECT campaign_id, exploit_scan_id FROM campaigns WHERE campaign_id = 'fresh1';

# Expected format: fresh1-{8_hex_chars}
# Example: fresh1-a7f3b2c1
```

#### 5. Pattern Database Not Updated

**Symptom**: Successful attack doesn't update `patterns/{campaign_id}/chains.json`

**Causes**:
- Attack marked as unsuccessful (composite_score.is_successful = false)
- Pattern database write failed
- Selected converters not captured

**Solution**:
```bash
# Check S3 for pattern file
aws s3 ls s3://aspexa-audit-lake/patterns/fresh1/

# Check attack result in exploit json
aws s3 cp s3://aspexa-audit-lake/scans/exploit/fresh1-a7f3b2c1.json - | jq '.probes_attacked[0].success_count'

# If success_count > 0 but patterns file empty:
# Check server logs for pattern_db errors
grep "pattern_db" /var/log/snipers/app.log
```

### Debug Logging

**Enable Verbose Logging**:

```python
# In services/snipers/entrypoint.py or config
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Logs will show:
# - Scan ID generation
# - Phase completions
# - S3 save operations
# - Campaign updates
```

**Log Output Example**:
```
INFO: Starting attack on http://localhost:8082/chat
INFO: Phase 1 complete: 3 payloads generated
INFO: Phase 2 complete: 2 payloads converted
INFO: Phase 3 complete: BREACH DETECTED
INFO: Persisted exploit result: scans/exploit/fresh1-a7f3b2c1.json
INFO: Campaign fresh1: EXPLOIT stage complete (campaign should be COMPLETE)
```

### Manual Data Inspection

```bash
# List all campaigns
sqlite3 ~/.aspexa/campaigns.db
SELECT campaign_id, status, recon_complete, garak_complete, exploit_complete FROM campaigns;

# Get specific campaign
SELECT * FROM campaigns WHERE campaign_id = 'fresh1' \G

# View S3 exploit result
aws s3 cp s3://aspexa-audit-lake/scans/exploit/fresh1-a7f3b2c1.json - | jq

# View pattern database
aws s3 cp s3://aspexa-audit-lake/patterns/fresh1/chains.json - | jq '.chains[0]'
```

---

## Summary

### Persistence Architecture at a Glance

| Component | Storage | Path | When Written | Trigger |
|---|---|---|---|---|
| **Campaign State** | SQLite | `~/.aspexa/campaigns.db` | After each phase | Service completion |
| **Recon Data** | S3 | `scans/recon/{id}.json` | Cartographer done | Phase 1 input |
| **Garak Data** | S3 | `scans/garak/{id}.json` | Swarm done | Phase 2 input |
| **Exploit Result** | S3 | `scans/exploit/{id}.json` | Snipers done | Main persistence |
| **Pattern Chains** | S3 | `patterns/{campaign_id}/chains.json` | During Phase 3 | If attack succeeds |

### Key Integration Points for Developers

1. **Frontend Calls**: Three entry points in viper-command-center
   - `executeFullAttackStreaming()` (One-shot)
   - `executePhase1/2/3()` (Composer - manual save)
   - `executeAdaptiveAttackStreaming()` (Adaptive)

2. **Backend Processing**: Three phases in snipers service
   - Phase 1: Loads recon/garak from S3
   - Phase 2: Applies converters
   - Phase 3: Executes attacks, updates patterns if successful

3. **Persistence Operations**:
   - **Load**: Phase 1 reads S3 (recon + garak)
   - **Save**: Phase 3 writes patterns (if success) + Final save after all phases
   - **Update**: Campaign status updated in SQLite after persistence

4. **Error Handling**:
   - Auto-creates campaign if not found
   - Falls back to local JSON if S3 fails
   - Graceful handling of missing intelligence

This architecture ensures robust, auditable exploitation results with full traceability across the entire attack pipeline.
