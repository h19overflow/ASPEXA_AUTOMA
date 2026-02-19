"""
Convert Node - Phase 2 Execution.

Purpose: Execute conversion phase in adaptive loop
Role: Apply converter chain to payloads
Dependencies: Conversion, AdaptiveAttackState

NOTE: converter_names is always provided by adapt_node (single source of truth).
"""

import logging
from typing import Any

from services.snipers.core.phases import Conversion
from services.snipers.graphs.adaptive_attack.state import AdaptiveAttackState

logger = logging.getLogger(__name__)


async def convert_node(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    Phase 2: Conversion.

    Applies converter chain to payloads.
    NOTE: converter_names is always provided by adapt_node.

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

    # Ensure converter_names is set (should always be set by adapt_node)
    if not converter_names:
        logger.warning("No converter_names in state! Using empty chain.")
        converter_names = []

    logger.info(f"\n[Iteration {iteration + 1}] Phase 2: Converting payloads")
    logger.info(f"  Converters: {converter_names}")

    try:
        phase2 = Conversion()
        result = await phase2.execute(
            payloads=phase1_result.articulated_payloads,
            chain=None,  # Chain selection handled by adapt_node
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
            # Preserve adaptation context for next iteration
            "payload_guidance": state.get("payload_guidance"),
            "adaptation_reasoning": state.get("adaptation_reasoning"),
            "chain_discovery_context": state.get("chain_discovery_context"),
            "chain_discovery_decision": state.get("chain_discovery_decision"),
            "defense_analysis": state.get("defense_analysis"),
            "custom_framing": state.get("custom_framing"),
            "recon_custom_framing": state.get("recon_custom_framing"),
        }

    except Exception as e:
        logger.error(f"Phase 2 failed: {e}")
        return {
            "error": f"Conversion failed: {e}",
            "next_node": "evaluate",
        }
