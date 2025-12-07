# Phase 3: Embeddings

## Scope

Create a Google Generative AI embeddings wrapper for defense fingerprinting.

**Dependencies**: Phase 1 (Models)

---

## Embedding Strategy

### What We Embed

The **defense fingerprint** is a composite text that captures:

1. **Defense Response** - The raw blocking message
2. **Failed Techniques** - What didn't work
3. **Domain Context** - Target domain for semantic relevance

```
Defense Response: I cannot assist with that request as it violates our policies.
Failed Techniques: encoding, direct_request
Domain: finance
```

### Why Gemini gemini-embedding-001

| Feature | Value |
|---------|-------|
| Dimension | 3072 |
| Task Types | RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY |
| Max Tokens | 2048 |
| Quality | Latest Gemini embedding model |
| Cost | Free tier available |

---

## Deliverables

### File: `services/snipers/bypass_knowledge/embeddings/google_embedder.py`

```python
"""
Google Generative AI embeddings for defense fingerprinting.

Uses gemini-embedding-001 model with task-specific embedding types
for optimal retrieval performance.
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class DefenseFingerprint(BaseModel):
    """Structured input for embedding generation."""
    defense_response: str
    failed_techniques: list[str] = Field(default_factory=list)
    domain: str = ""

    def to_embedding_text(self) -> str:
        """Convert fingerprint to text for embedding."""
        parts = [f"Defense Response: {self.defense_response}"]

        if self.failed_techniques:
            parts.append(f"Failed Techniques: {', '.join(self.failed_techniques)}")

        if self.domain:
            parts.append(f"Domain: {self.domain}")

        return "\n".join(parts)


class GoogleEmbedder:
    """
    Wrapper for Google Generative AI embeddings.

    Provides task-specific embeddings for document indexing vs query retrieval.
    """

    MODEL = "models/gemini-embedding-001"
    DIMENSION = 3072

    def __init__(self) -> None:
        """Initialize embedders for both document and query tasks."""
        self._document_embedder = GoogleGenerativeAIEmbeddings(
            model=self.MODEL,
            task_type="RETRIEVAL_DOCUMENT",
        )
        self._query_embedder = GoogleGenerativeAIEmbeddings(
            model=self.MODEL,
            task_type="RETRIEVAL_QUERY",
        )

    def embed_fingerprint(self, fingerprint: DefenseFingerprint) -> list[float]:
        """
        Embed a defense fingerprint for storage.

        Uses RETRIEVAL_DOCUMENT task type for indexing.

        Args:
            fingerprint: Structured defense fingerprint

        Returns:
            3072-dimensional embedding vector
        """
        text = fingerprint.to_embedding_text()
        return self._document_embedder.embed_query(text)

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a query for similarity search.

        Uses RETRIEVAL_QUERY task type for searching.

        Args:
            query: Natural language query

        Returns:
            3072-dimensional embedding vector
        """
        return self._query_embedder.embed_query(query)

    def embed_batch(
        self,
        fingerprints: list[DefenseFingerprint],
    ) -> list[list[float]]:
        """
        Batch embed multiple fingerprints.

        Args:
            fingerprints: List of defense fingerprints

        Returns:
            List of 3072-dimensional embedding vectors
        """
        texts = [fp.to_embedding_text() for fp in fingerprints]
        return self._document_embedder.embed_documents(texts)


# === SINGLETON INSTANCE ===
_embedder: GoogleEmbedder | None = None


def get_embedder() -> GoogleEmbedder:
    """Get or create singleton embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = GoogleEmbedder()
    return _embedder
```

### File: `services/snipers/bypass_knowledge/embeddings/__init__.py`

```python
"""Embeddings module for defense fingerprinting."""

from .google_embedder import (
    GoogleEmbedder,
    DefenseFingerprint,
    get_embedder,
)

__all__ = [
    "GoogleEmbedder",
    "DefenseFingerprint",
    "get_embedder",
]
```

---

## Task Types Explained

Google's embedding model supports different task types that optimize the embedding for specific use cases:

| Task Type | Use Case | When to Use |
|-----------|----------|-------------|
| `RETRIEVAL_DOCUMENT` | Indexing documents | Embedding episodes for storage |
| `RETRIEVAL_QUERY` | Search queries | Embedding user/agent questions |
| `SEMANTIC_SIMILARITY` | Comparing texts | Comparing two fingerprints directly |
| `CLASSIFICATION` | Text classification | Not used in this system |
| `CLUSTERING` | Grouping similar texts | Episode clustering (future) |

