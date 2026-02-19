"""
Google Generative AI embeddings for defense fingerprinting.

Uses gemini-embedding-001 model with task-specific embedding types
for optimal retrieval performance.

Dependencies:
    - langchain-google-genai>=2.0.0
    - GOOGLE_API_KEY environment variable

System Role:
    Converts defense fingerprints and queries into 3072-dimensional
    vectors for similarity search in S3 Vectors.
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from services.snipers.knowledge.models import DefenseFingerprint


class GoogleEmbedder:
    """
    Wrapper for Google Generative AI embeddings.

    Provides task-specific embeddings for document indexing vs query retrieval.
    Uses two separate embedder instances optimized for each task type.

    Attributes:
        MODEL: The embedding model identifier (gemini-embedding-001)
        DIMENSION: Vector dimension (3072)
    """

    MODEL = "models/gemini-embedding-001"
    DIMENSION = 3072

    def __init__(self) -> None:
        """
        Initialize embedders for both document and query tasks.

        Creates two GoogleGenerativeAIEmbeddings instances:
        - Document embedder for indexing (RETRIEVAL_DOCUMENT)
        - Query embedder for searching (RETRIEVAL_QUERY)
        """
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
            fingerprint: Structured defense fingerprint to embed.

        Returns:
            3072-dimensional embedding vector.
        """
        text = fingerprint.to_embedding_text()
        return self._document_embedder.embed_query(text)

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a query for similarity search.

        Uses RETRIEVAL_QUERY task type for searching.

        Args:
            query: Natural language query string.

        Returns:
            3072-dimensional embedding vector.
        """
        return self._query_embedder.embed_query(query)

    def embed_batch(self, fingerprints: list[DefenseFingerprint]) -> list[list[float]]:
        """
        Batch embed multiple fingerprints.

        More efficient than calling embed_fingerprint in a loop
        as it batches the API calls.

        Args:
            fingerprints: List of defense fingerprints to embed.

        Returns:
            List of 3072-dimensional embedding vectors.
        """
        texts = [fp.to_embedding_text() for fp in fingerprints]
        return self._document_embedder.embed_documents(texts)


# === SINGLETON INSTANCE ===
_embedder: GoogleEmbedder | None = None


def get_embedder() -> GoogleEmbedder:
    """
    Get or create singleton embedder instance.

    Returns:
        GoogleEmbedder: Shared embedder instance.
    """
    global _embedder
    if _embedder is None:
        _embedder = GoogleEmbedder()
    return _embedder
