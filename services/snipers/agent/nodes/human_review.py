"""
Human Review Nodes

Handles human-in-the-loop review points using LangGraph interrupts.
"""
from typing import Any, Dict

from langgraph.types import interrupt

from services.snipers.models import HumanFeedback
from services.snipers.agent.state import ExploitAgentState


def human_review_plan_node(state: ExploitAgentState) -> Dict[str, Any]:
    """
    Node: INTERRUPT for human review of attack plan.

    Pauses workflow execution and presents the complete attack plan
    to human reviewers for approval, rejection, or modification.

    This is a CRITICAL GATE - no attacks are executed without human approval.

    Args:
        state: Current exploit agent state

    Returns:
        Dict with human_approved, human_feedback, awaiting_human_review, and next_action
    """
    attack_plan = state.get("attack_plan")
    if not attack_plan:
        return {"error": "No attack plan to review", "next_action": "error"}

    # CRITICAL INTERRUPT: Human must review attack plan before execution
    human_response = interrupt({
        "type": "attack_plan_review",
        "probe_name": state["probe_name"],
        "attack_plan": attack_plan.model_dump(),
        "question": "Review and approve attack plan. Options: approve, reject, modify"
    })

    # Human response structure: {"decision": "approve|reject|modify", "feedback": "...", "modifications": {...}}
    decision = human_response.get("decision", "reject")

    feedback = HumanFeedback(
        approved=(decision == "approve"),
        feedback_text=human_response.get("feedback"),
        modifications=human_response.get("modifications")
    )

    return {
        "human_approved": (decision == "approve"),
        "human_feedback": feedback,
        "awaiting_human_review": False,
        "next_action": decision
    }


def human_review_result_node(state: ExploitAgentState) -> Dict[str, Any]:
    """
    Node: INTERRUPT for human review of attack results.

    Pauses workflow to let human reviewers verify attack success,
    request retries with modifications, or approve final results.

    Args:
        state: Current exploit agent state

    Returns:
        Dict with human_feedback and next_action
    """
    results = state.get("attack_results", [])
    if not results:
        return {"error": "No results to review", "next_action": "error"}

    latest_result = results[-1]

    # INTERRUPT: Human reviews attack results
    human_response = interrupt({
        "type": "attack_result_review",
        "probe_name": state["probe_name"],
        "result": latest_result.model_dump(),
        "question": "Review attack result. Options: approve, retry, stop"
    })

    decision = human_response.get("decision", "stop")

    feedback = HumanFeedback(
        approved=(decision == "approve"),
        feedback_text=human_response.get("feedback"),
        modifications=human_response.get("modifications")
    )

    # Update result with human review
    latest_result.human_reviewed = True
    latest_result.human_feedback = feedback

    return {
        "human_feedback": feedback,
        "next_action": "retry" if decision == "retry" else "complete"
    }
