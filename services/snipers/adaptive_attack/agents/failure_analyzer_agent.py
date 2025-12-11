"""
Failure Analyzer Agent.

Purpose: LLM-powered semantic failure analysis for attack intelligence
Role: Replace rule-based FailureAnalyzer with agentic reasoning
Dependencies: langchain.agents.create_agent, FailureAnalysisDecision model
"""

import logging
from typing import Any

from dotenv import load_dotenv
load_dotenv()

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from services.snipers.adaptive_attack.models.chain_discovery import ChainDiscoveryContext
from services.snipers.adaptive_attack.models.failure_analysis import (
    FailureAnalysisDecision,
    DefenseSignal,
)
from services.snipers.adaptive_attack.agents.prompts.failure_analysis_prompt import (
    FAILURE_ANALYSIS_SYSTEM_PROMPT,
    build_failure_analysis_user_prompt,
)
from services.snipers.adaptive_attack.components.failure_analyzer import FailureAnalyzer
from services.snipers.utils.prompt_articulation.models.tool_intelligence import ReconIntelligence

logger = logging.getLogger(__name__)


class FailureAnalyzerAgent:
    """
    LLM-powered failure analysis using structured output.

    Uses create_agent with ToolStrategy(FailureAnalysisDecision) for
    semantic understanding of attack failures.

    Falls back to rule-based FailureAnalyzer on LLM failure.
    """

    def __init__(self, agent: Any = None):
        """
        Initialize agent with LangChain.

        Args:
            agent: Optional agent for dependency injection (testing)
        """
        if agent is None:
            agent = create_agent(
                model="google_genai:gemini-2.5-pro",
                response_format=ToolStrategy(FailureAnalysisDecision),
            )
        self._agent = agent
        self._rule_based_fallback = FailureAnalyzer()
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
        config: dict | None = None,
    ) -> ChainDiscoveryContext:
        """
        Extract chain discovery context via LLM analysis.

        Same interface as rule-based FailureAnalyzer for drop-in replacement.

        Args:
            phase3_result: Phase 3 attack result with scorer data
            failure_cause: Why the iteration failed
            target_responses: Raw response texts from target
            iteration_history: Previous iteration outcomes
            tried_converters: All converter chains attempted
            objective: Attack objective
            recon_intelligence: Structured recon data (tools, defenses, system prompt)
            config: Optional LangChain config

        Returns:
            ChainDiscoveryContext with extracted intelligence

        Note:
            Falls back to rule-based analysis on LLM failure
        """
        try:
            return await self._analyze_with_llm(
                phase3_result=phase3_result,
                failure_cause=failure_cause,
                target_responses=target_responses,
                iteration_history=iteration_history,
                tried_converters=tried_converters,
                objective=objective,
                recon_intelligence=recon_intelligence,
                config=config,
            )
        except Exception as e:
            self.logger.warning(f"LLM analysis failed: {e}, using rule-based fallback")
            return self._rule_based_fallback.analyze(
                phase3_result=phase3_result,
                failure_cause=failure_cause,
                target_responses=target_responses,
                iteration_history=iteration_history,
                tried_converters=tried_converters,
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
        config: dict | None,
    ) -> ChainDiscoveryContext:
        """
        Perform LLM-powered failure analysis.

        Args:
            phase3_result: Phase 3 attack result
            failure_cause: Why the iteration failed
            target_responses: Raw responses from target
            iteration_history: Previous iterations
            tried_converters: All chains attempted
            objective: Attack objective
            recon_intelligence: Structured recon data for context-aware analysis
            config: LangChain config

        Returns:
            ChainDiscoveryContext converted from LLM decision

        Raises:
            ValueError: If LLM fails to produce structured output
        """
        user_prompt = build_failure_analysis_user_prompt(
            phase3_result=phase3_result,
            failure_cause=failure_cause,
            target_responses=target_responses,
            iteration_history=iteration_history,
            tried_converters=tried_converters,
            objective=objective,
            recon_intelligence=recon_intelligence,
        )

        self.logger.info("[FailureAnalyzerAgent] Analyzing failure via LLM")
        self.logger.info(f"  Responses: {len(target_responses)}")
        self.logger.info(f"  History: {len(iteration_history)} iterations")

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

        self.logger.info(f"  Detected {len(decision.detected_defenses)} defense signals")
        self.logger.info(f"  Root cause: {decision.primary_failure_cause[:80]}...")
        self.logger.info(f"  Confidence: {decision.analysis_confidence:.2f}")

        # Convert to ChainDiscoveryContext for compatibility
        return self._convert_to_chain_discovery_context(
            decision=decision,
            iteration_history=iteration_history,
            tried_converters=tried_converters,
        )

    def _convert_to_chain_discovery_context(
        self,
        decision: FailureAnalysisDecision,
        iteration_history: list[dict[str, Any]],
        tried_converters: list[list[str]],
    ) -> ChainDiscoveryContext:
        """
        Convert FailureAnalysisDecision to ChainDiscoveryContext.

        Maintains compatibility with existing adapt_node integration.

        Args:
            decision: LLM failure analysis decision
            iteration_history: Previous iterations
            tried_converters: All chains attempted

        Returns:
            ChainDiscoveryContext with converted fields
        """
        # Extract defense signal types
        defense_signals = [d.defense_type for d in decision.detected_defenses]

        # Add encoding confusion signal if detected
        if "target_cannot_decode" in decision.primary_failure_cause.lower():
            defense_signals.append("target_cannot_decode")

        # Determine defense evolution from pattern analysis
        defense_evolution = self._classify_defense_evolution(
            decision.pattern_across_iterations,
            decision.defense_adaptation_observed,
        )

        # Compute converter effectiveness from history
        converter_effectiveness = self._compute_converter_effectiveness(iteration_history)

        # Map recommendations to unexplored directions
        unexplored_directions = decision.specific_recommendations[:5]

        # Map to required properties based on analysis
        required_properties = self._extract_required_properties(decision)

        # Find best score and chain
        best_score, best_chain = self._find_best_result(iteration_history)

        return ChainDiscoveryContext(
            defense_signals=defense_signals,
            failure_root_cause=decision.primary_failure_cause,
            defense_evolution=defense_evolution,
            converter_effectiveness=converter_effectiveness,
            unexplored_directions=unexplored_directions,
            required_properties=required_properties,
            iteration_count=len(iteration_history),
            best_score_achieved=best_score,
            best_chain_so_far=best_chain,
        )

    def _classify_defense_evolution(
        self,
        pattern: str,
        adaptation: str,
    ) -> str:
        """
        Classify defense evolution from LLM analysis.

        Args:
            pattern: Pattern across iterations from LLM
            adaptation: Defense adaptation observed from LLM

        Returns:
            Evolution classification string
        """
        pattern_lower = pattern.lower()
        adaptation_lower = adaptation.lower()

        if any(w in pattern_lower for w in ["strengthen", "harder", "more"]):
            return "defenses_strengthening"

        if any(w in pattern_lower for w in ["weaken", "gap", "opportunity"]):
            return "finding_weakness"

        if any(w in adaptation_lower for w in ["learning", "adapting", "improving"]):
            return "defenses_strengthening"

        if any(w in pattern_lower for w in ["stuck", "same", "plateau"]):
            return "stuck_in_local_optimum"

        if any(w in pattern_lower for w in ["improv", "progress", "better"]):
            return "finding_weakness"

        return "exploring"

    def _compute_converter_effectiveness(
        self,
        iteration_history: list[dict[str, Any]],
    ) -> dict[str, float]:
        """
        Compute effectiveness score for each tried converter chain.

        Args:
            iteration_history: Previous iteration outcomes

        Returns:
            Dict mapping chain key to effectiveness score
        """
        effectiveness = {}

        for iteration in iteration_history:
            converters = iteration.get("converters")
            converters = converters if converters is not None else []
            score = iteration.get("score", 0.0)
            is_successful = iteration.get("is_successful", False)

            chain_key = ",".join(converters) if converters else "none"

            if chain_key not in effectiveness:
                effectiveness[chain_key] = score
            else:
                effectiveness[chain_key] = (effectiveness[chain_key] + score) / 2

            if is_successful:
                effectiveness[chain_key] = max(effectiveness[chain_key], 0.9)

        return effectiveness

    def _extract_required_properties(
        self,
        decision: FailureAnalysisDecision,
    ) -> list[str]:
        """
        Extract required properties from LLM decision.

        Args:
            decision: LLM failure analysis decision

        Returns:
            List of required properties for next chain
        """
        properties = []

        # Extract from defense signals
        for defense in decision.detected_defenses:
            if defense.defense_type == "keyword_filter":
                properties.append("keyword_obfuscation")
            elif defense.defense_type == "pattern_matching":
                properties.append("structure_breaking")
            elif defense.defense_type == "explicit_refusal":
                properties.append("semantic_preservation")
            elif defense.defense_type == "encoding_confusion":
                properties.append("visual_only_converters")

        # Extract from exploitation opportunity
        if "partial" in decision.exploitation_opportunity.lower():
            properties.append("build_on_partial_success")

        if "gap" in decision.exploitation_opportunity.lower():
            properties.append("exploit_identified_gap")

        # Extract from recommended approach
        if "radical" in decision.recommended_approach.lower():
            properties.append("radical_change_needed")

        if "refine" in decision.recommended_approach.lower():
            properties.append("incremental_improvement")

        return list(set(properties))

    def _find_best_result(
        self,
        iteration_history: list[dict[str, Any]],
    ) -> tuple[float, list[str]]:
        """
        Find the best score and corresponding chain from history.

        Args:
            iteration_history: Previous iteration outcomes

        Returns:
            Tuple of (best_score, best_chain)
        """
        best_score = 0.0
        best_chain: list[str] = []

        for iteration in iteration_history:
            score = iteration.get("score", 0.0)
            if score > best_score:
                best_score = score
                converters = iteration.get("converters")
                best_chain = converters if converters is not None else []

        return best_score, best_chain
