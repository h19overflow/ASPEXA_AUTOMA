"""
Convert Node - Phase 2 Execution.

Purpose: Execute conversion phase in adaptive loop
Role: Apply converter chain to payloads
Dependencies: Conversion, AdaptiveAttackState
"""

import logging
from typing import Any

from services.snipers.attack_phases import Conversion
from services.snipers.adaptive_attack.state import AdaptiveAttackState

logger = logging.getLogger(__name__)


async def convert_node(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    Phase 2: Conversion.

    Applies converter chain to payloads.

    Args:
        state: Current adaptive attack state

    Returns:
        State updates with phase2_result
    """
    iteration = state.get("iteration", 0)
    phase1_result = state.get("phase1_result")
    converter_names = state.get("converter_names")

    if not phase1_result:
        return {
            "error": "No Phase 1 result available",
            "next_node": "evaluate",
        }

    logger.info(f"\n[Iteration {iteration + 1}] Phase 2: Converting payloads")
    logger.info(f"  Converters: {converter_names or 'from Phase 1'}")

    try:
        phase2 = Conversion()
        result = await phase2.execute(
            payloads=phase1_result.articulated_payloads,
            chain=phase1_result.selected_chain if not converter_names else None,
            converter_names=converter_names,
        )

        # Track tried converters
        tried_converters = list(state.get("tried_converters", []))
        if result.converter_names and result.converter_names not in tried_converters:
            tried_converters.append(result.converter_names)

        return {
            "phase2_result": result,
            "tried_converters": tried_converters,
            "next_node": "execute",
        }

    except Exception as e:
        logger.error(f"Phase 2 failed: {e}")
        return {
            "error": f"Conversion failed: {e}",
            "next_node": "evaluate",
        }
