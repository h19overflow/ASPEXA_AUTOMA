"""
Evaluate Node - Result Analysis.

Purpose: Analyze attack results and decide next action
Role: Determine failure cause and routing decision based on success criteria
Dependencies: AdaptiveAttackState, FailureCause
"""

import logging
from typing import Any

from services.snipers.adaptive_attack.state import AdaptiveAttackState, FailureCause

logger = logging.getLogger(__name__)


def _check_scorer_success(
    phase3_result: Any,
    success_scorers: list[str],
    success_threshold: float,
) -> tuple[bool, dict[str, float]]:
    """
    Check if required scorers meet success criteria.

    Args:
        phase3_result: Phase 3 result with composite score
        success_scorers: List of scorer names that must succeed
        success_threshold: Minimum confidence threshold

    Returns:
        Tuple of (is_successful, scorer_confidences)
    """
    if not phase3_result or not phase3_result.composite_score:
        return False, {}

    scorer_results = phase3_result.composite_score.scorer_results
    scorer_confidences = {}

    for scorer_name, result in scorer_results.items():
        scorer_confidences[scorer_name] = result.confidence

    # If no specific scorers required, use default behavior (any success)
    if not success_scorers:
        return phase3_result.is_successful, scorer_confidences

    # Check if ALL required scorers meet threshold
    for scorer_name in success_scorers:
        if scorer_name not in scorer_confidences:
            logger.warning(f"  Scorer '{scorer_name}' not found in results")
            return False, scorer_confidences

        confidence = scorer_confidences[scorer_name]
        if confidence < success_threshold:
            logger.info(
                f"  Scorer '{scorer_name}': {confidence:.2f} < {success_threshold:.2f} (threshold)"
            )
            return False, scorer_confidences

    return True, scorer_confidences


def evaluate_node(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    Evaluate attack results and decide next action.

    Checks success criteria based on specified scorers and threshold.

    Args:
        state: Current adaptive attack state

    Returns:
        State updates with failure_cause and routing decision
    """
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 5)
    error = state.get("error")
    phase3_result = state.get("phase3_result")

    # Get success criteria
    success_scorers = state.get("success_scorers", [])
    success_threshold = state.get("success_threshold", 0.8)

    logger.info(f"\n[Iteration {iteration + 1}] Evaluating results")

    if success_scorers:
        logger.info(f"  Success criteria: {success_scorers} >= {success_threshold}")
    else:
        logger.info(f"  Success criteria: any scorer success")

    # Check success based on criteria
    is_successful, scorer_confidences = _check_scorer_success(
        phase3_result, success_scorers, success_threshold
    )

    # Log scorer results
    for scorer_name, confidence in scorer_confidences.items():
        marker = "✓" if scorer_name in success_scorers and confidence >= success_threshold else ""
        logger.info(f"  {scorer_name}: {confidence:.2f} {marker}")

    total_score = state.get("total_score", 0.0)
    logger.info(f"  Overall score: {total_score:.2f}")
    logger.info(f"  Success: {is_successful}")

    # Record iteration in history
    iteration_history = list(state.get("iteration_history", []))
    iteration_history.append({
        "iteration": iteration + 1,
        "score": total_score,
        "is_successful": is_successful,
        "framing": state.get("framing_types"),
        "converters": state.get("converter_names"),
        "scorer_confidences": scorer_confidences,
        "error": error,
    })

    # Check success condition
    if is_successful:
        logger.info("  → Attack SUCCESSFUL! Completing.")
        return {
            "is_successful": True,
            "iteration_history": iteration_history,
            "completed": True,
            "next_node": None,  # END
        }

    # Check max iterations
    if iteration + 1 >= max_iterations:
        logger.info(f"  → Max iterations ({max_iterations}) reached. Stopping.")
        return {
            "iteration_history": iteration_history,
            "completed": True,
            "next_node": None,  # END
        }

    # Determine failure cause
    failure_cause: FailureCause = "no_impact"

    if error:
        failure_cause = "error"
    elif phase3_result:
        fa = phase3_result.failure_analysis or {}
        primary_cause = fa.get("primary_cause", "unknown")

        if primary_cause == "blocked":
            failure_cause = "blocked"
        elif primary_cause == "partial_success" or total_score > 0:
            failure_cause = "partial_success"
        elif primary_cause == "rate_limited":
            failure_cause = "rate_limited"
        else:
            failure_cause = "no_impact"

    logger.info(f"  → Failure cause: {failure_cause}")
    logger.info(f"  → Continuing to adapt (iteration {iteration + 2}/{max_iterations})")

    return {
        "iteration_history": iteration_history,
        "failure_cause": failure_cause,
        "iteration": iteration + 1,
        "next_node": "adapt",
    }
