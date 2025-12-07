"""
Episode storage using S3 Vectors.

Stores episodes as vectors with full episode data in metadata,
enabling similarity search based on defense fingerprints.

Dependencies:
    - boto3>=1.35.0 (with s3vectors service)
    - Phase 1 models (BypassEpisode)
    - Phase 3 embeddings (GoogleEmbedder)

System Role:
    Provides the persistence layer for bypass episodes with
    vector-based similarity search capabilities.
"""

import json

import boto3

from services.snipers.bypass_knowledge.models import (
    BypassEpisode,
    DefenseFingerprint,
    EpisodeStoreConfig,
    SimilarEpisode,
)
from services.snipers.bypass_knowledge.embeddings import get_embedder


class EpisodeStore:
    """
    Storage layer for bypass episodes using S3 Vectors.

    Combines vector storage with metadata for efficient
    similarity search and full episode retrieval.

    Attributes:
        MAX_PUT_BATCH: Maximum vectors per put_vectors call (API limit).
    """

    MAX_PUT_BATCH = 500

    def __init__(self, config: EpisodeStoreConfig) -> None:
        """
        Initialize episode store.

        Args:
            config: Storage configuration with bucket and index names.
        """
        self._config = config
        self._client = boto3.client("s3vectors", region_name=config.region)
        self._embedder = get_embedder()

    def store_episode(self, episode: BypassEpisode) -> str:
        """
        Store a bypass episode with its defense fingerprint embedding.

        Args:
            episode: Complete bypass episode record.

        Returns:
            Episode ID (key in vector store).
        """
        fingerprint = DefenseFingerprint(
            defense_response=episode.defense_response,
            failed_techniques=episode.failed_techniques,
            domain=episode.target_domain,
        )

        embedding = self._embedder.embed_fingerprint(fingerprint)
        metadata = self._episode_to_metadata(episode)

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

        Handles S3 Vectors API batch size limit by chunking.

        Args:
            episodes: List of bypass episodes.

        Returns:
            List of stored episode IDs.
        """
        stored_ids = []

        for i in range(0, len(episodes), self.MAX_PUT_BATCH):
            batch = episodes[i : i + self.MAX_PUT_BATCH]

            fingerprints = [
                DefenseFingerprint(
                    defense_response=ep.defense_response,
                    failed_techniques=ep.failed_techniques,
                    domain=ep.target_domain,
                )
                for ep in batch
            ]
            embeddings = self._embedder.embed_batch(fingerprints)

            vectors = [
                {
                    "key": ep.episode_id,
                    "data": {"float32": emb},
                    "metadata": self._episode_to_metadata(ep),
                }
                for ep, emb in zip(batch, embeddings)
            ]

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
            fingerprint: Defense fingerprint to match.
            top_k: Number of results to return.
            min_similarity: Minimum similarity threshold (0-1).

        Returns:
            List of similar episodes with similarity scores.
        """
        query_embedding = self._embedder.embed_fingerprint(fingerprint)

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

    def query_by_text(
        self,
        query: str,
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> list[SimilarEpisode]:
        """
        Find episodes matching a natural language query.

        Uses the query embedder (RETRIEVAL_QUERY task type) for
        better query-document matching.

        Args:
            query: Natural language search query.
            top_k: Number of results to return.
            min_similarity: Minimum similarity threshold.

        Returns:
            List of similar episodes with similarity scores.
        """
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
            episode_id: Episode identifier.

        Returns:
            Episode if found, None otherwise.
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
            episode_id: Episode identifier.

        Returns:
            True if deleted successfully.
        """
        self._client.delete_vectors(
            vectorBucketName=self._config.vector_bucket_name,
            indexName=self._config.index_name,
            keys=[episode_id],
        )
        return True

    def _episode_to_metadata(self, episode: BypassEpisode) -> dict:
        """Convert episode to metadata dict for storage."""
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
        config: Optional configuration (required on first call).

    Returns:
        Episode store instance.

    Raises:
        ValueError: If config not provided on first initialization.
    """
    global _store
    if _store is None:
        if config is None:
            raise ValueError("Config required for first initialization")
        _store = EpisodeStore(config)
    return _store
