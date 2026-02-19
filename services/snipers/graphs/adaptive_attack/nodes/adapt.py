"""
Adapt Node - LLM-Powered Parameter Adaptation with Chain Discovery.

Purpose: Single source of truth for chain selection and strategy adaptation
Role: Runs BEFORE iteration 0 and AFTER each failure to select chains dynamically
Dependencies: StrategyGenerator, ResponseAnalyzer, FailureAnalyzer, ChainDiscoveryAgent
"""

import logging
from typing import Any

from libs.monitoring import CallbackHandler
from services.snipers.graphs.adaptive_attack.state import (
    AdaptiveAttackState,
    FRAMING_TYPES,
    CONVERTER_CHAINS,
)
from services.snipers.graphs.adaptive_attack.components.response_analyzer import ResponseAnalyzer
from services.snipers.graphs.adaptive_attack.components.failure_analyzer import FailureAnalyzer
from services.snipers.graphs.adaptive_attack.components.turn_logger import get_turn_logger
from services.snipers.graphs.adaptive_attack.agents.strategy_generator import StrategyGenerator
from services.snipers.graphs.adaptive_attack.agents.failure_analyzer_agent import FailureAnalyzerAgent
from services.snipers.graphs.adaptive_attack.agents.chain_discovery_agent import ChainDiscoveryAgent
from services.snipers.core.phases.articulation.models.tool_intelligence import ReconIntelligence

logger = logging.getLogger(__name__)


