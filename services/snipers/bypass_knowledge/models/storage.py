"""
Storage-related models for episode persistence.

Defines configuration and response models used by the storage layer.
"""

from pydantic import BaseModel, Field

from .episode import BypassEpisode


class SimilarEpisode(BaseModel):
    """
    Episode with similarity score from vector search.

    Wraps a BypassEpisode with its cosine similarity score
    from the vector query operation.
    """

    episode: BypassEpisode
    similarity: float = Field(ge=0.0, le=1.0, description="Cosine similarity score")


class EpisodeStoreConfig(BaseModel):
    """
    Configuration for episode storage.

    Loaded from environment variables via pydantic-settings.
    """

    vector_bucket_name: str = Field(description="S3 Vectors bucket name")
    index_name: str = Field(default="episodes", description="Vector index name")
    region: str = Field(default="ap-southeast-2", description="AWS region")
