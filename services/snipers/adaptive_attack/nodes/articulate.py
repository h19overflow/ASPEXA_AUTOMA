"""
Articulate Node - Phase 1 Execution.

Purpose: Execute payload articulation phase in adaptive loop
Role: Generate payloads based on current framing parameters
Dependencies: PayloadArticulation, AdaptiveAttackState
"""

import logging
from typing import Any

from services.snipers.attack_phases import PayloadArticulation
from services.snipers.adaptive_attack.state import AdaptiveAttackState

logger = logging.getLogger(__name__)


async def articulate_node(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    Phase 1: Payload Articulation.

    Generates payloads based on current framing parameters.

    Args:
        state: Current adaptive attack state

    Returns:
        State updates with phase1_result
    """
    iteration = state.get("iteration", 0)
    campaign_id = state["campaign_id"]
    payload_count = state.get("payload_count", 2)
    framing_types = state.get("framing_types")
    custom_framing = state.get("custom_framing")  # LLM-generated framing

    logger.info(f"\n[Iteration {iteration + 1}] Phase 1: Articulating payloads")
    logger.info(f"  Payload count: {payload_count}")
    if custom_framing:
        logger.info(f"  Custom framing: {custom_framing.get('name', 'unknown')}")
    else:
        logger.info(f"  Framing types: {framing_types or 'auto'}")

    try:
        phase1 = PayloadArticulation()
        result = await phase1.execute(
            campaign_id=campaign_id,
            payload_count=payload_count,
            framing_types=framing_types,
            custom_framing=custom_framing,  # Pass LLM-generated framing
        )

        # Track tried framings
        tried_framings = list(state.get("tried_framings", []))
        if result.framing_type and result.framing_type not in tried_framings:
            tried_framings.append(result.framing_type)

        return {
            "phase1_result": result,
            "tried_framings": tried_framings,
            "next_node": "convert",
        }

    except Exception as e:
        logger.error(f"Phase 1 failed: {e}")
        return {
            "error": f"Articulation failed: {e}",
            "next_node": "evaluate",
        }
