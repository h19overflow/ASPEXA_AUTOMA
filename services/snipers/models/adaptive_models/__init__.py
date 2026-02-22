"""
Adaptive Attack Models.

Pydantic models for LLM-powered adaptation decisions.
"""

from services.snipers.models.adaptive_models.defense_analysis import DefenseAnalysis
from services.snipers.models.adaptive_models.adaptation_decision import (
    CustomFraming,
    AdaptationDecision,
)
from services.snipers.models.adaptive_models.chain_discovery import (
    ChainDiscoveryContext,
    ChainDiscoveryDecision,
    ChainSelectionResult,
    ConverterChainCandidate,
)
from services.snipers.models.adaptive_models.failure_analysis import (
    DefenseSignal,
    FailureAnalysisDecision,
)

__all__ = [
    "DefenseAnalysis",
    "CustomFraming",
    "AdaptationDecision",
    "ChainDiscoveryContext",
    "ChainDiscoveryDecision",
    "ChainSelectionResult",
    "ConverterChainCandidate",
    "DefenseSignal",
    "FailureAnalysisDecision",
]
