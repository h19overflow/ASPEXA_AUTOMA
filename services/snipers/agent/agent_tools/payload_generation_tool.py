"""
Payload Generation Tool

Generates attack payloads based on learned patterns.
Uses structured output with LangChain's with_structured_output for Pydantic validation.
"""
from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from services.snipers.models import PayloadGeneration
from services.snipers.agent.prompts import (
    PAYLOAD_GENERATION_PROMPT,
    format_example_findings,
    format_recon_intelligence,
)


def create_payload_generation_agent(llm: BaseChatModel) -> BaseChatModel:
    """
    Create payload generation agent with structured Pydantic output.

    Args:
        llm: Language model for generation

    Returns:
        LLM with structured output bound to PayloadGeneration
    """
    return llm.with_structured_output(PayloadGeneration)


def generate_payloads_with_context(
    agent: BaseChatModel, llm: BaseChatModel, context: Dict[str, Any]
) -> PayloadGeneration:
    """
    Generate payloads using the agent with structured output.

    Args:
        agent: LLM with structured output (PayloadGeneration)
        llm: Language model (unused, kept for API compatibility)
        context: Context dict with probe_name, target_url, pattern_analysis,
                 converter_selection, example_findings, recon_intelligence, human_guidance

    Returns:
        PayloadGeneration with validated structure

    Raises:
        ValueError: If payload generation fails
    """
    try:
        pattern_analysis = context.get("pattern_analysis", {})
        converter_selection = context.get("converter_selection", {})

        if hasattr(pattern_analysis, "model_dump"):
            pattern_analysis_str = str(pattern_analysis.model_dump())
        else:
            pattern_analysis_str = str(pattern_analysis)

        if hasattr(converter_selection, "model_dump"):
            converter_selection_str = str(converter_selection.model_dump())
        else:
            converter_selection_str = str(converter_selection)

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

        prompt = PAYLOAD_GENERATION_PROMPT.format(
            probe_name=context["probe_name"],
            target_url=context["target_url"],
            pattern_analysis=pattern_analysis_str,
            converter_selection=converter_selection_str,
            example_findings=format_example_findings(context.get("example_findings", [])),
            recon_intelligence=format_recon_intelligence(
                context.get("recon_intelligence", {})
            ),
            vulnerability_cluster=vulnerability_cluster_str,
            human_guidance=context.get("human_guidance", "No specific guidance provided."),
        )

        messages = [
            SystemMessage(content="You are an expert at crafting attack payloads based on learned patterns."),
            HumanMessage(content=prompt)
        ]

        result = agent.invoke(messages)

        if not isinstance(result, PayloadGeneration):
            raise ValueError(f"Expected PayloadGeneration, got {type(result)}")

        return result

    except Exception as e:
        raise ValueError(f"Payload generation failed: {str(e)}") from e
