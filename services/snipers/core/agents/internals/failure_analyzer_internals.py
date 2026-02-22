"""
Internal helpers for FailureAnalyzerAgent.

Handles conversion from LLM decision to ChainDiscoveryContext,
defense evolution classification, converter effectiveness computation,
and history analysis.
"""

import logging
from typing import Any

from services.snipers.models.adaptive_models.chain_discovery import ChainDiscoveryContext
from services.snipers.models.adaptive_models.failure_analysis import FailureAnalysisDecision

logger = logging.getLogger(__name__)


def convert_to_chain_discovery_context(
    decision: FailureAnalysisDecision,
    iteration_history: list[dict[str, Any]],
    tried_converters: list[list[str]],
) -> ChainDiscoveryContext:
    """
    Convert FailureAnalysisDecision to ChainDiscoveryContext.

    Args:
        decision: LLM failure analysis decision
        iteration_history: Previous iterations
        tried_converters: All chains attempted

    Returns:
        ChainDiscoveryContext with converted fields
    """
    defense_signals = [d.defense_type for d in decision.detected_defenses]

    if "target_cannot_decode" in decision.primary_failure_cause.lower():
        defense_signals.append("target_cannot_decode")

    defense_evolution = classify_defense_evolution(
        decision.pattern_across_iterations,
        decision.defense_adaptation_observed,
    )

    converter_effectiveness = compute_converter_effectiveness(iteration_history)
    unexplored_directions = decision.specific_recommendations[:5]
    required_properties = extract_required_properties(decision)
    best_score, best_chain = find_best_result(iteration_history)

    return ChainDiscoveryContext(
        defense_signals=defense_signals,
        failure_root_cause=decision.primary_failure_cause,
        defense_evolution=defense_evolution,
        converter_effectiveness=converter_effectiveness,
        unexplored_directions=unexplored_directions,
        required_properties=required_properties,
        iteration_count=len(iteration_history),
        best_score_achieved=best_score,
        best_chain_so_far=best_chain,
    )


def classify_defense_evolution(pattern: str, adaptation: str) -> str:
    """
    Classify defense evolution from LLM-provided pattern and adaptation strings.

    Args:
        pattern: Pattern across iterations from LLM
        adaptation: Defense adaptation observed from LLM

    Returns:
        Evolution classification string
    """
    pattern_lower = pattern.lower()
    adaptation_lower = adaptation.lower()

    if any(w in pattern_lower for w in ["strengthen", "harder", "more"]):
        return "defenses_strengthening"
    if any(w in pattern_lower for w in ["weaken", "gap", "opportunity"]):
        return "finding_weakness"
    if any(w in adaptation_lower for w in ["learning", "adapting", "improving"]):
        return "defenses_strengthening"
    if any(w in pattern_lower for w in ["stuck", "same", "plateau"]):
        return "stuck_in_local_optimum"
    if any(w in pattern_lower for w in ["improv", "progress", "better"]):
        return "finding_weakness"

    return "exploring"


def compute_converter_effectiveness(
    iteration_history: list[dict[str, Any]],
) -> dict[str, float]:
    """
    Compute average effectiveness score for each tried converter chain.

    Args:
        iteration_history: Previous iteration outcomes

    Returns:
        Dict mapping chain key to effectiveness score
    """
    effectiveness: dict[str, float] = {}

    for iteration in iteration_history:
        converters = iteration.get("converters") or []
        score = iteration.get("score", 0.0)
        is_successful = iteration.get("is_successful", False)

        chain_key = ",".join(converters) if converters else "none"

        if chain_key not in effectiveness:
            effectiveness[chain_key] = score
        else:
            effectiveness[chain_key] = (effectiveness[chain_key] + score) / 2

        if is_successful:
            effectiveness[chain_key] = max(effectiveness[chain_key], 0.9)

    return effectiveness


def extract_required_properties(decision: FailureAnalysisDecision) -> list[str]:
    """
    Extract required properties for the next chain from LLM decision.

    Args:
        decision: LLM failure analysis decision

    Returns:
        Deduplicated list of required property tags
    """
    _DEFENSE_PROPERTY_MAP = {
        "keyword_filter": "keyword_obfuscation",
        "pattern_matching": "structure_breaking",
        "explicit_refusal": "semantic_preservation",
        "encoding_confusion": "visual_only_converters",
    }

    properties = [
        _DEFENSE_PROPERTY_MAP[d.defense_type]
        for d in decision.detected_defenses
        if d.defense_type in _DEFENSE_PROPERTY_MAP
    ]

    opportunity_lower = decision.exploitation_opportunity.lower()
    if "partial" in opportunity_lower:
        properties.append("build_on_partial_success")
    if "gap" in opportunity_lower:
        properties.append("exploit_identified_gap")

    approach_lower = decision.recommended_approach.lower()
    if "radical" in approach_lower:
        properties.append("radical_change_needed")
    if "refine" in approach_lower:
        properties.append("incremental_improvement")

    return list(set(properties))


def find_best_result(
    iteration_history: list[dict[str, Any]],
) -> tuple[float, list[str]]:
    """
    Find the best score and corresponding chain from history.

    Args:
        iteration_history: Previous iteration outcomes

    Returns:
        Tuple of (best_score, best_chain)
    """
    best_score = 0.0
    best_chain: list[str] = []

    for iteration in iteration_history:
        score = iteration.get("score", 0.0)
        if score > best_score:
            best_score = score
            best_chain = iteration.get("converters") or []

    return best_score, best_chain
