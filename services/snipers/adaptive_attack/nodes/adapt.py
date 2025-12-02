"""
Adapt Node - LLM-Powered Parameter Adaptation with Chain Discovery.

Purpose: Analyze responses and generate intelligent adaptation strategy
Role: Integrate failure analysis and chain discovery for dynamic chain generation
Dependencies: StrategyGenerator, ResponseAnalyzer, FailureAnalyzer, ChainDiscoveryAgent
"""

import asyncio
import logging
from typing import Any

from libs.monitoring import CallbackHandler
from services.snipers.adaptive_attack.state import (
    AdaptiveAttackState,
    FRAMING_TYPES,
    CONVERTER_CHAINS,
)
from services.snipers.adaptive_attack.components.response_analyzer import ResponseAnalyzer
from services.snipers.adaptive_attack.components.strategy_generator import StrategyGenerator
from services.snipers.adaptive_attack.components.failure_analyzer import FailureAnalyzer
from services.snipers.adaptive_attack.components.chain_discovery_agent import ChainDiscoveryAgent
from services.snipers.adaptive_attack.components.turn_logger import get_turn_logger

logger = logging.getLogger(__name__)


def adapt_node(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    LLM-powered adaptation based on response analysis.

    Wraps async implementation with fallback to rule-based logic.

    Args:
        state: Current adaptive attack state

    Returns:
        State updates with new parameters and strategy
    """
    try:
        return asyncio.run(_adapt_node_async(state))
    except Exception as e:
        logger.warning(f"LLM adaptation failed: {e}, using rule-based fallback")
        return _rule_based_adapt(state)


async def _adapt_node_async(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    Async implementation of LLM-powered adaptation with chain discovery.

    Flow:
    1. Extract failure intelligence via FailureAnalyzer
    2. Generate chain candidates via ChainDiscoveryAgent
    3. Generate overall strategy via StrategyGenerator (with chain candidates)
    4. Return state updates with selected chain and reasoning
    """
    responses = state.get("target_responses", [])
    history = state.get("iteration_history", [])
    tried_framings = state.get("tried_framings", [])
    tried_converters = state.get("tried_converters", [])
    phase1_result = state.get("phase1_result")
    phase3_result = state.get("phase3_result")
    failure_cause = state.get("failure_cause")

    # Extract objective from phase1 result
    objective = "test security boundaries"
    if phase1_result and hasattr(phase1_result, "garak_objective"):
        objective = phase1_result.garak_objective or objective

    logger.info("\n[Adaptation] LLM-powered strategy generation with chain discovery")

    # === Step 1: Pre-analyze responses (rule-based) ===
    analyzer = ResponseAnalyzer()
    pre_analysis = analyzer.analyze(responses)
    logger.info(f"  Pre-analysis: {pre_analysis.get('tone', 'unknown')} tone, "
                f"{len(pre_analysis.get('refusal_keywords', []))} refusal keywords")

    # === Step 2: Extract failure intelligence ===
    failure_analyzer = FailureAnalyzer()
    chain_discovery_context = failure_analyzer.analyze(
        phase3_result=phase3_result,
        failure_cause=failure_cause,
        target_responses=responses,
        iteration_history=history,
        tried_converters=tried_converters,
    )
    logger.info(f"  Chain discovery context: {len(chain_discovery_context.defense_signals)} signals, "
                f"root cause: {chain_discovery_context.failure_root_cause[:50]}...")

    # === Step 3: Generate chain candidates via ChainDiscoveryAgent ===
    chain_agent = ChainDiscoveryAgent()
    chain_handler = CallbackHandler()
    chain_decision = await chain_agent.generate(
        context=chain_discovery_context,
        tried_converters=tried_converters,
        objective=objective,
        config={"callbacks": [chain_handler], "run_name": "ChainDiscovery"},
    )
    logger.info(f"  Chain discovery: {len(chain_decision.chains)} candidates generated")

    # Select best chain from candidates (returns full observability)
    chain_selection_result = chain_agent.select_best_chain(chain_decision, chain_discovery_context)
    selected_chain = chain_selection_result.selected_chain
    logger.info(f"  Selected chain: {selected_chain}")
    logger.info(f"  Selection method: {chain_selection_result.selection_method}")
    logger.info(f"  Selection reasoning: {chain_selection_result.selection_reasoning[:100]}...")

    # === Step 4: Generate overall strategy via StrategyGenerator ===
    # Extract recon intelligence from phase1 result for custom framing
    recon_intelligence = None
    if phase1_result and hasattr(phase1_result, "context_summary"):
        # Try to get recon intelligence from context summary
        context_summary = phase1_result.context_summary
        if isinstance(context_summary, dict):
            recon_intel_dict = context_summary.get("recon_intelligence")
            if recon_intel_dict:
                recon_intelligence = recon_intel_dict

    generator = StrategyGenerator()
    strategy_handler = CallbackHandler()

    # Build config with recon intelligence
    config = {
        "callbacks": [strategy_handler],
        "run_name": "StrategyGenerator",
    }
    if recon_intelligence:
        config["recon_intelligence"] = recon_intelligence
        logger.info(f"  Passing recon intelligence to strategy generator (target: {recon_intelligence.get('target_self_description', 'unknown')})")

    decision = await generator.generate(
        responses=responses,
        iteration_history=history,
        tried_framings=tried_framings,
        tried_converters=tried_converters,
        objective=objective,
        pre_analysis=pre_analysis,
        config=config,
    )

    # Log decision
    logger.info(f"  Strategy: custom_framing={decision.use_custom_framing}, "
                f"confidence={decision.confidence:.2f}")
    if decision.use_custom_framing and decision.custom_framing:
        logger.info(f"  Custom framing: {decision.custom_framing.name}")
    else:
        logger.info(f"  Preset framing: {decision.preset_framing}")
    logger.info(f"  Final converters: {selected_chain}")
    logger.info(f"  Reasoning: {decision.reasoning[:100]}...")

    # Log adaptation to JSON file
    iteration = state.get("iteration", 0)
    new_framing = decision.custom_framing.model_dump() if decision.use_custom_framing and decision.custom_framing else decision.preset_framing
    get_turn_logger().log_adaptation(
        iteration=iteration,
        failure_cause=failure_cause or "unknown",
        defense_analysis=decision.defense_analysis.model_dump(),
        strategy_reasoning=decision.reasoning,
        new_framing=new_framing,
        new_converters=selected_chain,
        confidence=decision.confidence,
    )

    # Build custom_framing dict for PayloadArticulation
    custom_framing_dict = None
    if decision.use_custom_framing and decision.custom_framing:
        custom_framing_dict = {
            "name": decision.custom_framing.name,
            "system_context": decision.custom_framing.system_context,
            "user_prefix": decision.custom_framing.user_prefix,
            "user_suffix": decision.custom_framing.user_suffix,
        }

    # Build recon_custom_framing dict for recon-intelligence-based framing
    recon_custom_framing_dict = None
    if decision.recon_custom_framing:
        recon_custom_framing_dict = {
            "role": decision.recon_custom_framing.role,
            "context": decision.recon_custom_framing.context,
            "justification": decision.recon_custom_framing.justification,
        }
        logger.info(f"  Recon custom framing: {decision.recon_custom_framing.role} - {decision.recon_custom_framing.context}")

    # Update tried_converters with selected chain
    updated_tried_converters = list(tried_converters)
    if selected_chain and selected_chain not in updated_tried_converters:
        updated_tried_converters.append(selected_chain)

    return {
        "defense_analysis": decision.defense_analysis.model_dump(),
        "custom_framing": custom_framing_dict,
        "recon_custom_framing": recon_custom_framing_dict,
        "framing_types": [decision.preset_framing] if not decision.use_custom_framing and decision.preset_framing else None,
        "converter_names": selected_chain if selected_chain else None,
        "payload_guidance": decision.payload_adjustments,
        "adaptation_reasoning": decision.reasoning,
        "adaptation_actions": ["llm_strategy_generated"],
        "tried_converters": updated_tried_converters,
        # Chain discovery state with full observability
        "chain_discovery_context": chain_discovery_context,
        "chain_discovery_decision": chain_decision,
        "chain_selection_result": chain_selection_result,
        "error": None,
        "next_node": "articulate",
    }


def _rule_based_adapt(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    Fallback: Original rule-based adaptation logic.

    Used when LLM fails or times out.
    """
    failure_cause = state.get("failure_cause", "no_impact")
    tried_framings = state.get("tried_framings", [])
    tried_converters = state.get("tried_converters", [])
    payload_count = state.get("payload_count", 2)
    max_concurrent = state.get("max_concurrent", 3)

    logger.info(f"\n[Adaptation] Rule-based fallback for: {failure_cause}")

    adaptation_actions = []
    new_framing = None
    new_converters = None

    if failure_cause == "no_impact":
        adaptation_actions.append("change_framing")
        adaptation_actions.append("change_converters")

        for framing in FRAMING_TYPES:
            if framing not in tried_framings:
                new_framing = [framing]
                break

        for chain in CONVERTER_CHAINS:
            if chain not in tried_converters:
                new_converters = chain
                break

    elif failure_cause == "blocked":
        adaptation_actions.append("escalate_obfuscation")

        for chain in reversed(CONVERTER_CHAINS):
            if chain not in tried_converters:
                new_converters = chain
                break

    elif failure_cause == "partial_success":
        adaptation_actions.append("increase_payload_count")
        payload_count = min(payload_count + 1, 6)

    elif failure_cause == "rate_limited":
        adaptation_actions.append("reduce_concurrency")
        max_concurrent = max(1, max_concurrent - 1)

    elif failure_cause == "error":
        adaptation_actions.append("retry_same")

    logger.info(f"  Actions: {adaptation_actions}")
    logger.info(f"  New framing: {new_framing or 'unchanged'}")
    logger.info(f"  New converters: {new_converters or 'unchanged'}")

    return {
        "adaptation_actions": adaptation_actions,
        "framing_types": new_framing if new_framing else state.get("framing_types"),
        "converter_names": new_converters if new_converters else state.get("converter_names"),
        "payload_count": payload_count,
        "max_concurrent": max_concurrent,
        "custom_framing": None,  # Clear any previous custom framing
        "error": None,
        "next_node": "articulate",
    }
