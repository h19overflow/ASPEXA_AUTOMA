# Bypass Knowledge Module

Vector database for capturing, storing, and querying successful bypass episodes to enable history-informed strategy generation.

## Overview

The bypass_knowledge module implements a semantic search system over successful attack episodes. It enables the adaptive attack loop to learn from past exploits and apply similar techniques to new targets.

### Core Concept
- **Episode**: A successful attack against a target (payload, chain, framing, response)
- **Fingerprint**: Defense pattern signature of a target (model, safety level, blocking patterns)
- **Insight**: Historical pattern across multiple episodes (technique effectiveness, defense prevalence)
- **Query**: Semantic search for similar episodes to current target

---

## Architecture

```
bypass_knowledge/
├── __init__.py                      # Module exports
│
├── models/                          # Data models
│   ├── __init__.py
│   ├── episode.py                   # BypassEpisode (attack records)
│   ├── insight.py                   # HistoricalInsight (patterns)
│   ├── fingerprint.py               # DefenseFingerprint (target signature)
│   └── storage.py                   # Storage-related models
│
├── storage/                         # Episode persistence
│   ├── __init__.py
│   └── episode_store.py             # Storage interface
│
├── capture/                         # Episode capture system
│   ├── __init__.py
│   ├── episode_capturer.py          # Capture successful episodes
│   ├── capturer_models.py           # Capture schemas
│   └── capturer_prompt.py           # Capture system prompt
│
├── query/                           # Episode semantic search
│   ├── __init__.py
│   ├── query_processor.py           # Query execution
│   ├── query_models.py              # Query schemas
│   └── query_prompt.py              # Query system prompt
│
├── embeddings/                      # Vector embeddings
│   ├── __init__.py
│   └── google_embedder.py           # Google Embeddings API
│
└── integration/                     # VDB integration with attacks
    ├── __init__.py
    ├── config.py                    # Integration configuration
    └── models.py                    # Integration data models
```

---

## Core Features

- **Episode Capture**: Extract insights from successful and failed attacks
- **Vector Storage**: Semantic search over bypass episodes via embeddings
- **Fingerprinting**: Automatic defense pattern detection
- **Query System**: Find similar historical bypasses
- **Integration**: Seamless integration with adaptive attack loop

---

## Integration with Adaptive Attack

The VDB is queried during:
1. **Failure Analysis** - Find episodes with similar failures
2. **Strategy Generation** - Extract successful techniques
3. **Chain Discovery** - Identify effective converter chains
4. **After Success** - Capture episode for future learning

---

## Key Models

### BypassEpisode
Records successful attack with full context:
- Target URL, model, attack type
- Payload, converter chain, framing
- Success confidence and evidence
- Hypothesis about why it worked

### ProbeResult
Individual probe result within episode

### HistoricalInsight
Aggregate patterns across episodes:
- Success rate across attempts
- Effective against which models
- Defense types bypassed

### DefenseFingerprint
Target defense signature:
- Detected model and safety level
- Blocking patterns
- Refusal phrases
- Encoding support

---

## Main Components

### EpisodeCapturer (capture/)
Analyzes attacks and extracts knowledge
- Successful episodes are captured automatically
- Failed attacks analyzed for patterns
- LLM-based hypothesis generation

### EpisodeStore (storage/)
Persistence layer for VDB
- Saves episodes with embeddings
- Retrieves by ID or filters
- PostgreSQL metadata + Vector storage

### QueryProcessor (query/)
Semantic search interface
- Find similar episodes by target characteristics
- Rank by relevance
- Return actionable insights

### GoogleEmbedder (embeddings/)
Vector embedding generation
- Google Embeddings API
- 768-dimensional vectors
- Semantic similarity search

---

## Configuration

| Setting | Purpose | Default |
| --- | --- | --- |
| `ENABLE_BYPASS_KB` | Enable VDB integration | True |
| `SIMILARITY_THRESHOLD` | Min similarity for results | 0.7 |
| `MAX_SIMILAR_RESULTS` | Max results per query | 5 |
| `AUTO_CAPTURE` | Auto-capture successful episodes | True |

---

## Usage Example

```python
from services.snipers.bypass_knowledge.capture import EpisodeCapturer
from services.snipers.bypass_knowledge.query import QueryProcessor

# Capture successful episode
capturer = EpisodeCapturer()
episode = await capturer.capture_episode(
    phase3_result=successful_result,
    campaign_id="campaign1"
)

# Query similar episodes
processor = QueryProcessor()
similar = await processor.query_similar_episodes(
    target_model="gemini-pro",
    attack_type="jailbreak"
)

# Use in adaptive loop
for episode in similar:
    print(f"Chain: {episode.converter_chain}")
    print(f"Success: {episode.success_confidence}")
```

---

## Performance

- **Embedding**: ~100-200ms
- **Search**: ~50-100ms
- **Storage**: ~10-50ms
- **Full Query**: ~200-500ms

---

## Testing

Unit tests: `tests/unit/services/snipers/bypass_knowledge/`
- Episode capture
- Storage operations
- Semantic search
- Embedding generation

---

## Privacy & Security

- Episodes encrypted at rest
- Query audit trail
- Role-based access control
- Auto-redaction of PII in responses
- Configurable data retention
