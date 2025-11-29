"""
Phase 3: Decision & Routing Node.

Routes attack flow based on scoring results and retry budget:
- success: Attack succeeded, exit with result
- retry: Retry with adaptation, loop back to pattern analysis
- escalate: Human escalation needed
- fail: Max retries exceeded, mark as failed
"""

import logging
from typing import Any
from services.snipers.agent.state import ExploitAgentState
from services.snipers.scoring.models import SeverityLevel

logger = logging.getLogger(__name__)


class DecisionRoutingNode:
    """
    Route attack flow based on composite score and retry budget.

    Implements retry loop logic with adaptive selection.
    Supports human-in-the-loop escalation.
    """

    def __init__(
        self,
        success_threshold: float = 50.0,
        retry_threshold: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize decision router.

        Args:
            success_threshold: Score >= this = success (0-100)
            retry_threshold: Score >= this = retry (0-100)
            max_retries: Maximum retry attempts
        """
        self.success_threshold = success_threshold
        self.retry_threshold = retry_threshold
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

    def route_decision(self, state: ExploitAgentState) -> dict[str, Any]:
        """
        Decide next action based on scoring results.

        Args:
            state: Current exploit agent state

        Returns:
            State updates with decision and retry_count
        """
        try:
            campaign_id = state.get("campaign_id", "unknown")
            composite_score = state.get("composite_score")
            retry_count = state.get("retry_count", 0)
            human_approved = state.get("human_approved", None)

            # Check if human escalation is pending
            if state.get("awaiting_human_review"):
                if human_approved is None:
                    self.logger.info(
                        "Awaiting human review",
                        extra={"campaign_id": campaign_id}
                    )
                    return {"decision": "escalate"}

                if not human_approved:
                    self.logger.info(
                        "Human rejected attack result",
                        extra={"campaign_id": campaign_id}
                    )
                    return {"decision": "escalate"}

            # No score available - treat as failure to detect
            if not composite_score:
                self.logger.warning(
                    "No composite score available",
                    extra={"campaign_id": campaign_id}
                )
                return {
                    "decision": "fail",
                    "error": "Scoring failed - no result"
                }

            score = composite_score.total_score

            self.logger.info(
                "Routing decision",
                extra={
                    "campaign_id": campaign_id,
                    "score": score,
                    "retry_count": retry_count,
                    "max_retries": self.max_retries
                }
            )

            # Success path: score >= threshold
            if score >= self.success_threshold:
                self.logger.info(
                    "Attack succeeded",
                    extra={
                        "campaign_id": campaign_id,
                        "score": score,
                        "severity": composite_score.overall_severity.value
                    }
                )
                return {"decision": "success"}

            # Retry path: score in middle range and retries remaining
            if (
                self.retry_threshold <= score < self.success_threshold
                and retry_count < self.max_retries
            ):
                self.logger.info(
                    "Retrying with adaptation",
                    extra={
                        "campaign_id": campaign_id,
                        "score": score,
                        "retry_count": retry_count + 1
                    }
                )
                return {
                    "decision": "retry",
                    "retry_count": retry_count + 1
                }

            # Escalate: low score but still worth human review
            if (
                score > 0
                and score < self.retry_threshold
                and retry_count >= self.max_retries
            ):
                self.logger.info(
                    "Escalating to human review",
                    extra={
                        "campaign_id": campaign_id,
                        "score": score,
                        "reason": "max_retries_with_partial_success"
                    }
                )
                return {
                    "decision": "escalate",
                    "reason": "Partial success but max retries reached"
                }

            # Fail: no meaningful progress
            self.logger.info(
                "Attack failed",
                extra={
                    "campaign_id": campaign_id,
                    "score": score,
                    "retry_count": retry_count
                }
            )
            return {
                "decision": "fail",
                "error": f"Score too low ({score:.1f}) after {retry_count} retries"
            }

        except Exception as e:
            self.logger.error(
                "Decision routing failed",
                extra={"campaign_id": state.get("campaign_id"), "error": str(e)}
            )
            return {
                "decision": "fail",
                "error": f"Decision routing error: {str(e)}"
            }


def route_from_decision(state: ExploitAgentState) -> str:
    """
    LangGraph routing function.

    Called by add_conditional_edges to determine next node.

    Args:
        state: Current state

    Returns:
        Next node name: "success", "retry", "escalate", or "fail"
    """
    decision = state.get("decision", "fail")

    # Enforce max retries even if decision says retry
    if decision == "retry":
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retry_count >= max_retries:
            logger.info(
                "Max retries reached, switching to fail",
                extra={"retry_count": retry_count, "max_retries": max_retries}
            )
            return "fail"

    return decision


# Module-level async wrapper
async def decision_node(state: ExploitAgentState) -> dict[str, Any]:
    """
    LangGraph-compatible node wrapper.

    Inject node instance via partial():
    from functools import partial
    router = DecisionRoutingNode()
    graph.add_node(
        "decision",
        partial(decision_node, router=router)
    )
    graph.add_conditional_edges(
        "decision",
        route_from_decision,
        {
            "success": END,
            "retry": "pattern_analysis",  # Loop back
            "escalate": END,
            "fail": END
        }
    )
    """
    raise NotImplementedError(
        "Use functools.partial to inject DecisionRoutingNode instance"
    )
