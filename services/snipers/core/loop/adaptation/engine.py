"""LLM-powered adaptation between attack iterations."""

import logging
from typing import Any

from libs.monitoring import CallbackHandler
from services.snipers.core.agents.chain_discovery_agent import ChainDiscoveryAgent
from services.snipers.core.agents.failure_analyzer_agent import FailureAnalyzerAgent
from services.snipers.core.agents.strategy_generator import StrategyGenerator
from services.snipers.models import Phase1Result, Phase3Result

logger = logging.getLogger(__name__)


def extract_recon_intelligence(phase1_result: Phase1Result | None):
    """Extract ReconIntelligence from phase1 context_summary."""
    if not phase1_result or not hasattr(phase1_result, "context_summary"):
        return None
    context = phase1_result.context_summary
    if not isinstance(context, dict):
        return None
    recon_dict = context.get("recon_intelligence")
    if not recon_dict:
        return None
    try:
        from services.snipers.core.phases.articulation.models.tool_intelligence import (
            ReconIntelligence,
        )
        return ReconIntelligence(**recon_dict)
    except Exception as e:
        logger.warning(f"Failed to parse recon intelligence: {e}")
        return None


def extract_swarm_context(phase1_result: Phase1Result | None) -> dict | None:
    """Extract swarm intelligence (garak) from phase1 context_summary."""
    if not phase1_result or not hasattr(phase1_result, "context_summary"):
        return None
    context = phase1_result.context_summary
    if not isinstance(context, dict):
        return None
    return context.get("swarm_context") or None


async def run_adaptation(
    phase3_result: Phase3Result | None,
    failure_cause: str,
    target_responses: list[str],
    iteration_history: list[dict[str, Any]],
    tried_converters: list[list[str]],
    tried_framings: list[str],
    phase1_result: Phase1Result | None,
    discovered_parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run LLM-powered adaptation: FailureAnalyzer -> ChainDiscovery -> Strategy."""
    objective = "test security boundaries"
    if phase1_result and hasattr(phase1_result, "garak_objective"):
        objective = phase1_result.garak_objective or objective
    recon_intelligence = extract_recon_intelligence(phase1_result)
    swarm_context = extract_swarm_context(phase1_result)

    chain_context = await _run_failure_analysis(
        phase3_result, failure_cause, target_responses,
        iteration_history, tried_converters, objective, recon_intelligence,
        swarm_context=swarm_context,
    )
    selection = await _run_chain_discovery(
        chain_context, tried_converters, objective, recon_intelligence,
    )
    decision = await _run_strategy_generation(
        target_responses, iteration_history, tried_framings,
        tried_converters, objective, recon_intelligence, chain_context,
        discovered_parameters,
    )

    return _build_adaptation_result(decision, selection)


async def _run_failure_analysis(
    phase3_result, failure_cause, target_responses,
    iteration_history, tried_converters, objective, recon_intelligence,
    swarm_context: dict | None = None,
):
    agent = FailureAnalyzerAgent()
    return await agent.analyze(
        phase3_result=phase3_result,
        failure_cause=failure_cause,
        target_responses=target_responses,
        iteration_history=iteration_history,
        tried_converters=tried_converters,
        objective=objective,
        recon_intelligence=recon_intelligence,
        swarm_context=swarm_context,
        config={"callbacks": [CallbackHandler()], "run_name": "FailureAnalysis"},
    )


async def _run_chain_discovery(
    chain_context, tried_converters, objective, recon_intelligence,
):
    agent = ChainDiscoveryAgent()
    chain_decision = await agent.generate(
        context=chain_context,
        tried_converters=tried_converters,
        objective=objective,
        recon_intelligence=recon_intelligence,
        config={"callbacks": [CallbackHandler()], "run_name": "ChainDiscovery"},
    )
    return agent.select_best_chain(chain_decision, chain_context)


async def _run_strategy_generation(
    target_responses, iteration_history, tried_framings,
    tried_converters, objective, recon_intelligence, chain_context,
    discovered_parameters=None,
):
    generator = StrategyGenerator()
    gen_config: dict[str, Any] = {
        "callbacks": [CallbackHandler()],
        "run_name": "StrategyGenerator",
    }
    if recon_intelligence:
        gen_config["recon_intelligence"] = recon_intelligence.model_dump()

    return await generator.generate(
        responses=target_responses,
        iteration_history=iteration_history,
        tried_framings=tried_framings,
        tried_converters=tried_converters,
        objective=objective,
        pre_analysis={},
        config=gen_config,
        chain_discovery_context=chain_context,
        discovered_parameters=discovered_parameters,
    )


def _build_adaptation_result(decision, selection) -> dict[str, Any]:
    discovered_params = getattr(decision, "discovered_parameters", {})
    custom_framing = _extract_custom_framing(decision)
    recon_custom_framing = _extract_recon_framing(decision)
    framing_types = (
        [decision.preset_framing]
        if not decision.use_custom_framing and decision.preset_framing else None
    )
    return {
        "converter_names": selection.selected_chain,
        "framing_types": framing_types,
        "custom_framing": custom_framing,
        "recon_custom_framing": recon_custom_framing,
        "payload_guidance": decision.payload_adjustments,
        "adaptation_reasoning": decision.reasoning,
        "discovered_parameters": discovered_params,
        "avoid_terms": getattr(decision, "avoid_terms", []) or [],
        "emphasize_terms": getattr(decision, "emphasize_terms", []) or [],
    }


def _extract_custom_framing(decision) -> dict | None:
    if not (decision.use_custom_framing and decision.custom_framing):
        return None
    cf = decision.custom_framing
    return {"name": cf.name, "system_context": cf.system_context,
            "user_prefix": cf.user_prefix, "user_suffix": cf.user_suffix}


def _extract_recon_framing(decision) -> dict | None:
    if not decision.recon_custom_framing:
        return None
    rcf = decision.recon_custom_framing
    return {"role": rcf.role, "context": rcf.context, "justification": rcf.justification}
