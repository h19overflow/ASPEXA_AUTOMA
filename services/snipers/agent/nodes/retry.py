"""
Retry Handling Node

Manages retry logic for failed attacks.
"""
from typing import Any, Dict

from services.snipers.agent.state import ExploitAgentState


def handle_retry_node(state: ExploitAgentState) -> Dict[str, Any]:
    """
    Node: Handle retry logic after failed attacks.

    Checks if retry limit has been reached. If not, prepares state
    for another attempt with modifications based on human feedback.

    Args:
        state: Current exploit agent state

    Returns:
        Dict with retry_count, failed_payloads, next_action, and reset flags
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count >= max_retries:
        return {
            "error": f"Max retries ({max_retries}) reached",
            "next_action": "give_up"
        }

    # Track failed payloads to avoid repeating them
    failed = state.get("failed_payloads", [])
    if state.get("current_payload"):
        failed.append(state["current_payload"])

    return {
        "retry_count": retry_count + 1,
        "failed_payloads": failed,
        "next_action": "retry",
        "human_approved": None,  # Reset approval for new attempt
        "awaiting_human_review": False
    }