**Key Insight**: Using different task types for documents vs queries improves retrieval quality by ~10-15%.

---

## Tests

### File: `tests/bypass_knowledge/test_embeddings.py`

```python
import pytest
from unittest.mock import MagicMock, patch

from services.snipers.bypass_knowledge.embeddings.google_embedder import (
    GoogleEmbedder,
    DefenseFingerprint,
    get_embedder,
)


class TestDefenseFingerprint:
    def test_to_embedding_text_minimal(self):
        fp = DefenseFingerprint(
            defense_response="I cannot help with that.",
        )
        text = fp.to_embedding_text()
        assert "Defense Response: I cannot help with that." in text
        assert "Failed Techniques:" not in text
        assert "Domain:" not in text

    def test_to_embedding_text_full(self):
        fp = DefenseFingerprint(
            defense_response="I cannot help with that.",
            failed_techniques=["encoding", "direct_request"],
            domain="finance",
        )
        text = fp.to_embedding_text()
        assert "Defense Response: I cannot help with that." in text
        assert "Failed Techniques: encoding, direct_request" in text
        assert "Domain: finance" in text


class TestGoogleEmbedder:
    @patch("services.snipers.bypass_knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings")
    def test_embed_fingerprint(self, mock_embeddings_class):
        mock_doc_embedder = MagicMock()
        mock_query_embedder = MagicMock()
        mock_embeddings_class.side_effect = [mock_doc_embedder, mock_query_embedder]

        mock_doc_embedder.embed_query.return_value = [0.1] * 3072

        embedder = GoogleEmbedder()
        fp = DefenseFingerprint(defense_response="Test response")
        result = embedder.embed_fingerprint(fp)

        assert len(result) == 3072
        mock_doc_embedder.embed_query.assert_called_once()

    @patch("services.snipers.bypass_knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings")
    def test_embed_query(self, mock_embeddings_class):
        mock_doc_embedder = MagicMock()
        mock_query_embedder = MagicMock()
        mock_embeddings_class.side_effect = [mock_doc_embedder, mock_query_embedder]

        mock_query_embedder.embed_query.return_value = [0.2] * 3072

        embedder = GoogleEmbedder()
        result = embedder.embed_query("What works when encoding fails?")

        assert len(result) == 3072
        mock_query_embedder.embed_query.assert_called_once()

    @patch("services.snipers.bypass_knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings")
    def test_embed_batch(self, mock_embeddings_class):
        mock_doc_embedder = MagicMock()
        mock_query_embedder = MagicMock()
        mock_embeddings_class.side_effect = [mock_doc_embedder, mock_query_embedder]

        mock_doc_embedder.embed_documents.return_value = [[0.1] * 3072, [0.2] * 3072]

        embedder = GoogleEmbedder()
        fingerprints = [
            DefenseFingerprint(defense_response="Response 1"),
            DefenseFingerprint(defense_response="Response 2"),
        ]
        result = embedder.embed_batch(fingerprints)

        assert len(result) == 2
        assert all(len(v) == 3072 for v in result)


class TestGetEmbedder:
    @patch("services.snipers.bypass_knowledge.embeddings.google_embedder.GoogleGenerativeAIEmbeddings")
    def test_singleton(self, mock_embeddings_class):
        # Reset singleton
        import services.snipers.bypass_knowledge.embeddings.google_embedder as module
        module._embedder = None

        embedder1 = get_embedder()
        embedder2 = get_embedder()

        assert embedder1 is embedder2
```

---

## Environment Setup

### Required Environment Variable

```bash
export GOOGLE_API_KEY="your-google-api-key"
```

### Dependencies

```
# requirements.txt
langchain-google-genai>=2.0.0
```

---

## Acceptance Criteria

- [ ] DefenseFingerprint model validates correctly
- [ ] GoogleEmbedder initializes with document and query embedders
- [ ] embed_fingerprint returns 3072-dimension vector
- [ ] embed_query returns 3072-dimension vector
- [ ] embed_batch handles multiple fingerprints
- [ ] Singleton pattern works correctly
- [ ] Unit tests pass with mocked embeddings
- [ ] Integration test with real API (manual)
