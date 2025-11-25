"""
Agent Routing Logic

Handles routing decisions after human interaction points in the exploit agent workflow.
Separates routing logic from the main workflow graph for better maintainability.
"""
from services.snipers.agent.state import ExploitAgentState


def route_after_human_review(state: ExploitAgentState) -> str:
    """
    Route after human reviews attack plan.

    Args:
        state: Current exploit agent state

    Returns:
        Routing decision: "approved", "modify", or "rejected"
    """
    next_action = state.get("next_action", "rejected")

    if next_action == "approve":
        return "approved"
    elif next_action == "modify":
        return "modify"
    else:
        return "rejected"


def route_after_result_review(state: ExploitAgentState) -> str:
    """
    Route after human reviews attack results.

    Args:
        state: Current exploit agent state

    Returns:
        Routing decision: "retry" or "complete"
    """
    next_action = state.get("next_action", "complete")
    return "retry" if next_action == "retry" else "complete"


def route_after_retry(state: ExploitAgentState) -> str:
    """
    Route after retry handling.

    Args:
        state: Current exploit agent state

    Returns:
        Routing decision: "retry" or "give_up"
    """
    next_action = state.get("next_action", "give_up")
    return "retry" if next_action == "retry" else "give_up"
