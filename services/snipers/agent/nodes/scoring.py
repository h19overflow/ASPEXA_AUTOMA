"""
Attack Result Scoring Node

Scores attack results to determine if the exploit was successful.
"""
from typing import Any, Dict

from langchain_core.language_models import BaseChatModel

from services.snipers.agent.agent_tools import score_attack_result
from services.snipers.models import AttackResult
from services.snipers.agent.state import ExploitAgentState


def score_result_node(
    agent: Any, llm: BaseChatModel, state: ExploitAgentState
) -> Dict[str, Any]:
    """
    Node: Score attack result using scoring agent.

    Uses the scoring agent with structured Pydantic output (ScoringResult) to
    evaluate whether the attack was successful by analyzing the target's response.

    Args:
        agent: Compiled scoring agent with Pydantic response_format
        llm: Language model (used as fallback)
        state: Current exploit agent state

    Returns:
        Dict with updated attack_results and state updates
    """
    payload = state.get("current_payload")
    response = state.get("current_response")

    if not payload or not response:
        return {"error": "Missing payload or response"}

    if not state.get("pattern_analysis"):
        return {"error": "Missing pattern analysis"}

    try:
        # Extract success_indicators from pattern_analysis
        success_indicators = []
        if state.get("pattern_analysis"):
            success_indicators = state["pattern_analysis"].success_indicators

        # Extract example outputs from example_findings
        example_outputs = [f.output for f in state["example_findings"]]

        scoring_result = score_attack_result(
            agent,
            llm,
            probe_name=state["probe_name"],
            attack_payload=payload,
            target_response=response,
            pattern_analysis=state["pattern_analysis"],
            success_indicators=success_indicators,
            example_outputs=example_outputs,
        )

        attempt_number = len(state.get("attack_results", [])) + 1

        attack_result = AttackResult(
            success=scoring_result.success,
            probe_name=state["probe_name"],
            attempt_number=attempt_number,
            payload=payload,
            response=response,
            score=scoring_result.confidence_score,
            scorer_name="agent_structured_scoring",
            human_reviewed=False,
        )

        results = state.get("attack_results", []) or []
        results.append(attack_result)

        return {
            "attack_results": results,
        }
    except Exception as e:
        return {
            "error": f"Scoring failed: {str(e)}",
        }
