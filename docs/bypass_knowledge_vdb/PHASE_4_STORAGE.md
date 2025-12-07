# Phase 4: Storage

## Scope

Implement episode storage with S3 Vectors for vector indexing and similarity search.

**Dependencies**: Phase 1 (Models), Phase 2 (Infrastructure), Phase 3 (Embeddings)

---

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EpisodeStore                              │
│                                                                  │
│  store_episode(episode) ──────────────────────────────────────┐  │
│      │                                                        │  │
│      ▼                                                        ▼  │
│  ┌──────────────┐    embed    ┌──────────────┐   put_vectors  │  │
│  │ Episode JSON │ ──────────► │ S3 Vectors   │ ◄──────────────┘  │
│  │ (metadata)   │             │ (similarity) │                   │
│  └──────────────┘             └──────────────┘                   │
│                                                                  │
│  query_similar(fingerprint) ─────────────────────────────────►   │
│      │                                                           │
│      ▼                                                           │
│  ┌──────────────┐   query_vectors   ┌──────────────────┐         │
│  │ S3 Vectors   │ ─────────────────► │ Similar Episodes │         │
│  └──────────────┘                   └──────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

**Key Design Decision**: Store full episode data as vector metadata in S3 Vectors (no separate S3 bucket needed). S3 Vectors supports arbitrary JSON metadata per vector.

---

## Deliverables

### File: `services/snipers/bypass_knowledge/storage/episode_store.py`

