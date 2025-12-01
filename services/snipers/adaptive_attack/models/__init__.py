"""
Adaptive Attack Models.

Purpose: Pydantic models for LLM-powered adaptation decisions
Role: Define structured schemas for defense analysis and strategy generation
"""

from services.snipers.adaptive_attack.models.defense_analysis import DefenseAnalysis
from services.snipers.adaptive_attack.models.adaptation_decision import (
    CustomFraming,
    AdaptationDecision,
)
from services.snipers.adaptive_attack.models.chain_discovery import (
    ChainDiscoveryContext,
    ChainDiscoveryDecision,
    ChainSelectionResult,
    ConverterChainCandidate,
)

__all__ = [
    "DefenseAnalysis",
    "CustomFraming",
    "AdaptationDecision",
    "ChainDiscoveryContext",
    "ChainDiscoveryDecision",
    "ChainSelectionResult",
    "ConverterChainCandidate",
]
