"""
Payload Generation Tool

Generates attack payloads based on pattern analysis and converter selection.
Uses structured output with create_agent and Pydantic validation.
"""
from typing import Any, Dict, Optional

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from services.snipers.models import (
    ConverterSelection,
    ExampleFinding,
    PayloadGeneration,
    PatternAnalysis,
)
from services.snipers.agent.prompts import (
    PAYLOAD_GENERATION_PROMPT,
    format_example_findings,
    format_recon_intelligence,
)


def create_payload_generation_agent(llm: BaseChatModel) -> Any:
    """
    Create payload generation agent with structured Pydantic output.

    Args:
        llm: Language model for generation

    Returns:
        Compiled agent that outputs PayloadGeneration
    """
    agent = create_agent(
        model=llm,
        tools=[],  # No tools needed for this agent
        system_prompt="You are an expert at crafting attack payloads based on learned patterns.",
        response_format=PayloadGeneration,
    )
    return agent


def generate_payloads_with_context(
    agent: Any,
    llm: BaseChatModel,
    probe_name: str,
    target_url: str,
    pattern_analysis: PatternAnalysis,
    converter_selection: ConverterSelection,
    example_findings: list[ExampleFinding],
    recon_intelligence: Dict[str, Any],
    human_guidance: Optional[str] = None,
) -> PayloadGeneration:
    """
    Generate attack payloads using the agent with structured output.

    Args:
        agent: Compiled payload generation agent
        llm: Language model
        probe_name: Name of the probe
        target_url: Target URL
        pattern_analysis: PatternAnalysis result
        converter_selection: ConverterSelection result
        example_findings: List of example findings
        recon_intelligence: Recon intelligence data
        human_guidance: Optional guidance from human

    Returns:
        PayloadGeneration with validated structure

    Raises:
        ValueError: If payload generation fails
    """
    try:
        human_guidance_text = human_guidance or "No specific guidance provided."

        prompt = PAYLOAD_GENERATION_PROMPT.format(
            probe_name=probe_name,
            target_url=target_url,
            pattern_analysis=pattern_analysis.model_dump_json(indent=2),
            converter_selection=converter_selection.model_dump_json(indent=2),
            example_findings=format_example_findings(example_findings),
            recon_intelligence=format_recon_intelligence(recon_intelligence or {}),
            human_guidance=human_guidance_text,
        )

        result = agent.invoke({"messages": [("user", prompt)]})
        payload_generation = result.get("structured_response")

        if not payload_generation:
            raise ValueError("No structured response from agent")

        if not isinstance(payload_generation, PayloadGeneration):
            # Fallback validation with Pydantic
            payload_generation = PayloadGeneration(**payload_generation)

        return payload_generation

    except Exception as e:
        raise ValueError(f"Payload generation failed: {str(e)}") from e
