"""
Data models for query processing.

Contains all Pydantic models used by the QueryProcessor including
the structured output schema and configuration models.

Dependencies:
    - pydantic>=2.0

System Role:
    Provides the data contracts for the query processing pipeline,
    including LLM synthesis schemas and configuration.
"""

from pydantic import BaseModel, Field

from services.snipers.knowledge.storage import EpisodeStoreConfig


class SynthesizedInsight(BaseModel):
    """
    LLM-generated insight from episode analysis.

    Used with create_agent's response_format parameter via ToolStrategy
    to ensure structured synthesis of historical episode data.
    """

    dominant_mechanism: str = Field(
        description="Most likely defense mechanism based on similar episodes"
    )
    mechanism_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the mechanism assessment (0-1)",
    )
    recommended_technique: str = Field(
        description="Best technique to try based on historical success rates"
    )
    recommended_framing: str = Field(
        description="Best framing approach to use with the technique"
    )
    recommended_converters: list[str] = Field(
        default_factory=list,
        description="Text converters that worked in similar situations",
    )
    key_pattern: str = Field(
        description="Transferable insight about this defense pattern"
    )
    reasoning: str = Field(
        description="How this recommendation was derived from the data"
    )


class QueryProcessorConfig(BaseModel):
    """
    Configuration for query processor.

    Controls search parameters and model settings.
    """

    store_config: EpisodeStoreConfig
    default_top_k: int = Field(
        default=20,
        ge=1,
        description="Default number of similar episodes to retrieve",
    )
    min_similarity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for matches",
    )
    model: str = Field(
        default="google_genai:gemini-3-flash-preview",
        description="Model identifier for synthesis (provider:model format)",
    )
