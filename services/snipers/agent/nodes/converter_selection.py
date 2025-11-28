"""
Converter Selection Node

Selects appropriate PyRIT converters based on pattern analysis.
"""
from typing import Any, Dict

from langchain_core.language_models import BaseChatModel

from services.snipers.agent.agent_tools import select_converters_with_context
from services.snipers.agent.state import ExploitAgentState


def select_converters_node(
    agent: Any, llm: BaseChatModel, state: ExploitAgentState
) -> Dict[str, Any]:
    """
    Node: Select PyRIT converters using converter selection agent.

    Uses the converter selection agent with structured Pydantic output to choose
    appropriate transformation converters based on pattern analysis.

    Args:
        agent: Compiled converter selection agent with Pydantic response_format
        llm: Language model (used as fallback)
        state: Current exploit agent state

    Returns:
        Dict with converter_selection and state updates
    """
    if not state.get("pattern_analysis"):
        return {"error": "No pattern analysis available"}

    try:
        converter_selection = select_converters_with_context(
            agent,
            llm,
            probe_name=state["probe_name"],
            target_url=state["target_url"],
            pattern_analysis=state["pattern_analysis"],
            recon_intelligence=state.get("recon_intelligence", {}),
            vulnerability_cluster=state.get("vulnerability_cluster"),
        )

        return {
            "converter_selection": converter_selection,
        }
    except Exception as e:
        return {
            "error": f"Converter selection failed: {str(e)}",
        }
