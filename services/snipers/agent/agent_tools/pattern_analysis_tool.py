"""
Pattern Analysis Tool

Analyzes attack patterns from example findings using COT and Step-Back prompting.
Uses structured output with LangChain's with_structured_output for Pydantic validation.
"""
from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from services.snipers.models import PatternAnalysis
from services.snipers.agent.prompts import (
    PATTERN_ANALYSIS_PROMPT,
    format_example_findings,
    format_recon_intelligence,
)


def create_pattern_analysis_agent(llm: BaseChatModel) -> BaseChatModel:
    """
    Create pattern analysis agent with structured Pydantic output.

    Args:
        llm: Language model for analysis

    Returns:
        LLM with structured output bound to PatternAnalysis
    """
    return llm.with_structured_output(PatternAnalysis)


def analyze_pattern_with_context(
    agent: BaseChatModel, llm: BaseChatModel, context: Dict[str, Any]
) -> PatternAnalysis:
    """
    Analyze attack patterns using the agent with structured output.

    Args:
        agent: LLM with structured output (PatternAnalysis)
        llm: Language model (unused, kept for API compatibility)
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

        messages = [
            SystemMessage(content="You are an expert security researcher analyzing vulnerability patterns."),
            HumanMessage(content=prompt)
        ]

        result = agent.invoke(messages)

        if not isinstance(result, PatternAnalysis):
            raise ValueError(f"Expected PatternAnalysis, got {type(result)}")

        return result

    except Exception as e:
        raise ValueError(f"Pattern analysis failed: {str(e)}") from e
