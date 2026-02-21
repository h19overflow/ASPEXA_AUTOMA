"""
Chain Discovery Agent.

Purpose: LLM-powered intelligent converter chain generation
Role: Generate optimal chains based on failure analysis context
Dependencies: langchain.agents.create_agent, ChainDiscoveryDecision model
"""

import logging
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model

from services.snipers.core.adaptive_models.chain_discovery import (
    ChainDiscoveryContext,
    ChainDiscoveryDecision,
    ChainSelectionResult,
)
from services.snipers.core.agents.consts import AVAILABLE_CONVERTERS
from services.snipers.core.agents.internals.chain_discovery_internals import (
    select_best_chain,
    validate_and_filter_chains,
)
from services.snipers.core.agents.prompts.chain_discovery_prompt import (
    CHAIN_DISCOVERY_SYSTEM_PROMPT,
    build_chain_discovery_user_prompt,
)
from services.snipers.core.phases.articulation.models.tool_intelligence import ReconIntelligence

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()
class ChainDiscoveryAgent:
    """
    LLM-powered chain discovery using structured output.

    Uses create_agent with ToolStrategy(ChainDiscoveryDecision) for
    guaranteed structured chain candidates.
    """

    def __init__(self, agent: Any = None):
        if agent is None:
            agent = create_agent(
                model=init_chat_model("google_genai:gemini-3-flash-preview"),
                response_format=ToolStrategy(ChainDiscoveryDecision),
            )
        self._agent = agent
        self.logger = logging.getLogger(__name__)

    async def generate(
        self,
        context: ChainDiscoveryContext,
        tried_converters: list[list[str]],
        objective: str,
        recon_intelligence: ReconIntelligence | None = None,
        config: dict = None,
    ) -> ChainDiscoveryDecision:
        """
        Generate converter chain candidates via LLM.

        Args:
            context: ChainDiscoveryContext from failure analysis
            tried_converters: All converter chains attempted so far
            objective: Attack objective
            recon_intelligence: Structured recon data for context-aware chain selection
            config: Optional LangChain config

        Returns:
            ChainDiscoveryDecision with chain candidates and reasoning

        Raises:
            ValueError: If LLM fails to produce structured output
        """
        user_prompt = build_chain_discovery_user_prompt(
            context=context,
            tried_converters=tried_converters,
            objective=objective,
            recon_intelligence=recon_intelligence,
        )

        self.logger.info(
            f"[ChainDiscoveryAgent] Generating chains "
            f"({len(context.defense_signals)} signals, {len(tried_converters)} tried)"
        )

        result = await self._agent.ainvoke(
            {
                "messages": [
                    {"role": "system", "content": CHAIN_DISCOVERY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            },
            config=config or {},
        )

        decision: ChainDiscoveryDecision | None = result.get("structured_response")

        if decision is None:
            raise ValueError("LLM did not return structured ChainDiscoveryDecision")

        decision = validate_and_filter_chains(decision, tried_converters)

        self.logger.info(f"  Generated {len(decision.chains)} chain candidates")
        for i, chain in enumerate(decision.chains):
            self.logger.info(
                f"    {i+1}. {chain.converters} (confidence: {chain.expected_effectiveness:.2f})"
            )

        return decision

    def select_best_chain(
        self,
        decision: ChainDiscoveryDecision,
        context: ChainDiscoveryContext,
    ) -> ChainSelectionResult:
        """
        Select the best chain from candidates with full observability.

        Delegates to internals.select_best_chain.
        """
        return select_best_chain(decision, context)
