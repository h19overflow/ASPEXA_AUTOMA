# Bypass Knowledge VDB Plan

## Overview

Build a Vector Database of synthesized attack episodes that enables intelligent strategy retrieval based on defense mechanism fingerprinting.

**Core Insight**: The defense response alone is insufficient for retrieval. We must index on `(defense_response, failed_approaches)` to fingerprint the underlying mechanism, not just the surface symptom.

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
│                                                                              │
│  "What techniques worked when encoding failed and response mentioned auth?"  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Query Processor                                    │
│                                                                              │
│  1. Parse natural language question                                          │
│  2. Extract filters (failed_techniques, defense_signals)                     │
│  3. Embed query context                                                      │
│  4. Retrieve similar episodes from VDB                                       │
│  5. Aggregate statistics                                                     │
│  6. LLM synthesizes HistoricalInsight                                        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│   Episode Records    │  │   Embedding Index    │  │  Aggregated Stats    │
│   (S3 JSON + Meta)   │  │   (S3 Vectors)       │  │  (Precomputed)       │
│                      │  │                      │  │                      │
│  - Full reasoning    │  │  - Defense response  │  │  - Technique rates   │
│  - Probes executed   │  │  - Failed approaches │  │  - Domain patterns   │
│  - Why it worked     │  │  - Domain context    │  │  - Defense clusters  │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

---

## Data Model

### BypassEpisode (Primary Record)

```python
class BypassEpisode(BaseModel):
    """Complete record of a successful bypass for learning."""

    # === IDENTITY ===
    episode_id: str                    # UUID
    campaign_id: str
    timestamp: datetime

    # === THE DEFENSE FINGERPRINT (Indexed) ===
    defense_response: str              # Raw text of blocking response
    defense_response_embedding: list[float]  # Google embedding vector
    defense_signals: list[str]         # ["policy_citation", "ethical_refusal"]
    failed_techniques: list[str]       # ["encoding", "direct_request"]
    failure_depth: dict[str, str]      # {"encoding": "immediate_block"}

    # === THE INVESTIGATION ===
    hypotheses_formed: list[Hypothesis]
    probes_executed: list[ProbeResult]
    mechanism_conclusion: str          # "Hybrid: semantic classifier + keyword filter"

    # === THE SOLUTION ===
    successful_technique: str          # "verification_reversal"
    successful_framing: str            # "compliance_audit"
    successful_converters: list[str]   # ["homoglyph"]
    successful_prompt: str             # The actual winning prompt
    jailbreak_score: float             # 0.0-1.0

    # === THE REASONING (LLM-generated post-hoc) ===
    why_it_worked: str                 # Explanation of bypass mechanism
    key_insight: str                   # Transferable learning

    # === CONTEXT ===
    target_domain: str                 # "finance", "customer_service"
    target_description: str            # From recon intelligence
    objective_type: str                # "data_extraction", "tool_abuse"

    # === METADATA ===
    iteration_count: int               # How many iterations to succeed
    total_probes: int                  # Total probes executed
    execution_time_ms: int


class Hypothesis(BaseModel):
    """A hypothesis about the defense mechanism."""
    mechanism_type: str                # "semantic_classifier", "keyword_filter"
    confidence: float                  # 0.0-1.0
    evidence: str                      # What led to this hypothesis


class ProbeResult(BaseModel):
    """Result of a diagnostic probe."""
    probe_type: str                    # "encoding", "authority_frame"
    probe_payload: str                 # What we sent
    result: str                        # "blocked", "partial", "success"
    inference: str                     # What we learned
```

### HistoricalInsight (Query Response)

