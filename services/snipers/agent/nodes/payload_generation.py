"""
Payload Generation Node

Generates attack payloads based on pattern analysis and converter selection.
"""
from typing import Any, Dict

from langchain_core.language_models import BaseChatModel

from services.snipers.agent.agent_tools import generate_payloads_with_context
from services.snipers.agent.state import ExploitAgentState


def generate_payloads_node(
    agent: Any, llm: BaseChatModel, state: ExploitAgentState
) -> Dict[str, Any]:
    """
    Node: Generate attack payloads using payload generation agent.

    Uses the payload generation agent with structured Pydantic output to create
    effective attack payloads following learned patterns and using selected converters.

    Args:
        agent: Compiled payload generation agent with Pydantic response_format
        llm: Language model (used as fallback)
        state: Current exploit agent state

    Returns:
        Dict with payload_generation and state updates
    """
    if not state.get("pattern_analysis") or not state.get("converter_selection"):
        return {"error": "Missing analysis data"}

    human_guidance = ""
    if state.get("human_feedback"):
        feedback = state["human_feedback"]
        if feedback.feedback_text:
            human_guidance = f"Human Feedback: {feedback.feedback_text}"
        if feedback.modifications:
            modifications_str = ", ".join(
                f"{k}: {v}" for k, v in feedback.modifications.items()
            )
            human_guidance += f"\nModifications: {modifications_str}"

    try:
        payload_generation = generate_payloads_with_context(
            agent,
            llm,
            probe_name=state["probe_name"],
            target_url=state["target_url"],
            pattern_analysis=state["pattern_analysis"],
            converter_selection=state["converter_selection"],
            example_findings=state["example_findings"],
            recon_intelligence=state.get("recon_intelligence", {}),
            human_guidance=human_guidance or None,
        )

        return {
            "payload_generation": payload_generation,
        }
    except Exception as e:
        return {
            "error": f"Payload generation failed: {str(e)}",
        }
