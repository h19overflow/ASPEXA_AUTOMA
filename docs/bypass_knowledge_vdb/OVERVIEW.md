# Bypass Knowledge VDB - Overview

## Purpose

Build a Vector Database of successful attack episodes that enables intelligent strategy retrieval based on defense mechanism fingerprinting.

## Core Insight

The defense response alone is insufficient for retrieval. We must index on:
```
(defense_response, failed_approaches) → successful_technique
```

This fingerprints the underlying mechanism, not just the surface symptom.

---

## Objectives

1. **Capture rich episodes** - Store the full reasoning trace, not just outcomes
2. **Enable semantic search** - Find similar defense patterns across campaigns
3. **Synthesize intelligence** - Return actionable insights, not raw records
4. **Support agentic querying** - Strategy agent can ask questions about historical patterns

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Strategy Reasoning Agent                             │
│  "What techniques worked when encoding failed and response mentioned auth?"  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Query Processor                                    │
│  1. Parse question  2. Extract filters  3. Embed  4. Retrieve  5. Synthesize │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
                          ┌──────────────────────────┐
                          │      S3 Vectors          │
                          │  (Vector Bucket + Index) │
                          │                          │
                          │  • Episode embeddings    │
                          │  • Full episode metadata │
                          │  • Cosine similarity     │
                          │  • Sub-100ms queries     │
                          └──────────────────────────┘
```

---

## Phase Breakdown

| Phase | Name | Scope | Dependency | Doc |
|-------|------|-------|------------|-----|
| 1 | Models | Pydantic data models | None | [PHASE_1_MODELS.md](PHASE_1_MODELS.md) |
| 2 | Infrastructure | Pulumi S3 Vectors | None | [PHASE_2_INFRASTRUCTURE.md](PHASE_2_INFRASTRUCTURE.md) |
| 3 | Embeddings | Google embedding wrapper | Phase 1 | [PHASE_3_EMBEDDINGS.md](PHASE_3_EMBEDDINGS.md) |
| 4 | Storage | Episode store + vector index | Phase 1, 2, 3 | [PHASE_4_STORAGE.md](PHASE_4_STORAGE.md) |
| 5 | Capture | Episode extraction in evaluate_node | Phase 4 | [PHASE_5_CAPTURE.md](PHASE_5_CAPTURE.md) |
| 6 | Query | Query processor + synthesis | Phase 4 | [PHASE_6_QUERY.md](PHASE_6_QUERY.md) |
| 7 | Integration | adapt_node integration | Phase 5, 6 | [PHASE_7_INTEGRATION.md](PHASE_7_INTEGRATION.md) |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Embeddings | `langchain_google_genai` (gemini-embedding-001, 3072 dim) |
| Vector Storage | AWS S3 Vectors (vector bucket + index) |
| Episode Storage | S3 Vectors metadata (JSON in vector records) |
| Infrastructure | Pulumi (`aws-native.s3vectors`) |
| Similarity | Cosine similarity (sub-100ms queries) |
| SDK | `boto3.client('s3vectors')` |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Episode capture rate | >90% of successful bypasses |
| Query latency | <500ms p95 |
| Insight usefulness | >70% recommended technique success |
| Storage cost | <$50/month for 10K episodes |

---

## File Structure (Target)

```
services/snipers/bypass_knowledge/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── episode.py           # BypassEpisode, Hypothesis, ProbeResult
│   └── insight.py           # HistoricalInsight, TechniqueStats
├── embeddings/
│   ├── __init__.py
│   └── google_embedder.py   # GoogleEmbedder, DefenseFingerprint
├── storage/
│   ├── __init__.py
│   └── episode_store.py     # EpisodeStore (S3 Vectors operations)
├── capture/
│   ├── __init__.py
│   └── episode_capturer.py  # EpisodeCapturer (extract from state)
├── query/
│   ├── __init__.py
│   └── query_processor.py   # QueryProcessor (search + synthesis)
└── integration/
    ├── __init__.py
    └── adapt_node_hook.py   # AdaptNodeHook (history injection)

infra/bypass_knowledge/
├── __init__.py
├── vector_infrastructure.py  # Pulumi S3 Vectors resources
├── Pulumi.yaml
└── Pulumi.dev.yaml
```
