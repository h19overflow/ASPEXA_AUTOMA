"""
Converter Selection Tool

Selects appropriate PyRIT converters based on pattern analysis.
Uses structured output with create_agent and Pydantic validation.
"""
import json
from typing import Any, Dict

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from services.snipers.models import ConverterSelection, PatternAnalysis
from services.snipers.agent.prompts import (
    CONVERTER_SELECTION_PROMPT,
    format_recon_intelligence,
)


def create_converter_selection_agent(llm: BaseChatModel) -> Any:
    """
    Create converter selection agent with structured Pydantic output.

    Args:
        llm: Language model for selection

    Returns:
        Compiled agent that outputs ConverterSelection
    """
    agent = create_agent(
        model=llm,
        tools=[],  # No tools needed for this agent
        system_prompt="You are an expert in selecting attack transformation converters for exploitation.",
        response_format=ConverterSelection,
    )
    return agent


def select_converters_with_context(
    agent: Any,
    llm: BaseChatModel,
    probe_name: str,
    target_url: str,
    pattern_analysis: PatternAnalysis,
    recon_intelligence: Dict[str, Any],
) -> ConverterSelection:
    """
    Select appropriate converters using the agent with structured output.

    Args:
        agent: Compiled converter selection agent
        llm: Language model
        probe_name: Name of the probe
        target_url: Target URL
        pattern_analysis: PatternAnalysis result
        recon_intelligence: Recon intelligence data

    Returns:
        ConverterSelection with validated structure

    Raises:
        ValueError: If converter selection fails
    """
    try:
        prompt = CONVERTER_SELECTION_PROMPT.format(
            probe_name=probe_name,
            target_url=target_url,
            pattern_analysis=pattern_analysis.model_dump_json(indent=2),
            recon_intelligence=format_recon_intelligence(recon_intelligence or {}),
        )

        result = agent.invoke({"messages": [("user", prompt)]})
        converter_selection = result.get("structured_response")

        if not converter_selection:
            raise ValueError("No structured response from agent")

        if not isinstance(converter_selection, ConverterSelection):
            # Fallback validation with Pydantic
            converter_selection = ConverterSelection(**converter_selection)

        return converter_selection

    except Exception as e:
        raise ValueError(f"Converter selection failed: {str(e)}") from e
