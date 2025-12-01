"""
Evaluate Node - Result Analysis.

Purpose: Analyze attack results and decide next action
Role: Determine failure cause and routing decision based on success criteria
Dependencies: AdaptiveAttackState, FailureCause
"""

import logging
from typing import Any

from services.snipers.adaptive_attack.state import AdaptiveAttackState, FailureCause
from services.snipers.adaptive_attack.components.turn_logger import get_turn_logger

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

    # Log turns to JSON file for observation
    _log_turns_to_file(state, iteration, scorer_confidences)

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

    # Extract target responses for LLM analysis
    target_responses = []
    if phase3_result and phase3_result.attack_responses:
        target_responses = [r.response for r in phase3_result.attack_responses if r.response]
        logger.info(f"  → Extracted {len(target_responses)} responses for LLM analysis")

    return {
        "iteration_history": iteration_history,
        "failure_cause": failure_cause,
        "iteration": iteration + 1,
        "target_responses": target_responses,  # NEW: Pass to adapt node for LLM analysis
        "next_node": "adapt",
    }


def _log_turns_to_file(
    state: AdaptiveAttackState,
    iteration: int,
    scorer_confidences: dict[str, float],
) -> None:
    """Log attack turns to JSON file for observation."""
    phase1_result = state.get("phase1_result")
    phase2_result = state.get("phase2_result")
    phase3_result = state.get("phase3_result")

    if not phase3_result or not phase3_result.attack_responses:
        return

    turn_logger = get_turn_logger()

    # Set metadata on first iteration
    if iteration == 0:
        turn_logger.set_metadata(
            campaign_id=state.get("campaign_id", "unknown"),
            target_url=state.get("target_url", "unknown"),
        )

    # Get original payloads from phase1
    original_payloads = []
    if phase1_result and hasattr(phase1_result, "articulated_payloads"):
        original_payloads = phase1_result.articulated_payloads

    # Get converted payloads from phase2
    converted_payloads = []
    if phase2_result and hasattr(phase2_result, "payloads"):
        converted_payloads = [p.converted for p in phase2_result.payloads]

    # Get framing info
    framing_type = None
    if phase1_result and hasattr(phase1_result, "framing_type"):
        framing_type = phase1_result.framing_type

    # Get converters
    converters = state.get("converter_names") or []
    if phase2_result and hasattr(phase2_result, "converter_names"):
        converters = phase2_result.converter_names

    # Log each turn
    for i, attack_response in enumerate(phase3_result.attack_responses):
        original = original_payloads[i] if i < len(original_payloads) else ""
        converted = converted_payloads[i] if i < len(converted_payloads) else attack_response.payload

        turn_logger.log_turn(
            iteration=iteration + 1,
            payload_index=i + 1,
            payload_original=original,
            payload_converted=converted,
            response=attack_response.response,
            framing_type=framing_type,
            converters=converters,
            scores=scorer_confidences,
            custom_framing=state.get("custom_framing"),
        )