async def adapt_node(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    LLM-powered adaptation based on response analysis.

    Async implementation with fallback to rule-based logic.

    Args:
        state: Current adaptive attack state

    Returns:
        State updates with new parameters and strategy
    """
    try:
        return await _adapt_node_async(state)
    except Exception as e:
        logger.warning(f"LLM adaptation failed: {e}, using rule-based fallback")
        return _rule_based_adapt(state)


async def _adapt_node_async(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    Async implementation of LLM-powered adaptation with chain discovery.

    Flow:
    - Pre-iteration (iteration 0, no history): Use initial chain selection
    - Post-iteration (has history): Full LLM-powered adaptation
    """
    iteration = state.get("iteration", 0)
    history = state.get("iteration_history", [])
    phase3_result = state.get("phase3_result")

    # === PRE-ITERATION CHAIN SELECTION (iteration 0) ===
    # If no history and no phase3_result, this is the initial call before iteration 0
    if iteration == 0 and not history and phase3_result is None:
        return await _initial_chain_selection(state)

    # === ADAPTIVE CHAIN SELECTION (iteration 1+) ===
    responses = state.get("target_responses", [])
    tried_framings = state.get("tried_framings", [])
    tried_converters = state.get("tried_converters", [])
    phase1_result = state.get("phase1_result")
    failure_cause = state.get("failure_cause")

    # Extract objective from phase1 result
    objective = "test security boundaries"
    if phase1_result and hasattr(phase1_result, "garak_objective"):
        objective = phase1_result.garak_objective or objective

    logger.info("\n[Adaptation] LLM-powered strategy generation with chain discovery")

    # === Step 0: Extract recon intelligence from phase1 result ===
    recon_intelligence = _extract_recon_intelligence(phase1_result)
    if recon_intelligence:
        logger.info(f"  Recon intelligence available: {recon_intelligence.target_self_description or 'no description'}")
        logger.info(f"    Tools: {len(recon_intelligence.tools)}, Filters: {len(recon_intelligence.content_filters)}")
    else:
        logger.info("  No recon intelligence available")

    # === BYPASS KNOWLEDGE INTEGRATION (Non-invasive) ===
    # Query historical episodes for similar defenses
    # Logs locally regardless of config, only queries S3 if enabled
    try:
        from services.snipers.knowledge.integration import get_adapt_hook
        history_context = await get_adapt_hook().query_history(dict(state))
    except Exception as e:
        logger.debug(f"Bypass knowledge query skipped: {e}")
        history_context = None
    # ===================================================

    # === Step 1: Pre-analyze responses (rule-based) ===
    analyzer = ResponseAnalyzer()
    pre_analysis = analyzer.analyze(responses)
    logger.info(f"  Pre-analysis: {pre_analysis.get('tone', 'unknown')} tone, "
                f"{len(pre_analysis.get('refusal_keywords', []))} refusal keywords")

    # === Step 2: Extract failure intelligence (agentic) ===
    failure_analyzer = FailureAnalyzerAgent()
    failure_handler = CallbackHandler()
    chain_discovery_context = await failure_analyzer.analyze(
        phase3_result=phase3_result,
        failure_cause=failure_cause,
        target_responses=responses,
        iteration_history=history,
        tried_converters=tried_converters,
        objective=objective,
        recon_intelligence=recon_intelligence,
        config={"callbacks": [failure_handler], "run_name": "FailureAnalysis"},
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
        recon_intelligence=recon_intelligence,
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
    generator = StrategyGenerator()
    strategy_handler = CallbackHandler()

    # Build config with recon intelligence (convert to dict for strategy generator)
    config = {
        "callbacks": [strategy_handler],
        "run_name": "StrategyGenerator",
    }
    if recon_intelligence:
        config["recon_intelligence"] = recon_intelligence.model_dump()
        logger.info(f"  Passing recon intelligence to strategy generator (target: {recon_intelligence.target_self_description or 'unknown'})")

    # Inject historical context if available and confident enough
    if history_context and history_context.should_inject:
        config["historical_context"] = history_context.to_prompt_context()
        logger.info(f"  Injecting historical context (confidence: {history_context.confidence:.2f})")

    decision = await generator.generate(
        responses=responses,
        iteration_history=history,
        tried_framings=tried_framings,
        tried_converters=tried_converters,
        objective=objective,
        pre_analysis=pre_analysis,
        config=config,
        chain_discovery_context=chain_discovery_context,
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
        # Bypass knowledge context (for observability)
        "history_context": history_context.model_dump() if history_context else None,
        "error": None,
        "next_node": "articulate",
    }


async def _initial_chain_selection(state: AdaptiveAttackState) -> dict[str, Any]:
    """
    Initial chain selection before iteration 0.

    Uses default chain since no failure data exists yet.
    This ensures adapt_node is the single source of truth for chain selection.
    Does NOT force preset framing - allows recon/custom framing to be selected
    by strategy generator in subsequent iterations.

    Args:
        state: Current adaptive attack state (iteration 0, no history)

    Returns:
        State updates with initial chain and framing
    """
    logger.info("\n[Pre-Iteration] Initial chain selection (no history)")

    # Use a sensible default chain for first iteration
    # rot13 is lightweight and provides basic obfuscation
    default_chain = ["rot13"]

    # For initial iteration, use default framing but don't lock it
    # Strategy generator will be able to override in subsequent iterations
    default_framing = FRAMING_TYPES[0] if FRAMING_TYPES else "qa_testing"

    logger.info(f"  Initial chain: {default_chain}")
    logger.info(f"  Initial framing: {default_framing}")
    logger.info("  Note: Recon/custom framing will take priority in subsequent iterations")

    return {
        "converter_names": default_chain,
        "framing_types": [default_framing],
        "adaptation_reasoning": "Initial chain selection (no history available)",
        "adaptation_actions": ["initial_chain_selected"],
        "tried_converters": [default_chain],
        "tried_framings": [default_framing],
        "custom_framing": None,
        "recon_custom_framing": None,
        "payload_guidance": None,  # No guidance for first iteration
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


def _extract_recon_intelligence(phase1_result: Any) -> ReconIntelligence | None:
    """
    Extract ReconIntelligence from phase1 result.

    Args:
        phase1_result: Phase 1 articulation result containing context_summary

    Returns:
        ReconIntelligence model or None if not available
    """
    if not phase1_result:
        return None

    if not hasattr(phase1_result, "context_summary"):
        return None

    context_summary = phase1_result.context_summary
    if not isinstance(context_summary, dict):
        return None

    recon_intel_dict = context_summary.get("recon_intelligence")
    if not recon_intel_dict:
        return None

    try:
        return ReconIntelligence(**recon_intel_dict)
    except Exception as e:
        logger.warning(f"Failed to parse recon intelligence: {e}")
        return None
