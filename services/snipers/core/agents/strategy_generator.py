from langchain.chat_models import init_chat_model
"""
Strategy Generator.

Purpose: LLM-powered adaptation strategy generation
Role: Invoke LLM with structured output to produce AdaptationDecision
Dependencies: langchain.agents.create_agent, ToolStrategy, models, prompts
"""

import logging
from typing import Any

from dotenv import load_dotenv
load_dotenv()

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from services.snipers.core.adaptive_models.adaptation_decision import AdaptationDecision
from services.snipers.core.adaptive_models.chain_discovery import ChainDiscoveryContext
from services.snipers.core.agents.prompts.adaptation_prompt import (
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
                model=init_chat_model("google_genai:gemini-3-flash-preview", thinking_budget=1024, thinking_level="low"),
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
        chain_discovery_context: ChainDiscoveryContext | None = None,
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
            config: Optional config with recon_intelligence
            chain_discovery_context: Failure analysis context with root cause

        Returns:
            AdaptationDecision with strategy and reasoning

        Raises:
            ValueError: If LLM fails to produce structured output
        """
        # Extract recon intelligence from config if available
        recon_intelligence = None
        if config:
            recon_intelligence = config.get("recon_intelligence")
            if recon_intelligence:
                self.logger.info(
                    "Recon intelligence available for strategy generation",
                    extra={
                        "target_description": recon_intelligence.get(
                            "target_self_description"
                        )
                    },
                )

        user_prompt = build_adaptation_user_prompt(
            responses=responses,
            iteration_history=iteration_history,
            tried_framings=tried_framings,
            tried_converters=tried_converters,
            objective=objective,
            pre_analysis=pre_analysis,
            recon_intelligence=recon_intelligence,
            chain_discovery_context=chain_discovery_context,
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
            f"recon_framing={'Yes' if decision.recon_custom_framing else 'No'}, "
            f"confidence={decision.confidence:.2f}"
        )

        if decision.recon_custom_framing:
            self.logger.info(
                f"Recon-based framing discovered: {decision.recon_custom_framing.role} - "
                f"{decision.recon_custom_framing.context}"
            )

        return decision
