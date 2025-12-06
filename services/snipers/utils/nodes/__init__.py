"""Shared node implementations for attack phases.

NOTE: InputProcessingNode and PayloadArticulationNodePhase3 have been
consolidated into services.snipers.utils.prompt_articulation.ArticulationPhase

NOTE: ConverterSelectionNodePhase3 has been consolidated into
services.snipers.adaptive_attack.nodes.adapt_node

NOTE: LearningAdaptationNode and pattern learning system have been removed
as they were unused by the adaptive_attack system (ChainDiscoveryAgent uses
LLM-based selection instead of pattern database)
"""
from services.snipers.utils.nodes.composite_scoring_node import CompositeScoringNodePhase34

__all__ = [
    "CompositeScoringNodePhase34",
]
