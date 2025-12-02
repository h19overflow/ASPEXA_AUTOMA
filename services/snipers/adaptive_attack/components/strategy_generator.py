"""
Strategy Generator.

Purpose: LLM-powered adaptation strategy generation
Role: Invoke LLM with structured output to produce AdaptationDecision
Dependencies: langchain.agents.create_agent, ToolStrategy, models, prompts
"""

import logging
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from services.snipers.adaptive_attack.models.adaptation_decision import AdaptationDecision
from services.snipers.adaptive_attack.prompts.adaptation_prompt import (
    ADAPTATION_SYSTEM_PROMPT,
    build_adaptation_user_prompt,
)

logger = logging.getLogger(__name__)


class StrategyGenerator:
    """
    LLM-powered strategy generation using structured output.

    Uses create_agent with ToolStrategy(AdaptationDecision) for
    guaranteed structured responses.
    """

    def __init__(self, agent: Any = None):
        """
        Initialize generator with LangChain agent.

        Args:
            agent: Optional agent for dependency injection (testing)
        """
        if agent is None:
            agent = create_agent(
                model="google_genai:gemini-2.5-flash",
                response_format=ToolStrategy(AdaptationDecision),
            )
        self._agent = agent
        self.logger = logging.getLogger(__name__)

    async def generate(
        self,
        responses: list[str],
        iteration_history: list[dict[str, Any]],
        tried_framings: list[str],
        tried_converters: list[list[str]],
        objective: str,
        pre_analysis: dict[str, Any],
        config: dict = None,
    ) -> AdaptationDecision:
        """
        Generate adaptation decision via LLM.

        Args:
            responses: Raw response texts from target
            iteration_history: Records of previous iterations
            tried_framings: All framings attempted so far
            tried_converters: All converter chains attempted
            objective: Attack objective
            pre_analysis: Rule-based pre-analysis of responses

        Returns:
            AdaptationDecision with strategy and reasoning

        Raises:
            ValueError: If LLM fails to produce structured output
        """
        user_prompt = build_adaptation_user_prompt(
            responses=responses,
            iteration_history=iteration_history,
            tried_framings=tried_framings,
            tried_converters=tried_converters,
            objective=objective,
            pre_analysis=pre_analysis,
        )

        self.logger.info("Generating adaptation strategy via LLM")

        result = await self._agent.ainvoke(
            {
                "messages": [
                    {"role": "system", "content": ADAPTATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            },
            config=config or {},
        )

        decision: AdaptationDecision | None = result.get("structured_response")

        if decision is None:
            raise ValueError("LLM did not return structured AdaptationDecision")

        self.logger.info(
            f"Strategy generated: custom_framing={decision.use_custom_framing}, "
            f"confidence={decision.confidence:.2f}"
        )

        return decision