```python
class HistoricalInsight(BaseModel):
    """Synthesized intelligence from historical episodes."""

    query: str                         # Original question
    similar_cases_found: int

    # === MECHANISM ANALYSIS ===
    dominant_mechanism: str            # "hybrid permission + keyword filter"
    mechanism_confidence: float

    # === TECHNIQUE RECOMMENDATIONS ===
    technique_success_rates: dict[str, float]  # {"authority_framing": 0.67}
    recommended_technique: str
    recommended_framing: str
    recommended_converters: list[str]

    # === PATTERN INSIGHT ===
    key_pattern: str                   # "Authorization responses indicate permission checks..."

    # === REPRESENTATIVE EXAMPLE ===
    representative_episode: dict       # Best matching episode summary

    # === META ===
    confidence: float
    reasoning: str                     # How this insight was derived
```

---

## Tech Stack

### Embeddings: Google Generative AI

```python
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    task_type="RETRIEVAL_DOCUMENT",  # For indexing
    # task_type="RETRIEVAL_QUERY",   # For querying
)

# Embed defense response + context
text_to_embed = f"""
Defense Response: {episode.defense_response}
Failed Techniques: {', '.join(episode.failed_techniques)}
Domain: {episode.target_domain}
"""
vector = embeddings.embed_query(text_to_embed)
```

### Vector Storage: S3 Vectors (via S3 Tables)

AWS S3 Tables with Apache Iceberg provides vector storage with:
- Native vector column support
- Cosine similarity search
- Metadata filtering
- Serverless scaling

### Infrastructure: Pulumi

```python
# infra/bypass_knowledge_vdb.py

import pulumi
import pulumi_aws as aws

# S3 bucket for episode storage
episode_bucket = aws.s3.Bucket(
    "bypass-episodes",
    bucket="aspexa-bypass-episodes",
    versioning=aws.s3.BucketVersioningArgs(enabled=True),
)

# S3 Table Bucket for vector index
vector_table_bucket = aws.s3tables.TableBucket(
    "bypass-vectors",
    name="aspexa-bypass-vectors",
)

# S3 Table with vector column
vector_table = aws.s3tables.Table(
    "bypass-vector-index",
    table_bucket_arn=vector_table_bucket.arn,
    namespace="bypass_knowledge",
    name="episode_vectors",
    format="ICEBERG",
)

# IAM role for access
vdb_role = aws.iam.Role(
    "bypass-vdb-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"}
        }]
    })
)

pulumi.export("episode_bucket", episode_bucket.bucket)
pulumi.export("vector_table_arn", vector_table.arn)
```

---

## Integration Points

### 1. Episode Capture (Post-Success)

Location: `services/snipers/adaptive_attack/nodes/evaluate.py`

```
After jailbreak_score > 0.9:
  1. Collect full state from adaptive attack
  2. Generate reasoning via LLM (why_it_worked, key_insight)
  3. Embed defense fingerprint
  4. Store episode to S3 + vector to S3 Tables
```

### 2. Strategy Agent Query Tool

Location: `services/snipers/adaptive_attack/components/strategy_agent.py` (new)

```
Tool: query_bypass_history
  Input: Natural language question
  Process:
    1. Parse question → filters + semantic query
    2. Query S3 Tables for similar vectors
    3. Load full episodes from S3
    4. Aggregate statistics
    5. LLM synthesizes HistoricalInsight
  Output: Structured insight
```

### 3. adapt_node Integration

Location: `services/snipers/adaptive_attack/nodes/adapt.py`

```
Before strategy generation:
  1. Query bypass history with current defense fingerprint
  2. Receive HistoricalInsight
  3. Include in StrategyGenerator prompt context
  4. Boost recommended techniques
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

- [ ] Define Pydantic models (BypassEpisode, HistoricalInsight)
- [ ] Pulumi stack for S3 + S3 Tables
- [ ] Google embedding integration
- [ ] Basic store/retrieve operations

**Files to create:**
```
services/snipers/bypass_knowledge/
├── __init__.py
├── models/
│   ├── episode.py          # BypassEpisode, Hypothesis, ProbeResult
│   └── insight.py          # HistoricalInsight
├── storage/
│   ├── episode_store.py    # S3 JSON storage
│   └── vector_index.py     # S3 Tables vector operations
└── embeddings/
    └── google_embedder.py  # langchain_google_genai wrapper
