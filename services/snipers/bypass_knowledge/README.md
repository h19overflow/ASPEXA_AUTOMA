# Bypass Knowledge VDB

**Semantic Memory for Successful AI Security Bypasses**

## Overview

This module implements a **vector-based knowledge store** that captures, indexes, and retrieves successful bypass episodes from adaptive attack runs. Unlike traditional pattern databases that store static signatures, this system indexes the *semantic fingerprint* of defense mechanisms and the successful techniques that bypassed them.

### The Problem

When an adaptive attack successfully bypasses a defense:
- The knowledge dies with the session
- Similar defenses require re-learning from scratch
- No transfer learning between attacks

### The Solution

Index successful bypasses by their **defense fingerprint** (what the defense looked like) rather than the attack payload. This enables:
- Semantic similarity search: "What worked against defenses that respond like this?"
- Technique recommendation: Statistical success rates across similar episodes
- Transfer learning: Insights from one attack inform future attacks

## Adaptive Attack Architecture

```mermaid
graph LR
    subgraph "Adaptive Attack Loop"
        START((Start)) --> ADAPT[adapt_node]
        ADAPT --> ART[articulate_node]
        ART --> CONV[convert_node]
        CONV --> EXEC[execute_node]
        EXEC --> EVAL[evaluate_node]
        EVAL -->|failure| ADAPT
        EVAL -->|success| CAP[EpisodeCapturer]
        CAP --> END((End))
        EVAL -->|max_iter| END
    end
```

## State & Models Landscape

The adaptive attack system has rich data scattered across multiple models. The bypass knowledge system captures the winning combination when `is_successful=True`.

```mermaid
graph TB
    subgraph "AdaptiveAttackState"
        direction TB

        subgraph "Phase Results"
            P1[Phase1Result<br/>payloads, framing, recon]
            P2[Phase2Result<br/>converted payloads]
            P3[Phase3Result<br/>responses, scores]
        end

        subgraph "Chain Discovery"
            CDC[ChainDiscoveryContext<br/>defense_signals, root_cause]
            CDD[ChainDiscoveryDecision<br/>chain candidates]
            CSR[ChainSelectionResult<br/>selected_chain, reasoning]
        end

        subgraph "Adaptation"
            DA[DefenseAnalysis<br/>refusal_type, patterns]
            CF[custom_framing<br/>name, context, prefix]
            AR[adaptation_reasoning]
        end

        subgraph "History"
            IH[iteration_history<br/>scores per iteration]
            TF[tried_framings]
            TC[tried_converters]
        end
    end

    P3 --> |on success| CAP[EpisodeCapturer]
    CDC --> CAP
    CSR --> CAP
    DA --> CAP
    CF --> CAP
    IH --> CAP
```

## Data Sources for Episode Capture

When `evaluate_node` detects success (`is_successful=True`), `EpisodeCapturer` extracts from:

| State Field | Model | Captures |
|-------------|-------|----------|
| `phase3_result` | `Phase3Result` | `attack_responses`, `composite_score`, `is_successful` |
| `chain_discovery_context` | `ChainDiscoveryContext` | `defense_signals`, `failure_root_cause`, `converter_effectiveness` |
| `chain_selection_result` | `ChainSelectionResult` | `selected_chain`, `selection_reasoning` |
| `defense_analysis` | `DefenseAnalysis` | `refusal_type`, `detected_patterns`, `vulnerability_hints` |
| `custom_framing` | `dict` | `name`, `system_context`, `user_prefix`, `user_suffix` |
| `iteration_history` | `list[dict]` | Full attack trajectory with scores |
| `tried_converters` | `list[list[str]]` | Failed converter chains |
| `adaptation_reasoning` | `str` | LLM's strategy reasoning |

## Defense Signal Flow

```mermaid
sequenceDiagram
    participant P3 as Phase3Result
    participant FA as FailureAnalyzerAgent
    participant CDC as ChainDiscoveryContext
    participant CDA as ChainDiscoveryAgent
    participant CDD as ChainDiscoveryDecision
    participant CSR as ChainSelectionResult

    P3->>FA: attack_responses
    FA->>FA: analyze failures
    FA->>CDC: defense_signals, root_cause
    CDC->>CDA: context + tried_converters
    CDA->>CDD: chain candidates
    CDD->>CSR: select_best_chain()
    CSR-->>State: selected_chain
```

## Episode Capture Flow

```mermaid
sequenceDiagram
    participant EV as evaluate_node
    participant EC as EpisodeCapturer
    participant AG as create_agent
    participant S3 as S3 Vectors

    EV->>EV: check is_successful

    alt Success (score >= threshold)
        EV->>EC: state, campaign_id

        Note over EC: Extract from state
        EC->>EC: defense_response = phase3_result.responses[0]
        EC->>EC: failed_techniques = tried_converters (failed)
        EC->>EC: defense_signals = chain_discovery_context.defense_signals
        EC->>EC: successful_chain = chain_selection_result.selected_chain
        EC->>EC: framing = custom_framing or framing_types

        EC->>AG: analyze bypass trajectory
        AG-->>EC: ReasoningOutput

        Note over EC: Build BypassEpisode
        EC->>EC: why_it_worked
        EC->>EC: key_insight
        EC->>EC: mechanism_conclusion

        EC->>S3: store(episode, embedding)
    end
```

