"""
Failure Analyzer Agent.

Purpose: LLM-powered semantic failure analysis for attack intelligence
Role: Replace rule-based FailureAnalyzer with agentic reasoning
Dependencies: langchain.agents.create_agent, FailureAnalysisDecision model
"""

import logging
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model

from services.snipers.models.adaptive_models.chain_discovery import ChainDiscoveryContext
from services.snipers.models.adaptive_models.failure_analysis import FailureAnalysisDecision
from services.snipers.core.agents.internals.failure_analyzer_internals import (
    convert_to_chain_discovery_context,
)
from services.snipers.core.agents.prompts.failure_analysis_prompt import (
    FAILURE_ANALYSIS_SYSTEM_PROMPT,
    build_failure_analysis_user_prompt,
)
from services.snipers.core.phases.articulation.models.tool_intelligence import ReconIntelligence

logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()

class FailureAnalyzerAgent:
    """
    LLM-powered failure analysis using structured output.

    Uses create_agent with ToolStrategy(FailureAnalysisDecision) for
    semantic understanding of attack failures.
    """

    def __init__(self, agent: Any = None):
        if agent is None:
            agent = create_agent(
                model=init_chat_model("google_genai:gemini-3-flash-preview"),
                response_format=ToolStrategy(FailureAnalysisDecision),
            )
        self._agent = agent
        self.logger = logging.getLogger(__name__)

    async def analyze(
        self,
        phase3_result: Any | None,
        failure_cause: str | None,
        target_responses: list[str],
        iteration_history: list[dict[str, Any]],
        tried_converters: list[list[str]],
        objective: str = "test security boundaries",
        recon_intelligence: ReconIntelligence | None = None,
        swarm_context: dict | None = None,
        config: dict | None = None,
    ) -> ChainDiscoveryContext:
        """Extract chain discovery context via LLM; falls back to minimal context on failure."""
        try:
            return await self._analyze_with_llm(
                phase3_result=phase3_result,
                failure_cause=failure_cause,
                target_responses=target_responses,
                iteration_history=iteration_history,
                tried_converters=tried_converters,
                objective=objective,
                recon_intelligence=recon_intelligence,
                swarm_context=swarm_context,
                config=config,
            )
        except Exception as e:
            self.logger.warning(f"LLM analysis failed: {e}, returning minimal context")
            return ChainDiscoveryContext(
                defense_signals=[],
                failure_root_cause=str(e),
                defense_evolution="exploring",
                converter_effectiveness={},
                unexplored_directions=["Try different converter chain"],
                required_properties=[],
                iteration_count=len(iteration_history),
                best_score_achieved=0.0,
                best_chain_so_far=[],
            )

    async def _analyze_with_llm(
        self,
        phase3_result: Any | None,
        failure_cause: str | None,
        target_responses: list[str],
        iteration_history: list[dict[str, Any]],
        tried_converters: list[list[str]],
        objective: str,
        recon_intelligence: ReconIntelligence | None,
        swarm_context: dict | None = None,
        config: dict | None = None,
    ) -> ChainDiscoveryContext:
        """Invoke LLM and convert response to ChainDiscoveryContext."""
        user_prompt = build_failure_analysis_user_prompt(
            phase3_result=phase3_result,
            failure_cause=failure_cause,
            target_responses=target_responses,
            iteration_history=iteration_history,
            tried_converters=tried_converters,
            objective=objective,
            recon_intelligence=recon_intelligence,
            swarm_context=swarm_context,
        )

        self.logger.info(
            f"[FailureAnalyzerAgent] Analyzing failure "
            f"({len(target_responses)} responses, {len(iteration_history)} iterations)"
        )

        result = await self._agent.ainvoke(
            {
                "messages": [
                    {"role": "system", "content": FAILURE_ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            },
            config=config or {},
        )

        decision: FailureAnalysisDecision | None = result.get("structured_response")

        if decision is None:
            raise ValueError("LLM did not return structured FailureAnalysisDecision")

        self.logger.info(
            f"  Defenses: {len(decision.detected_defenses)}, "
            f"cause: {decision.primary_failure_cause[:80]}..., "
            f"confidence: {decision.analysis_confidence:.2f}"
        )

        return convert_to_chain_discovery_context(
            decision=decision,
            iteration_history=iteration_history,
            tried_converters=tried_converters,
        )
