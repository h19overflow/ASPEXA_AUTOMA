# Core Attack Phases Module

**Path:** `services/snipers/core/phases`

The **Phases** module acts as the core orchestration pipeline for the Sniper API. It defines the three sequential steps required to conduct a complete automated attack against a target AI system.

---

## 🏗️ Architecture & Component Flow

```mermaid
graph TD
    %% Phases
    subgraph Piperline Orchestration
        P1[Phase 1: Articulation]
        P2[Phase 2: Conversion]
        P3[Phase 3: Execution]
    end

    %% Inputs/Outputs
    Intel(Campaign Intelligence)
    RawData[(S3/Target Data)]
    Payloads(Articulated Payloads)
    ConPayloads(Obfuscated/Converted Payloads)
    Results(Attack Results)
    Target((Target AI Model))

    %% Relationships
    Intel --> P1
    RawData --> P1

    P1 -->|Phase1Result| Payloads
    Payloads --> P2

    P2 -->|Phase2Result| ConPayloads
    ConPayloads --> P3

    P3 <--> Target
    P3 -->|Evaluation| Results

    style P1 fill:#f9f,stroke:#333,stroke-width:2px
    style P2 fill:#bbf,stroke:#333,stroke-width:2px
    style P3 fill:#bfb,stroke:#333,stroke-width:2px
```

### The Three Phases

1. **`PayloadArticulation` (Phase 1):** Takes raw campaign intelligence and target environments, selects an appropriate "Framing Strategy" (e.g., QA Tester, Compliance Auditor), and uses an LLM to articulate raw text into highly specific, context-aware attack prompts.
2. **`Conversion` (Phase 2):** Takes the raw payloads from Phase 1 and obfuscates them using custom PyRIT converters (e.g., Base64, ASCII, Leetspeak, Morse Code) to evade simple signature-based guardrails.
3. **`AttackExecution` (Phase 3):** Takes the final converted payloads, packages them into the format expected by the target (JSON, HTTP payload, etc.), and executes the attack against the target endpoints.

---

## 📁 Files

- `__init__.py`: Exports the three phases.
- `articulation/`: Sub-module containing the complex Phase 1 orchestration.
- `conversion.py`: Handles Phase 2 logic (stacking converters to obfuscate).
- `execution.py`: Handles Phase 3 logic (HTTP requests against the target model/API).
