"""
Snipers Shared Utilities.

Consolidates all reusable components:
- nodes: Shared node implementations for attack phases
- scoring: LLM-based attack success scorers
- converters: Payload transformation system
- prompt_articulation: Payload generation framework
- persistence: S3 integration layer
- pyrit: PyRIT initialization and bridging
"""

from services.snipers.utils.llm_provider import get_default_agent
from services.snipers.utils.persistence.s3_adapter import (
    persist_exploit_result,
    load_campaign_intel,
)

__all__ = [
    "get_default_agent",
    "persist_exploit_result",
    "load_campaign_intel",
]
