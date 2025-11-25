"""
Pattern Analysis Node

Analyzes attack patterns from example findings using the pattern analysis agent.
"""
from typing import Any, Dict

from langchain_core.language_models import BaseChatModel

from services.snipers.agent.agent_tools import analyze_pattern_with_context
from services.snipers.agent.state import ExploitAgentState


def analyze_pattern_node(
    agent: Any, llm: BaseChatModel, state: ExploitAgentState
) -> Dict[str, Any]:
    """
    Node: Analyze attack patterns using pattern analysis agent.

    Uses the pattern analysis agent with structured Pydantic output to identify
    common attack patterns from example findings using COT and Step-Back prompting.

    Args:
        agent: Compiled pattern analysis agent with Pydantic response_format
        llm: Language model (used as fallback)
        state: Current exploit agent state

    Returns:
        Dict with pattern_analysis and state updates
    """
    try:
        context = {
            "probe_name": state["probe_name"],
            "example_findings": state["example_findings"],
            "target_url": state["target_url"],
            "recon_intelligence": state.get("recon_intelligence", {}),
        }

        pattern_analysis = analyze_pattern_with_context(agent, llm, context)

        return {
            "pattern_analysis": pattern_analysis,
        }
    except Exception as e:
        return {
            "error": f"Pattern analysis failed: {str(e)}",
        }