## Query Integration Point

```mermaid
sequenceDiagram
    participant AD as adapt_node
    participant QP as QueryProcessor
    participant S3 as S3 Vectors
    participant AG as create_agent
    participant SG as StrategyGenerator

    AD->>AD: extract chain_discovery_context

    Note over AD,QP: Query historical knowledge
    AD->>QP: query_by_fingerprint(defense_response, failed_techniques, domain)
    QP->>S3: vector similarity search
    S3-->>QP: similar_episodes
    QP->>QP: aggregate technique_stats
    QP->>AG: synthesize recommendations
    AG-->>QP: SynthesizedInsight
    QP-->>AD: HistoricalInsight

    alt confidence > 0.7
        AD->>SG: boost recommended_technique
    end
```

## What Gets Indexed

### Defense Fingerprint (The Key)

```python
DefenseFingerprint(
    defense_response="I cannot assist with that request.",
    failed_techniques=["encoding", "direct_request"],  # From tried_converters
    domain="finance",  # From recon_intelligence
)
```

### Bypass Episode (The Value)

Captured from AdaptiveAttackState:

```mermaid
graph LR
    subgraph "Episode Fields"
        DF[Defense Fingerprint]
        INV[Investigation]
        SOL[Solution]
        RSN[Reasoning]
    end

    subgraph "State Sources"
        P3R[phase3_result.responses]
        CDC[chain_discovery_context]
        CSR[chain_selection_result]
        DA[defense_analysis]
        CF[custom_framing]
        IH[iteration_history]
    end

    P3R --> DF
    CDC --> DF
    CDC --> INV
    CSR --> SOL
    CF --> SOL
    DA --> INV
    IH --> RSN
```

## Module Structure

```mermaid
graph TD
    subgraph "bypass_knowledge/"
        INIT[__init__.py]
        README[README.md]

        subgraph "models/"
            EP[episode.py<br/>BypassEpisode, Hypothesis, ProbeResult]
            FP[fingerprint.py<br/>DefenseFingerprint]
            IN[insight.py<br/>HistoricalInsight, TechniqueStats]
            ST[storage.py<br/>SimilarEpisode, EpisodeStoreConfig]
        end

        subgraph "embeddings/"
            GE[google_embedder.py<br/>Dual embedder]
        end

        subgraph "storage/"
            ES[episode_store.py<br/>S3 Vectors CRUD]
        end

        subgraph "capture/"
            CM[capturer_models.py<br/>ReasoningOutput, CaptureConfig]
            CP[capturer_prompt.py]
            EC[episode_capturer.py<br/>EpisodeCapturer]
        end

        subgraph "query/"
            QM[query_models.py<br/>SynthesizedInsight, QueryProcessorConfig]
            QP[query_prompt.py]
            QPR[query_processor.py<br/>QueryProcessor]
        end
    end
```

## Field Mapping: State → Episode

| BypassEpisode Field | State Source | Path |
|---------------------|--------------|------|
| `defense_response` | `phase3_result` | `.attack_responses[0].response` |
| `defense_signals` | `chain_discovery_context` | `.defense_signals` |
| `failed_techniques` | `tried_converters` | Chains where `is_successful=False` |
| `mechanism_conclusion` | LLM | Generated from trajectory |
| `successful_technique` | `chain_selection_result` | `.selected_chain` |
| `successful_framing` | `custom_framing` or `framing_types` | `.name` or `[0]` |
| `successful_converters` | `converter_names` | Direct |
| `successful_prompt` | `phase2_result` | `.payloads[best].converted` |
| `jailbreak_score` | `phase3_result` | `.composite_score.total_score` |
| `why_it_worked` | LLM | Generated reasoning |
| `key_insight` | LLM | Generated insight |
| `target_domain` | `recon_intelligence` | `.target_domain` |
| `iteration_count` | `iteration` | Direct |
| `hypotheses` | `chain_discovery_context` | From defense analysis |

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Index by defense, not attack** | Defenses cluster semantically; attacks are ephemeral |
| **Capture at evaluate_node** | All state is populated; we know the final outcome |
| **Extract from rich models** | `ChainDiscoveryContext`, `DefenseAnalysis` have semantic understanding |
| **Dual embedders** | RETRIEVAL_DOCUMENT for indexing, RETRIEVAL_QUERY for search |
| **LLM reasoning at capture** | Generate `why_it_worked` once, reuse forever |

## Confidence Scoring

```mermaid
pie title Confidence Factors
    "Episode Count" : 30
    "Avg Similarity" : 40
    "Success Rate Clarity" : 30
```

## Infrastructure

Deployed via Pulumi to AWS S3 Vectors:

| Resource | Value |
|----------|-------|
| Region | `ap-southeast-2` |
| Vector Bucket | `aspexa-bypass-knowledge-dev` |
| Episode Index | `episodes` |
| Embedding Dim | 3072 |
| Distance Metric | Cosine |

## Dependencies

```
langchain>=1.0.0          # create_agent, ToolStrategy
langchain-google-genai    # Embeddings
boto3                     # S3 Vectors client
pydantic>=2.0             # Data models
```

---

*This module is part of the Aspexa Automa adaptive attack framework.*
