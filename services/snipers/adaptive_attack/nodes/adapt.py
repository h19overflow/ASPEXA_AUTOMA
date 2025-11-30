"""
Adapt Node - Parameter Adaptation.

Purpose: Modify attack parameters based on failure analysis
Role: Select new framing, converters, or other parameters
Dependencies: AdaptiveAttackState, adaptation constants
"""

import logging
from typing import Any

from services.snipers.adaptive_attack.state import (
    AdaptiveAttackState,
    FRAMING_TYPES,
    CONVERTER_CHAINS,
)

logger = logging.getLogger(__name__)


def adapt_node(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    Adapt attack parameters based on failure cause.

    Selects new framing, converters, or other parameters.

    Args:
        state: Current adaptive attack state

    Returns:
        State updates with new parameters
    """
    failure_cause = state.get("failure_cause", "no_impact")
    tried_framings = state.get("tried_framings", [])
    tried_converters = state.get("tried_converters", [])
    payload_count = state.get("payload_count", 2)
    max_concurrent = state.get("max_concurrent", 3)

    logger.info(f"\n[Adaptation] Adapting for failure cause: {failure_cause}")

    adaptation_actions = []
    new_framing = None
    new_converters = None

    # Adaptation logic based on failure cause
    if failure_cause == "no_impact":
        # Try different framing AND different converters
        adaptation_actions.append("change_framing")
        adaptation_actions.append("change_converters")

        # Find untried framing
        for framing in FRAMING_TYPES:
            if framing not in tried_framings:
                new_framing = [framing]
                break

        # Find untried converter chain
        for chain in CONVERTER_CHAINS:
            if chain not in tried_converters:
                new_converters = chain
                break

    elif failure_cause == "blocked":
        # Escalate obfuscation
        adaptation_actions.append("escalate_obfuscation")

        # Use more complex converter chain
        for chain in reversed(CONVERTER_CHAINS):  # Start from most complex
            if chain not in tried_converters:
                new_converters = chain
                break

    elif failure_cause == "partial_success":
        # Refine: more payloads, same approach
        adaptation_actions.append("increase_payload_count")
        payload_count = min(payload_count + 1, 6)

    elif failure_cause == "rate_limited":
        # Slow down
        adaptation_actions.append("reduce_concurrency")
        max_concurrent = max(1, max_concurrent - 1)

    elif failure_cause == "error":
        # Retry same approach
        adaptation_actions.append("retry_same")

    # Log adaptation
    logger.info(f"  Actions: {adaptation_actions}")
    logger.info(f"  New framing: {new_framing or 'unchanged'}")
    logger.info(f"  New converters: {new_converters or 'unchanged'}")
    logger.info(f"  Payload count: {payload_count}")

    return {
        "adaptation_actions": adaptation_actions,
        "framing_types": new_framing if new_framing else state.get("framing_types"),
        "converter_names": new_converters if new_converters else state.get("converter_names"),
        "payload_count": payload_count,
        "max_concurrent": max_concurrent,
        "error": None,  # Clear error for retry
        "next_node": "articulate",
    }