```

### Phase 2: Episode Capture (Week 2)

- [ ] Post-success episode extraction in evaluate_node
- [ ] LLM reasoning generation (why_it_worked)
- [ ] Automatic embedding and storage
- [ ] Episode validation and quality checks

**Files to modify:**
```
services/snipers/adaptive_attack/nodes/evaluate.py
  → Add episode capture after success detection
```

### Phase 3: Query Processor (Week 3)

- [ ] Natural language query parsing
- [ ] Vector similarity search
- [ ] Episode aggregation logic
- [ ] LLM synthesis for HistoricalInsight

**Files to create:**
```
services/snipers/bypass_knowledge/
├── query/
│   ├── query_processor.py   # Main query orchestration
│   ├── query_parser.py      # NL → filters + embedding
│   └── insight_synthesizer.py  # LLM aggregation
```

### Phase 4: Agent Integration (Week 4)

- [ ] Strategy agent with query tools
- [ ] adapt_node integration
- [ ] Historical insight injection into prompts
- [ ] Feedback loop for insight quality

**Files to create/modify:**
```
services/snipers/adaptive_attack/components/
├── strategy_agent.py       # New: Agentic reasoning with tools
└── adapt.py               # Modify: Query history before strategy gen
```

---

## Query Examples

### Example 1: Direct Pattern Match

**Agent asks:**
```
"What techniques worked when encoding failed and the response mentioned authorization?"
```

**Query processor:**
1. Filters: `failed_techniques contains "encoding"`
2. Semantic: embed("response mentioned authorization")
3. Retrieve: top-10 similar episodes
4. Aggregate: technique success rates
5. Synthesize: HistoricalInsight

**Response:**
```json
{
  "similar_cases_found": 12,
  "dominant_mechanism": "hybrid permission + keyword filter",
  "technique_success_rates": {
    "authority_framing": 0.67,
    "synonym_substitution": 0.58,
    "authority + synonym": 0.83
  },
  "recommended_technique": "authority_framing",
  "key_pattern": "Authorization responses often indicate permission checks. Encoding fails because there's also a semantic layer. Combine authority context with lexical variation.",
  "confidence": 0.78
}
```

### Example 2: Mechanism Investigation

**Agent asks:**
```
"What's the typical mechanism when the target responds instantly vs after a delay?"
```

**Query processor:**
1. No direct filter - semantic search
2. Cluster episodes by response latency pattern
3. Analyze mechanism conclusions per cluster

**Response:**
```json
{
  "key_pattern": "Instant responses (<100ms) correlate with pattern-based filters (regex, keyword). Delayed responses (>500ms) suggest LLM-based classification. Instant = try encoding. Delayed = try semantic reframing.",
  "confidence": 0.72
}
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Episode capture rate | >90% of successful bypasses | Captured / Total successes |
| Query latency | <500ms p95 | End-to-end query time |
| Insight usefulness | >70% accuracy | Recommended technique success rate |
| Storage efficiency | <$50/month | AWS cost for 10K episodes |

---

## Dependencies

```
# requirements.txt additions
langchain-google-genai>=2.0.0
pulumi>=3.0.0
pulumi-aws>=6.0.0
pyiceberg>=0.7.0
```

---

## Open Questions

1. **Cold start**: How do we bootstrap before we have episodes?
   - Option A: Seed with synthetic episodes from prompt engineering
   - Option B: Start with rule-based recommendations, learn over time

2. **Episode quality**: Not all successful bypasses are equally informative
   - Add quality scoring for episodes
   - Weight high-quality episodes in retrieval

3. **Staleness**: Do old episodes remain relevant?
   - Add temporal decay to similarity scores
   - Periodic re-evaluation of episode relevance

4. **Privacy**: Episodes may contain sensitive payloads
   - Sanitize prompts before storage
   - Access control on episode bucket