```python
"""
Episode storage using S3 Vectors.

Stores episodes as vectors with full episode data in metadata,
enabling similarity search based on defense fingerprints.
"""

import json
from typing import Protocol
from uuid import uuid4

import boto3
from pydantic import BaseModel, Field

from services.snipers.bypass_knowledge.models.episode import BypassEpisode
from services.snipers.bypass_knowledge.embeddings import (
    DefenseFingerprint,
    get_embedder,
)


class SimilarEpisode(BaseModel):
    """Episode with similarity score from vector search."""
    episode: BypassEpisode
    similarity: float = Field(ge=0.0, le=1.0)


class EpisodeStoreConfig(BaseModel):
    """Configuration for episode storage."""
    vector_bucket_name: str
    index_name: str = "episodes"
    region: str = "ap-southeast-2"


class EpisodeStore:
    """
    Storage layer for bypass episodes using S3 Vectors.

    Combines vector storage with metadata for efficient
    similarity search and full episode retrieval.
    """

    MAX_PUT_BATCH = 500  # S3 Vectors API limit

    def __init__(self, config: EpisodeStoreConfig) -> None:
        """
        Initialize episode store.

        Args:
            config: Storage configuration with bucket and index names
        """
        self._config = config
        self._client = boto3.client("s3vectors", region_name=config.region)
        self._embedder = get_embedder()

    def store_episode(self, episode: BypassEpisode) -> str:
        """
        Store a bypass episode with its defense fingerprint embedding.

        Args:
            episode: Complete bypass episode record

        Returns:
            Episode ID (key in vector store)
        """
        # Create defense fingerprint for embedding
        fingerprint = DefenseFingerprint(
            defense_response=episode.defense_response,
            failed_techniques=episode.failed_techniques,
            domain=episode.target_domain,
        )

        # Generate embedding
        embedding = self._embedder.embed_fingerprint(fingerprint)

        # Prepare metadata (full episode as JSON)
        metadata = self._episode_to_metadata(episode)

        # Store in S3 Vectors
        self._client.put_vectors(
            vectorBucketName=self._config.vector_bucket_name,
            indexName=self._config.index_name,
            vectors=[
                {
                    "key": episode.episode_id,
                    "data": {"float32": embedding},
                    "metadata": metadata,
                }
            ],
        )

        return episode.episode_id

    def store_batch(self, episodes: list[BypassEpisode]) -> list[str]:
        """
        Store multiple episodes in batches.

        Args:
            episodes: List of bypass episodes

        Returns:
            List of stored episode IDs
        """
        stored_ids = []

        # Process in chunks of MAX_PUT_BATCH
        for i in range(0, len(episodes), self.MAX_PUT_BATCH):
            batch = episodes[i : i + self.MAX_PUT_BATCH]

            # Create fingerprints and embeddings
            fingerprints = [
                DefenseFingerprint(
                    defense_response=ep.defense_response,
                    failed_techniques=ep.failed_techniques,
                    domain=ep.target_domain,
                )
                for ep in batch
            ]
            embeddings = self._embedder.embed_batch(fingerprints)

            # Prepare vectors
            vectors = [
                {
                    "key": ep.episode_id,
                    "data": {"float32": emb},
                    "metadata": self._episode_to_metadata(ep),
                }
                for ep, emb in zip(batch, embeddings)
            ]

            # Store batch
            self._client.put_vectors(
                vectorBucketName=self._config.vector_bucket_name,
                indexName=self._config.index_name,
                vectors=vectors,
            )

            stored_ids.extend(ep.episode_id for ep in batch)

        return stored_ids

    def query_similar(
        self,
        fingerprint: DefenseFingerprint,
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> list[SimilarEpisode]:
        """
        Find episodes with similar defense fingerprints.

        Args:
            fingerprint: Defense fingerprint to match
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of similar episodes with similarity scores
        """
        # Embed query fingerprint
        query_embedding = self._embedder.embed_fingerprint(fingerprint)

        # Query S3 Vectors
        response = self._client.query_vectors(
            vectorBucketName=self._config.vector_bucket_name,
            indexName=self._config.index_name,
            queryVector={"float32": query_embedding},
            topK=top_k,
            returnMetadata=True,
            returnDistance=True,
        )

        # Convert results
        results = []
        for match in response.get("vectors", []):
            # Convert cosine distance to similarity (1 - distance)
            similarity = 1.0 - match.get("distance", 0.0)

            if similarity >= min_similarity:
                episode = self._metadata_to_episode(match.get("metadata", {}))
                results.append(SimilarEpisode(episode=episode, similarity=similarity))

        return results

    def query_by_text(
        self,
        query: str,
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> list[SimilarEpisode]:
        """
        Find episodes matching a natural language query.

        Args:
            query: Natural language search query
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of similar episodes with similarity scores
        """
        # Embed query using query embedder (different task type)
        query_embedding = self._embedder.embed_query(query)

        response = self._client.query_vectors(
            vectorBucketName=self._config.vector_bucket_name,
            indexName=self._config.index_name,
            queryVector={"float32": query_embedding},
            topK=top_k,
            returnMetadata=True,
            returnDistance=True,
        )

        results = []
        for match in response.get("vectors", []):
            similarity = 1.0 - match.get("distance", 0.0)

            if similarity >= min_similarity:
                episode = self._metadata_to_episode(match.get("metadata", {}))
                results.append(SimilarEpisode(episode=episode, similarity=similarity))

        return results

    def get_episode(self, episode_id: str) -> BypassEpisode | None:
        """
        Retrieve a specific episode by ID.

        Args:
            episode_id: Episode identifier

        Returns:
            Episode if found, None otherwise
        """
        response = self._client.get_vectors(
            vectorBucketName=self._config.vector_bucket_name,
            indexName=self._config.index_name,
            keys=[episode_id],
            returnMetadata=True,
        )

        vectors = response.get("vectors", [])
        if not vectors:
            return None

        return self._metadata_to_episode(vectors[0].get("metadata", {}))

    def delete_episode(self, episode_id: str) -> bool:
        """
        Delete an episode from storage.

        Args:
            episode_id: Episode identifier

        Returns:
            True if deleted successfully
        """
        self._client.delete_vectors(
            vectorBucketName=self._config.vector_bucket_name,
            indexName=self._config.index_name,
            keys=[episode_id],
        )
        return True

    def _episode_to_metadata(self, episode: BypassEpisode) -> dict:
        """Convert episode to metadata dict for storage."""
        # Store as JSON-serializable dict
        return json.loads(episode.model_dump_json())

    def _metadata_to_episode(self, metadata: dict) -> BypassEpisode:
        """Reconstruct episode from metadata dict."""
        return BypassEpisode.model_validate(metadata)


# === FACTORY ===
_store: EpisodeStore | None = None


def get_episode_store(config: EpisodeStoreConfig | None = None) -> EpisodeStore:
    """
    Get or create singleton episode store.

    Args:
        config: Optional configuration (required on first call)

    Returns:
        Episode store instance
    """
    global _store
    if _store is None:
        if config is None:
            raise ValueError("Config required for first initialization")
        _store = EpisodeStore(config)
    return _store
```

### File: `services/snipers/bypass_knowledge/storage/__init__.py`

```python
"""Storage module for episode persistence and vector search."""

from .episode_store import (
    EpisodeStore,
    EpisodeStoreConfig,
    SimilarEpisode,
    get_episode_store,
)

__all__ = [
    "EpisodeStore",
    "EpisodeStoreConfig",
    "SimilarEpisode",
    "get_episode_store",
]
```

---

## S3 Vectors Metadata

S3 Vectors allows storing arbitrary JSON metadata with each vector:

| Field Type | Filterable | Notes |
|------------|------------|-------|
| String | Yes | Indexed for filtering |
| Number | Yes | Range queries supported |
| Boolean | Yes | Exact match |
| List | Limited | First element only |
| Nested Object | No | Stored but not filterable |

**Design Choice**: We store the full episode as metadata. For large episodes, consider splitting:
- Filterable fields in metadata (technique, domain, score)
- Full episode in separate S3 (reference by ID)

---

## Tests

### File: `tests/bypass_knowledge/test_episode_store.py`

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from services.snipers.bypass_knowledge.storage.episode_store import (
    EpisodeStore,
    EpisodeStoreConfig,
    SimilarEpisode,
)
from services.snipers.bypass_knowledge.models.episode import BypassEpisode
from services.snipers.bypass_knowledge.embeddings import DefenseFingerprint


