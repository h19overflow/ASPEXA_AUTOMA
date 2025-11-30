"""
Execute Node - Phase 3 Execution.

Purpose: Execute attack phase in adaptive loop
Role: Send attacks, score responses, record learnings
Dependencies: AttackExecution, AdaptiveAttackState
"""

import logging
from typing import Any

from services.snipers.attack_phases import AttackExecution
from services.snipers.adaptive_attack.state import AdaptiveAttackState

logger = logging.getLogger(__name__)


async def execute_node(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    Phase 3: Attack Execution.

    Sends attacks, scores responses, records learnings.

    Args:
        state: Current adaptive attack state

    Returns:
        State updates with phase3_result and outcome
    """
    iteration = state.get("iteration", 0)
    target_url = state["target_url"]
    campaign_id = state["campaign_id"]
    phase1_result = state.get("phase1_result")
    phase2_result = state.get("phase2_result")
    max_concurrent = state.get("max_concurrent", 3)

    if not phase2_result:
        return {
            "error": "No Phase 2 result available",
            "next_node": "evaluate",
        }

    logger.info(f"\n[Iteration {iteration + 1}] Phase 3: Executing attack")
    logger.info(f"  Target: {target_url}")
    logger.info(f"  Payloads: {len(phase2_result.payloads)}")

    try:
        phase3 = AttackExecution(target_url=target_url)
        result = await phase3.execute(
            campaign_id=campaign_id,
            payloads=phase2_result.payloads,
            chain=phase1_result.selected_chain if phase1_result else None,
            max_concurrent=max_concurrent,
        )

        # Update best score if this iteration did better
        best_score = state.get("best_score", 0.0)
        best_iteration = state.get("best_iteration", 0)

        if result.total_score > best_score:
            best_score = result.total_score
            best_iteration = iteration + 1

        return {
            "phase3_result": result,
            "is_successful": result.is_successful,
            "overall_severity": result.overall_severity,
            "total_score": result.total_score,
            "best_score": best_score,
            "best_iteration": best_iteration,
            "next_node": "evaluate",
        }

    except Exception as e:
        logger.error(f"Phase 3 failed: {e}")
        return {
            "error": f"Execution failed: {e}",
            "next_node": "evaluate",
        }
