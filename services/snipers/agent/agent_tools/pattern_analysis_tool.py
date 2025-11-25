"""
Pattern Analysis Tool

Analyzes attack patterns from example findings using COT and Step-Back prompting.
Uses structured output with create_agent and Pydantic validation.
"""
from typing import Any, Dict

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from services.snipers.models import PatternAnalysis
from services.snipers.agent.prompts import (
    PATTERN_ANALYSIS_PROMPT,
    format_example_findings,
    format_recon_intelligence,
)


def create_pattern_analysis_agent(llm: BaseChatModel) -> Any:
    """
    Create pattern analysis agent with structured Pydantic output.

    Args:
        llm: Language model for analysis

    Returns:
        Compiled agent that outputs PatternAnalysis
    """
    agent = create_agent(
        model=llm,
        tools=[],  # No tools needed for this agent
        system_prompt="You are an expert security researcher analyzing vulnerability patterns.",
        response_format=PatternAnalysis,
    )
    return agent


def analyze_pattern_with_context(
    agent: Any, llm: BaseChatModel, context: Dict[str, Any]
) -> PatternAnalysis:
    """
    Analyze attack patterns using the agent with structured output.

    Args:
        agent: Compiled pattern analysis agent
        llm: Language model (used for fallback if agent fails)
        context: Context dict with probe_name, example_findings, target_url, recon_intelligence

    Returns:
        PatternAnalysis with validated structure

    Raises:
        ValueError: If pattern analysis fails
    """
    try:
        prompt = PATTERN_ANALYSIS_PROMPT.format(
            probe_name=context["probe_name"],
            num_examples=len(context["example_findings"]),
            target_url=context["target_url"],
            example_findings=format_example_findings(context["example_findings"]),
            recon_intelligence=format_recon_intelligence(
                context.get("recon_intelligence", {})
            ),
        )

        result = agent.invoke({"messages": [("user", prompt)]})
        pattern_analysis = result.get("structured_response")

        if not pattern_analysis:
            raise ValueError("No structured response from agent")

        if not isinstance(pattern_analysis, PatternAnalysis):
            # Fallback validation with Pydantic
            pattern_analysis = PatternAnalysis(**pattern_analysis)

        return pattern_analysis

    except Exception as e:
        raise ValueError(f"Pattern analysis failed: {str(e)}") from e
