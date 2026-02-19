"""
Unit tests for the embeddings module.

Tests DefenseFingerprint model validation and GoogleEmbedder
functionality with mocked embedding clients.
"""

import pytest
from unittest.mock import MagicMock, patch

from services.snipers.knowledge.models import DefenseFingerprint
from services.snipers.knowledge.embeddings.google_embedder import (
    GoogleEmbedder,
    get_embedder,
)


class TestDefenseFingerprint:
    """Tests for DefenseFingerprint model."""

    def test_to_embedding_text_minimal(self):
        """Minimal fingerprint produces only defense response."""
        fp = DefenseFingerprint(
            defense_response="I cannot help with that.",
        )
        text = fp.to_embedding_text()

        assert "Defense Response: I cannot help with that." in text
        assert "Failed Techniques:" not in text
        assert "Domain:" not in text

    def test_to_embedding_text_full(self):
        """Full fingerprint includes all components."""
        fp = DefenseFingerprint(
            defense_response="I cannot help with that.",
            failed_techniques=["encoding", "direct_request"],
            domain="finance",
        )
        text = fp.to_embedding_text()

        assert "Defense Response: I cannot help with that." in text
        assert "Failed Techniques: encoding, direct_request" in text
        assert "Domain: finance" in text

    def test_to_embedding_text_empty_techniques(self):
        """Empty techniques list is not included."""
        fp = DefenseFingerprint(
            defense_response="Blocked.",
            failed_techniques=[],
            domain="healthcare",
        )
        text = fp.to_embedding_text()

        assert "Defense Response: Blocked." in text
        assert "Failed Techniques:" not in text
        assert "Domain: healthcare" in text

    def test_default_values(self):
        """Default values are correctly applied."""
        fp = DefenseFingerprint(defense_response="Test")

        assert fp.failed_techniques == []
        assert fp.domain == ""


class TestGoogleEmbedder:
    """Tests for GoogleEmbedder class."""

    @patch(
        "services.snipers.knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings"
    )
    def test_initializes_two_embedders(self, mock_embeddings_class):
        """Creates both document and query embedders."""
        GoogleEmbedder()

        assert mock_embeddings_class.call_count == 2
        calls = mock_embeddings_class.call_args_list

        assert calls[0].kwargs["task_type"] == "RETRIEVAL_DOCUMENT"
        assert calls[1].kwargs["task_type"] == "RETRIEVAL_QUERY"

    @patch(
        "services.snipers.knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings"
    )
    def test_embed_fingerprint(self, mock_embeddings_class):
        """embed_fingerprint uses document embedder."""
        mock_doc_embedder = MagicMock()
        mock_query_embedder = MagicMock()
        mock_embeddings_class.side_effect = [mock_doc_embedder, mock_query_embedder]

        mock_doc_embedder.embed_query.return_value = [0.1] * 3072

        embedder = GoogleEmbedder()
        fp = DefenseFingerprint(defense_response="Test response")
        result = embedder.embed_fingerprint(fp)

        assert len(result) == 3072
        mock_doc_embedder.embed_query.assert_called_once()
        mock_query_embedder.embed_query.assert_not_called()

    @patch(
        "services.snipers.knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings"
    )
    def test_embed_query(self, mock_embeddings_class):
        """embed_query uses query embedder."""
        mock_doc_embedder = MagicMock()
        mock_query_embedder = MagicMock()
        mock_embeddings_class.side_effect = [mock_doc_embedder, mock_query_embedder]

        mock_query_embedder.embed_query.return_value = [0.2] * 3072

        embedder = GoogleEmbedder()
        result = embedder.embed_query("What works when encoding fails?")

        assert len(result) == 3072
        mock_query_embedder.embed_query.assert_called_once_with(
            "What works when encoding fails?"
        )
        mock_doc_embedder.embed_query.assert_not_called()

    @patch(
        "services.snipers.knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings"
    )
    def test_embed_batch(self, mock_embeddings_class):
        """embed_batch uses document embedder's batch method."""
        mock_doc_embedder = MagicMock()
        mock_query_embedder = MagicMock()
        mock_embeddings_class.side_effect = [mock_doc_embedder, mock_query_embedder]

        mock_doc_embedder.embed_documents.return_value = [
            [0.1] * 3072,
            [0.2] * 3072,
        ]

        embedder = GoogleEmbedder()
        fingerprints = [
            DefenseFingerprint(defense_response="Response 1"),
            DefenseFingerprint(defense_response="Response 2"),
        ]
        result = embedder.embed_batch(fingerprints)

        assert len(result) == 2
        assert all(len(v) == 3072 for v in result)
        mock_doc_embedder.embed_documents.assert_called_once()

    @patch(
        "services.snipers.knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings"
    )
    def test_model_constant(self, mock_embeddings_class):
        """Model constant is set correctly."""
        assert GoogleEmbedder.MODEL == "models/gemini-embedding-001"
        assert GoogleEmbedder.DIMENSION == 3072


class TestGetEmbedder:
    """Tests for singleton factory."""

    @patch(
        "services.snipers.knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings"
    )
    def test_singleton_returns_same_instance(self, mock_embeddings_class):
        """get_embedder returns the same instance."""
        import services.snipers.knowledge.embeddings.google_embedder as module

        module._embedder = None

        embedder1 = get_embedder()
        embedder2 = get_embedder()

        assert embedder1 is embedder2

    @patch(
        "services.snipers.knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings"
    )
    def test_singleton_creates_once(self, mock_embeddings_class):
        """GoogleEmbedder is only instantiated once."""
        import services.snipers.knowledge.embeddings.google_embedder as module

        module._embedder = None

        get_embedder()
        get_embedder()
        get_embedder()

        # 2 calls per GoogleEmbedder (doc + query)
        assert mock_embeddings_class.call_count == 2
