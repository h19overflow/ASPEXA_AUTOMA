"""
Attack Execution Node

Executes approved attack payloads against the target using PyRIT.
"""
import logging
from typing import Any, Dict

from services.snipers.agent.state import ExploitAgentState
from services.snipers.tools.pyrit_executor import PyRITExecutor, PyRITExecutorError

logger = logging.getLogger(__name__)

# Initialize executor once at module level (reuse across calls)
_executor = PyRITExecutor()


def execute_attack_node(state: ExploitAgentState) -> Dict[str, Any]:
    """
    Node: Execute attack with generated payloads using PyRIT.

    Requires human approval before execution. Sends one payload
    at a time and records the response.

    This is a CRITICAL NODE - attacks only execute after human approval.

    Args:
        state: Current exploit agent state

    Returns:
        Dict with current_payload, current_response, current_payload_index, and next_action
    """
    if not state.get("human_approved"):
        return {
            "error": "Attack execution requires human approval",
            "next_action": "error"
        }

    payloads = state["payload_generation"].generated_payloads
    current_index = state.get("current_payload_index", 0)

    if current_index >= len(payloads):
        return {
            "error": "No more payloads to execute",
            "next_action": "complete"
        }

    payload = payloads[current_index]

    # Extract converter names and target from state
    converter_names = state["converter_selection"].selected_converters
    target_url = state["target_url"]

    logger.info(
        f"Executing payload {current_index + 1}/{len(payloads)} "
        f"with {len(converter_names)} converters"
    )

    # Execute attack via PyRIT
    try:
        result = _executor.execute_attack(
            payload=payload,
            converter_names=converter_names,
            target_url=target_url
        )

        response = result["response"]
        errors = result["errors"]

        # Log converter errors but continue execution
        if errors:
            logger.warning(
                f"Converter errors during execution: {errors}"
            )

        logger.info(
            f"Attack executed successfully: "
            f"response_len={len(response)}, errors={len(errors)}"
        )

    except PyRITExecutorError as e:
        logger.error(f"Attack execution failed: {str(e)}")
        return {
            "error": f"Attack execution failed: {str(e)}",
            "current_payload": payload,
            "current_response": f"[EXECUTION ERROR: {str(e)}]",
            "current_payload_index": current_index + 1,
            "next_action": "score_result"  # Score the error
        }
    except Exception as e:
        logger.error(f"Unexpected error during attack execution: {str(e)}", exc_info=True)
        return {
            "error": f"Unexpected error: {str(e)}",
            "current_payload": payload,
            "current_response": f"[UNEXPECTED ERROR: {str(e)}]",
            "current_payload_index": current_index + 1,
            "next_action": "score_result"
        }

    return {
        "current_payload": payload,
        "current_response": response,
        "current_payload_index": current_index + 1,
        "next_action": "score_result"
    }