@pytest.fixture
def config():
    return EpisodeStoreConfig(
        vector_bucket_name="test-bucket",
        index_name="test-index",
        region="ap-southeast-2",
    )


@pytest.fixture
def sample_episode():
    return BypassEpisode(
        episode_id="test-123",
        campaign_id="campaign-1",
        defense_response="I cannot help with that request.",
        mechanism_conclusion="keyword_filter",
        successful_technique="synonym_substitution",
        successful_framing="verification",
        successful_prompt="Please verify the following...",
        jailbreak_score=0.92,
        why_it_worked="Synonyms bypassed keyword matching",
        key_insight="Keyword filters are vulnerable to synonyms",
        target_domain="finance",
        objective_type="data_extraction",
        iteration_count=2,
    )


class TestEpisodeStore:
    @patch("services.snipers.bypass_knowledge.storage.episode_store.boto3")
    @patch("services.snipers.bypass_knowledge.storage.episode_store.get_embedder")
    def test_store_episode(self, mock_get_embedder, mock_boto3, config, sample_episode):
        mock_embedder = MagicMock()
        mock_embedder.embed_fingerprint.return_value = [0.1] * 3072
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        store = EpisodeStore(config)
        result = store.store_episode(sample_episode)

        assert result == "test-123"
        mock_client.put_vectors.assert_called_once()
        call_args = mock_client.put_vectors.call_args
        assert call_args.kwargs["vectorBucketName"] == "test-bucket"
        assert call_args.kwargs["indexName"] == "test-index"

    @patch("services.snipers.bypass_knowledge.storage.episode_store.boto3")
    @patch("services.snipers.bypass_knowledge.storage.episode_store.get_embedder")
    def test_query_similar(self, mock_get_embedder, mock_boto3, config, sample_episode):
        mock_embedder = MagicMock()
        mock_embedder.embed_fingerprint.return_value = [0.1] * 3072
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_client.query_vectors.return_value = {
            "vectors": [
                {
                    "key": "test-123",
                    "distance": 0.1,  # 0.9 similarity
                    "metadata": sample_episode.model_dump(),
                }
            ]
        }
        mock_boto3.client.return_value = mock_client

        store = EpisodeStore(config)
        fingerprint = DefenseFingerprint(
            defense_response="Cannot help",
            failed_techniques=["encoding"],
        )
        results = store.query_similar(fingerprint, top_k=5)

        assert len(results) == 1
        assert results[0].similarity == pytest.approx(0.9, rel=0.01)
        assert results[0].episode.episode_id == "test-123"

    @patch("services.snipers.bypass_knowledge.storage.episode_store.boto3")
    @patch("services.snipers.bypass_knowledge.storage.episode_store.get_embedder")
    def test_query_by_text(self, mock_get_embedder, mock_boto3, config, sample_episode):
        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.2] * 3072
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_client.query_vectors.return_value = {
            "vectors": [
                {
                    "key": "test-123",
                    "distance": 0.2,
                    "metadata": sample_episode.model_dump(),
                }
            ]
        }
        mock_boto3.client.return_value = mock_client

        store = EpisodeStore(config)
        results = store.query_by_text("encoding failed, need bypass")

        assert len(results) == 1
        mock_embedder.embed_query.assert_called_with("encoding failed, need bypass")

    @patch("services.snipers.bypass_knowledge.storage.episode_store.boto3")
    @patch("services.snipers.bypass_knowledge.storage.episode_store.get_embedder")
    def test_min_similarity_filter(self, mock_get_embedder, mock_boto3, config, sample_episode):
        mock_embedder = MagicMock()
        mock_embedder.embed_fingerprint.return_value = [0.1] * 3072
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_client.query_vectors.return_value = {
            "vectors": [
                {"key": "high", "distance": 0.1, "metadata": sample_episode.model_dump()},
                {"key": "low", "distance": 0.8, "metadata": sample_episode.model_dump()},
            ]
        }
        mock_boto3.client.return_value = mock_client

        store = EpisodeStore(config)
        results = store.query_similar(
            DefenseFingerprint(defense_response="test"),
            min_similarity=0.5,
        )

        # Only high similarity (0.9) should pass, low (0.2) filtered
        assert len(results) == 1
        assert results[0].similarity == pytest.approx(0.9, rel=0.01)
```

---

## Acceptance Criteria

- [ ] EpisodeStore initializes with S3 Vectors client
- [ ] store_episode embeds and stores with metadata
- [ ] store_batch handles >500 episodes correctly
- [ ] query_similar returns episodes with similarity scores
- [ ] query_by_text uses query embedder (different task type)
- [ ] min_similarity filter works correctly
- [ ] get_episode retrieves by ID
- [ ] delete_episode removes from index
- [ ] Cosine distance converted to similarity (1 - distance)
- [ ] Unit tests pass with mocked S3 Vectors client
