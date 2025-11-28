"""
Converter Selection Tool

Selects appropriate PyRIT converters based on pattern analysis.
Uses structured output with LangChain's with_structured_output for Pydantic validation.
"""
from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from services.snipers.models import ConverterSelection
from services.snipers.agent.prompts import (
    CONVERTER_SELECTION_PROMPT,
    format_recon_intelligence,
)


def create_converter_selection_agent(llm: BaseChatModel) -> BaseChatModel:
    """
    Create converter selection agent with structured Pydantic output.

    Args:
        llm: Language model for selection

    Returns:
        LLM with structured output bound to ConverterSelection
    """
    return llm.with_structured_output(ConverterSelection)


def select_converters_with_context(
    agent: BaseChatModel, llm: BaseChatModel, context: Dict[str, Any]
) -> ConverterSelection:
    """
    Select converters using the agent with structured output.

    Args:
        agent: LLM with structured output (ConverterSelection)
        llm: Language model (unused, kept for API compatibility)
        context: Context dict with probe_name, target_url, pattern_analysis, recon_intelligence

    Returns:
        ConverterSelection with validated structure

    Raises:
        ValueError: If converter selection fails
    """
    try:
        pattern_analysis = context.get("pattern_analysis", {})
        if hasattr(pattern_analysis, "model_dump"):
            pattern_analysis_str = str(pattern_analysis.model_dump())
        else:
            pattern_analysis_str = str(pattern_analysis)

        vulnerability_cluster = context.get("vulnerability_cluster", {})
        vulnerability_cluster_str = ""
        if vulnerability_cluster:
            vulnerability_cluster_str = f"""
Severity: {vulnerability_cluster.get('severity', 'unknown')}
Category: {vulnerability_cluster.get('category', 'unknown')}
Related vulnerabilities: {vulnerability_cluster.get('related_count', 0)}
"""
        else:
            vulnerability_cluster_str = "No vulnerability cluster data available."

        prompt = CONVERTER_SELECTION_PROMPT.format(
            probe_name=context["probe_name"],
            target_url=context["target_url"],
            pattern_analysis=pattern_analysis_str,
            recon_intelligence=format_recon_intelligence(
                context.get("recon_intelligence", {})
            ),
            vulnerability_cluster=vulnerability_cluster_str,
        )

        messages = [
            SystemMessage(content="You are an expert in selecting attack transformation converters."),
            HumanMessage(content=prompt)
        ]

        result = agent.invoke(messages)

        if not isinstance(result, ConverterSelection):
            raise ValueError(f"Expected ConverterSelection, got {type(result)}")

        return result

    except Exception as e:
        raise ValueError(f"Converter selection failed: {str(e)}") from e
