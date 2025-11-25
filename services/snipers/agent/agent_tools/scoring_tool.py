"""
Scoring Tool

Evaluates attack results using LLM-based analysis.
Uses structured output with LangChain's with_structured_output for Pydantic validation.
"""
from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from services.snipers.models import ScoringResult
from services.snipers.agent.prompts import ATTACK_SCORING_PROMPT


def create_scoring_agent(llm: BaseChatModel) -> BaseChatModel:
    """
    Create scoring agent with structured Pydantic output.

    Args:
        llm: Language model for scoring

    Returns:
        LLM with structured output bound to ScoringResult
    """
    return llm.with_structured_output(ScoringResult)


def score_attack_result(
    agent: BaseChatModel, llm: BaseChatModel, context: Dict[str, Any]
) -> ScoringResult:
    """
    Score attack result using the agent with structured output.

    Args:
        agent: LLM with structured output (ScoringResult)
        llm: Language model (unused, kept for API compatibility)
        context: Context dict with probe_name, attack_payload, target_response,
                 pattern_analysis, success_indicators, example_outputs

    Returns:
        ScoringResult with validated structure

    Raises:
        ValueError: If scoring fails
    """
    try:
        pattern_analysis = context.get("pattern_analysis", {})
        if hasattr(pattern_analysis, "model_dump"):
            pattern_analysis_str = str(pattern_analysis.model_dump())
        else:
            pattern_analysis_str = str(pattern_analysis)

        success_indicators = context.get("success_indicators", [])
        if isinstance(success_indicators, list):
            success_indicators_str = "\n".join(f"- {ind}" for ind in success_indicators)
        else:
            success_indicators_str = str(success_indicators)

        example_outputs = context.get("example_outputs", [])
        if isinstance(example_outputs, list):
            example_outputs_str = "\n".join(f"- {out}" for out in example_outputs)
        else:
            example_outputs_str = str(example_outputs)

        prompt = ATTACK_SCORING_PROMPT.format(
            probe_name=context["probe_name"],
            attack_payload=context.get("attack_payload", ""),
            target_response=context.get("target_response", ""),
            pattern_analysis=pattern_analysis_str,
            success_indicators=success_indicators_str,
            example_outputs=example_outputs_str,
        )

        messages = [
            SystemMessage(content="You are an expert at evaluating attack success."),
            HumanMessage(content=prompt)
        ]

        result = agent.invoke(messages)

        if not isinstance(result, ScoringResult):
            raise ValueError(f"Expected ScoringResult, got {type(result)}")

        return result

    except Exception as e:
        raise ValueError(f"Attack scoring failed: {str(e)}") from e
