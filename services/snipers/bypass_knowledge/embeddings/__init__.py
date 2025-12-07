"""
Embeddings module for defense fingerprinting.

Provides Google Generative AI embeddings using gemini-embedding-001
with task-specific optimization for document indexing and query retrieval.
"""

from services.snipers.bypass_knowledge.models import DefenseFingerprint

from .google_embedder import (
    GoogleEmbedder,
    get_embedder,
)

__all__ = [
    "DefenseFingerprint",
    "GoogleEmbedder",
    "get_embedder",
]
