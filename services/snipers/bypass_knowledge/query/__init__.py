"""
Query module for bypass knowledge retrieval.

Provides the QueryProcessor class that transforms natural language
queries into actionable insights by searching similar episodes
and synthesizing recommendations. Uses LangChain v1 create_agent
with ToolStrategy for structured synthesis.

Structure:
    - query_models.py: Pydantic models (SynthesizedInsight, QueryProcessorConfig)
    - query_prompt.py: System prompt for synthesis agent
    - query_processor.py: Main QueryProcessor class
"""

from .query_models import QueryProcessorConfig, SynthesizedInsight
from .query_prompt import SYNTHESIS_SYSTEM_PROMPT
from .query_processor import QueryProcessor, get_query_processor

__all__ = [
    # Models
    "QueryProcessorConfig",
    "SynthesizedInsight",
    # Prompt
    "SYNTHESIS_SYSTEM_PROMPT",
    # Main class
    "QueryProcessor",
    "get_query_processor",
]
