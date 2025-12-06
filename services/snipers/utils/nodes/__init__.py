"""Shared node implementations for attack phases.

NOTE: InputProcessingNode and PayloadArticulationNodePhase3 have been
consolidated into services.snipers.utils.prompt_articulation.ArticulationPhase
"""
from services.snipers.utils.nodes.converter_selection_node import ConverterSelectionNodePhase3
from services.snipers.utils.nodes.composite_scoring_node import CompositeScoringNodePhase34
from services.snipers.utils.nodes.learning_adaptation_node import LearningAdaptationNode

__all__ = [
    "ConverterSelectionNodePhase3",
    "CompositeScoringNodePhase34",
    "LearningAdaptationNode",
]
