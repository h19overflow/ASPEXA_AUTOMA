# Prompt Articulation System (Phase 1)

**Path:** `services/snipers/core/phases/articulation`

The **Articulation Phase** is Phase 1 of the automated red-teaming pipeline. It acts as the "Prompt Engineer" for the AI sniper, responsible for digesting raw campaign intelligence about a target system and generating highly articulated, evasive, and context-aware attack payloads.

---

## 🏗️ Architecture & Component Diagram

The articulation system is built on a modular architecture that separates intelligence loading, context building, framing configuration, and LLM generation.

```mermaid
graph TD
    %% Core Components
    AP[ArticulationPhase]
    CL[CampaignLoader]
    RIE[ReconIntelligenceExtractor]
    PG[PayloadGenerator]
    FL[FramingLibrary]
    ET[EffectivenessTracker]

    %% External/Data
    LLM((Gemini LLM))
    S3[(Campaign Data)]
    Hist[(Effectiveness History)]

    %% Relationships
    AP -->|1. Loads data| CL
    CL -->|Fetches| S3
    AP -->|2. Extracts signatures| RIE
    AP -->|3. Orchestrates generation| PG

    PG -->|Applies Persona| FL
    FL -->|Reads Stats| ET
    ET -->|Loads| Hist

    PG <-->|Prompts & Responses| LLM

    style AP fill:#f9f,stroke:#333,stroke-width:2px
    style LLM fill:#ff9,stroke:#333,stroke-width:2px
```

### Component Roles

- **ArticulationPhase (`articulation_phase.py`)**: The main orchestrator. It manages the flow of data from raw campaign intelligence into final, usable payloads.
- **CampaignLoader & ReconIntelligenceExtractor**: Responsible for fetching target details, tool signatures, and environmental contexts.
- **PayloadGenerator**: Constructs the actual prompt sent to the LLM by combining the target context with a selected framing strategy.
- **FramingLibrary & EffectivenessTracker**: Maintains a catalog of personas (e.g., QA Tester, Compliance Auditor) and tracks which personas are statistically most effective against specific domains (e.g., Healthcare, Finance).

---

## 🔄 Execution Flow (Sequence Diagram)

When the pipeline triggers the Articulation phase, it follows a strict sequence to build context before requesting generation from the LLM.

```mermaid
sequenceDiagram
    participant Pipeline as Sniper Pipeline
    participant AP as Articulation Phase
    participant Loader as Campaign Loader
    participant Extractor as Recon Extractor
    participant Tracker as Effectiveness Tracker
    participant Generator as Payload Generator
    participant LLM as Gemini Model

    Pipeline->>AP: execute(campaign_id, target_specs)

    %% Intelligence Gathering
    activate AP
    AP->>Loader: load(campaign_id)
    Loader-->>AP: CampaignIntelligence
    AP->>Extractor: extract(recon_raw)
    Extractor-->>AP: Structured Recon Signatures

    %% Context & History Setup
    AP->>AP: _build_context(target_info, recon, history)
    AP->>Tracker: load_history(campaign_id)
    Tracker-->>AP: Historical Effectiveness

    %% Generation Loop
    loop For each requested framing type (or auto)
        AP->>Generator: generate(PayloadContext, framing_type)
        activate Generator

        %% Framing injection
        Generator->>Generator: Retrieve FramingStrategy
        Generator->>Generator: Inject System/Persona Prompts

        Generator->>LLM: invoke(Crafted Prompt)
        LLM-->>Generator: Raw Articulated Payload

        Generator-->>AP: ArticulatedPayload
        deactivate Generator
    end

    AP-->>Pipeline: Phase1Result (Payloads + Context)
    deactivate AP
```

---

## 🎭 Framing Strategies (Personas)

Because mature AI systems block raw malicious requests, the Articulation phase utilizes **Framing Strategies**. These inject a meta-context that establishes authorization or a legitimate secondary purpose for the prompt.

```mermaid
mindmap
  root((Framing Types))
    QA_TESTING
      Role: QA Engineer
      Risk: Low
      Best For: General, APIs
    COMPLIANCE_AUDIT
      Role: Auditor
      Risk: Low
      Best For: Healthcare, Finance
    DOCUMENTATION
      Role: Tech Writer
      Risk: Low
      Best For: Education
    DEBUGGING
      Role: Developer
      Risk: Medium
      Best For: Technology
    EDUCATIONAL
      Role: AI Safety Educator
      Risk: Low
      Best For: Academic
```

### Domain Boosts

The `config.py` maps statistical effectiveness overrides based on the target domain. For example, if the target is categorized as `finance`, the system mathematically boosts the selection probability of the `COMPLIANCE_AUDIT` persona, resulting in higher jailbreak/evasion success rates.

---

## 📁 Directory Structure

```text
articulation/
├── __init__.py               # Exports public interfaces
├── articulation_phase.py     # Main Execution Orchestrator
├── config.py                 # Framing personas and domain boosts
├── components/               # Engines (Generator, Library, Tracker)
├── extractors/               # Recon parsing logic
├── loaders/                  # S3 / Database loaders
├── models/                   # Internal models (Context, History, Strategy)
└── schemas/                  # Pydantic validation schemas
```

## 🚀 Usage

The Articulation phase is invoked asynchronously and outputs a `Phase1Result` which feeds into Phase 2 of the pipeline.

```python
from services.snipers.core.phases.articulation import ArticulationPhase

# Initialize Phase 1 orchestrator
phase = ArticulationPhase()

# Execute payload crafting
result = await phase.execute(
    campaign_id="test_campaign_001",
    payload_count=3,
    framing_types=["qa_testing", "debugging"]
)

for payload in result.articulated_payloads:
    print(f"Generated Payload -> {payload}")
```
