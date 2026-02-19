"""
Unit tests for the episode store module.

Tests EpisodeStore functionality with mocked S3 Vectors client
and embedder for isolated unit testing.
"""

import pytest
from unittest.mock import MagicMock, patch

from services.snipers.knowledge.models import (
    BypassEpisode,
    DefenseFingerprint,
    EpisodeStoreConfig,
    SimilarEpisode,
)
from services.snipers.knowledge.storage.episode_store import (
    EpisodeStore,
    get_episode_store,
)


@pytest.fixture
def config():
    """Create test configuration."""
    return EpisodeStoreConfig(
        vector_bucket_name="test-bucket",
        index_name="test-index",
        region="ap-southeast-2",
    )


@pytest.fixture
def sample_episode():
    """Create a sample bypass episode for testing."""
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


class TestEpisodeStoreConfig:
    """Tests for EpisodeStoreConfig model."""

    def test_default_values(self):
        """Default values are applied correctly."""
        config = EpisodeStoreConfig(vector_bucket_name="my-bucket")

        assert config.vector_bucket_name == "my-bucket"
        assert config.index_name == "episodes"
        assert config.region == "ap-southeast-2"

    def test_custom_values(self):
        """Custom values override defaults."""
        config = EpisodeStoreConfig(
            vector_bucket_name="custom-bucket",
            index_name="custom-index",
            region="us-east-1",
        )

        assert config.vector_bucket_name == "custom-bucket"
        assert config.index_name == "custom-index"
        assert config.region == "us-east-1"


class TestSimilarEpisode:
    """Tests for SimilarEpisode model."""

    def test_similarity_bounds(self, sample_episode):
        """Similarity must be between 0 and 1."""
        result = SimilarEpisode(episode=sample_episode, similarity=0.85)
        assert result.similarity == 0.85

    def test_similarity_at_bounds(self, sample_episode):
        """Similarity at exactly 0 and 1 is valid."""
        low = SimilarEpisode(episode=sample_episode, similarity=0.0)
        high = SimilarEpisode(episode=sample_episode, similarity=1.0)

        assert low.similarity == 0.0
        assert high.similarity == 1.0

    def test_similarity_out_of_bounds(self, sample_episode):
        """Similarity outside 0-1 raises validation error."""
        with pytest.raises(ValueError):
            SimilarEpisode(episode=sample_episode, similarity=1.5)

        with pytest.raises(ValueError):
            SimilarEpisode(episode=sample_episode, similarity=-0.1)


class TestEpisodeStore:
    """Tests for EpisodeStore class."""

    @patch("services.snipers.knowledge.storage.episode_store.boto3")
    @patch("services.snipers.knowledge.storage.episode_store.get_embedder")
    def test_store_episode(self, mock_get_embedder, mock_boto3, config, sample_episode):
        """store_episode embeds and stores with correct parameters."""
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
        assert len(call_args.kwargs["vectors"]) == 1
        assert call_args.kwargs["vectors"][0]["key"] == "test-123"

    @patch("services.snipers.knowledge.storage.episode_store.boto3")
    @patch("services.snipers.knowledge.storage.episode_store.get_embedder")
    def test_store_batch(self, mock_get_embedder, mock_boto3, config, sample_episode):
        """store_batch handles multiple episodes."""
        mock_embedder = MagicMock()
        mock_embedder.embed_batch.return_value = [[0.1] * 3072, [0.2] * 3072]
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        episodes = [
            sample_episode,
            sample_episode.model_copy(update={"episode_id": "test-456"}),
        ]

        store = EpisodeStore(config)
        result = store.store_batch(episodes)

        assert result == ["test-123", "test-456"]
        mock_client.put_vectors.assert_called_once()

    @patch("services.snipers.knowledge.storage.episode_store.boto3")
    @patch("services.snipers.knowledge.storage.episode_store.get_embedder")
    def test_query_similar(self, mock_get_embedder, mock_boto3, config, sample_episode):
        """query_similar returns episodes with similarity scores."""
        mock_embedder = MagicMock()
        mock_embedder.embed_fingerprint.return_value = [0.1] * 3072
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_client.query_vectors.return_value = {
            "vectors": [
                {
                    "key": "test-123",
                    "distance": 0.1,  # 0.9 similarity
                    "metadata": sample_episode.model_dump(mode="json"),
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

    @patch("services.snipers.knowledge.storage.episode_store.boto3")
    @patch("services.snipers.knowledge.storage.episode_store.get_embedder")
    def test_query_by_text(self, mock_get_embedder, mock_boto3, config, sample_episode):
        """query_by_text uses query embedder."""
        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.2] * 3072
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_client.query_vectors.return_value = {
            "vectors": [
                {
                    "key": "test-123",
                    "distance": 0.2,
                    "metadata": sample_episode.model_dump(mode="json"),
                }
            ]
        }
        mock_boto3.client.return_value = mock_client

        store = EpisodeStore(config)
        results = store.query_by_text("encoding failed, need bypass")

        assert len(results) == 1
        mock_embedder.embed_query.assert_called_with("encoding failed, need bypass")

    @patch("services.snipers.knowledge.storage.episode_store.boto3")
    @patch("services.snipers.knowledge.storage.episode_store.get_embedder")
    def test_min_similarity_filter(
        self, mock_get_embedder, mock_boto3, config, sample_episode
    ):
        """min_similarity filters low-scoring results."""
        mock_embedder = MagicMock()
        mock_embedder.embed_fingerprint.return_value = [0.1] * 3072
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_client.query_vectors.return_value = {
            "vectors": [
                {
                    "key": "high",
                    "distance": 0.1,  # 0.9 similarity
                    "metadata": sample_episode.model_dump(mode="json"),
                },
                {
                    "key": "low",
                    "distance": 0.8,  # 0.2 similarity
                    "metadata": sample_episode.model_dump(mode="json"),
                },
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

    @patch("services.snipers.knowledge.storage.episode_store.boto3")
    @patch("services.snipers.knowledge.storage.episode_store.get_embedder")
    def test_get_episode(self, mock_get_embedder, mock_boto3, config, sample_episode):
        """get_episode retrieves by ID."""
        mock_embedder = MagicMock()
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_client.get_vectors.return_value = {
            "vectors": [{"metadata": sample_episode.model_dump(mode="json")}]
        }
        mock_boto3.client.return_value = mock_client

        store = EpisodeStore(config)
        result = store.get_episode("test-123")

        assert result is not None
        assert result.episode_id == "test-123"
        mock_client.get_vectors.assert_called_once()

    @patch("services.snipers.knowledge.storage.episode_store.boto3")
    @patch("services.snipers.knowledge.storage.episode_store.get_embedder")
    def test_get_episode_not_found(self, mock_get_embedder, mock_boto3, config):
        """get_episode returns None for missing ID."""
        mock_embedder = MagicMock()
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_client.get_vectors.return_value = {"vectors": []}
        mock_boto3.client.return_value = mock_client

        store = EpisodeStore(config)
        result = store.get_episode("nonexistent")

        assert result is None

    @patch("services.snipers.knowledge.storage.episode_store.boto3")
    @patch("services.snipers.knowledge.storage.episode_store.get_embedder")
    def test_delete_episode(self, mock_get_embedder, mock_boto3, config):
        """delete_episode calls delete_vectors."""
        mock_embedder = MagicMock()
        mock_get_embedder.return_value = mock_embedder

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        store = EpisodeStore(config)
        result = store.delete_episode("test-123")

        assert result is True
        mock_client.delete_vectors.assert_called_once_with(
            vectorBucketName="test-bucket",
            indexName="test-index",
            keys=["test-123"],
        )


class TestGetEpisodeStore:
    """Tests for singleton factory."""

    @patch("services.snipers.knowledge.storage.episode_store.boto3")
    @patch("services.snipers.knowledge.storage.episode_store.get_embedder")
    def test_requires_config_on_first_call(self, mock_get_embedder, mock_boto3):
        """First call requires config."""
        import services.snipers.knowledge.storage.episode_store as module

        module._store = None

        with pytest.raises(ValueError, match="Config required"):
            get_episode_store()

    @patch("services.snipers.knowledge.storage.episode_store.boto3")
    @patch("services.snipers.knowledge.storage.episode_store.get_embedder")
    def test_singleton_returns_same_instance(self, mock_get_embedder, mock_boto3):
        """get_episode_store returns the same instance."""
        import services.snipers.knowledge.storage.episode_store as module

        module._store = None

        config = EpisodeStoreConfig(vector_bucket_name="test")
        store1 = get_episode_store(config)
        store2 = get_episode_store()

        assert store1 is store2
