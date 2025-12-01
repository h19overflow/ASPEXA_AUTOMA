"""
Adaptive Attack LangGraph.

Purpose: StateGraph for adaptive attack loop with conditional routing
Role: Orchestrates attack phases with feedback-driven adaptation
Dependencies: LangGraph, node implementations, state

Graph structure:
    START → articulate → convert → execute → evaluate → [adapt|END]
                                                  ↑         ↓
                                                  └─────────┘

Routing logic:
- evaluate → END: if is_successful or max_iterations reached
- evaluate → adapt: if failure, continue adapting
- adapt → articulate: restart attack with new parameters
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, START, END

from services.snipers.adaptive_attack.state import (
    AdaptiveAttackState,
    create_initial_state,
)
from services.snipers.adaptive_attack.nodes import (
    articulate_node,
    convert_node,
    execute_node,
    evaluate_node,
    adapt_node,
)
from services.snipers.adaptive_attack.components.turn_logger import (
    reset_turn_logger,
    get_turn_logger,
)

logger = logging.getLogger(__name__)


def route_after_evaluate(state: AdaptiveAttackState) -> Literal["adapt", "__end__"]:
    """
    Route after evaluation based on attack outcome.

    Args:
        state: Current state after evaluation

    Returns:
        "adapt" to continue adapting, "__end__" to complete
    """
    if state.get("completed", False):
        return END
    return "adapt"


def build_adaptive_attack_graph() -> StateGraph:
    """
    Build the adaptive attack StateGraph.

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph with state schema
    builder = StateGraph(AdaptiveAttackState)

    # Add nodes
    builder.add_node("articulate", articulate_node)
    builder.add_node("convert", convert_node)
    builder.add_node("execute", execute_node)
    builder.add_node("evaluate", evaluate_node)
    builder.add_node("adapt", adapt_node)

    # Add edges: linear flow through phases
    builder.add_edge(START, "articulate")
    builder.add_edge("articulate", "convert")
    builder.add_edge("convert", "execute")
    builder.add_edge("execute", "evaluate")

    # Conditional edge: evaluate decides to adapt or end
    builder.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "adapt": "adapt",
            END: END,
        }
    )

    # Adapt loops back to articulate
    builder.add_edge("adapt", "articulate")

    # Compile graph
    graph = builder.compile()

    return graph


# Singleton compiled graph
_compiled_graph = None


def get_adaptive_attack_graph() -> StateGraph:
    """
    Get or create the compiled adaptive attack graph.

    Returns:
        Compiled StateGraph (singleton)
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_adaptive_attack_graph()
    return _compiled_graph


async def run_adaptive_attack(
    campaign_id: str,
    target_url: str,
    max_iterations: int = 5,
    payload_count: int = 2,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
) -> AdaptiveAttackState:
    """
    Run adaptive attack loop.

    Executes the LangGraph until success or max iterations.

    Args:
        campaign_id: Campaign ID to load intelligence
        target_url: Target URL to attack
        max_iterations: Maximum adaptation iterations
        payload_count: Initial number of payloads
        framing_types: Initial framing types (None = auto)
        converter_names: Initial converters (None = auto)
        success_scorers: Scorers that must succeed (e.g., ["jailbreak"])
            Options: jailbreak, prompt_leak, data_leak, tool_abuse, pii_exposure
        success_threshold: Minimum confidence for success (0.0-1.0)

    Returns:
        Final AdaptiveAttackState with all results
    """
    logger.info("\n" + "=" * 70)
    logger.info("ADAPTIVE ATTACK LOOP")
    logger.info("=" * 70)
    logger.info(f"Campaign: {campaign_id}")
    logger.info(f"Target: {target_url}")
    logger.info(f"Max iterations: {max_iterations}")
    if success_scorers:
        logger.info(f"Success scorers: {success_scorers} >= {success_threshold}")
    logger.info("=" * 70 + "\n")

    # Reset turn logger for new run
    reset_turn_logger()

    # Create initial state
    initial_state = create_initial_state(
        campaign_id=campaign_id,
        target_url=target_url,
        max_iterations=max_iterations,
        payload_count=payload_count,
        framing_types=framing_types,
        converter_names=converter_names,
        success_scorers=success_scorers,
        success_threshold=success_threshold,
    )

    # Get compiled graph
    graph = get_adaptive_attack_graph()

    # Run graph to completion
    final_state = await graph.ainvoke(initial_state)

    # Log final results
    logger.info("\n" + "=" * 70)
    logger.info("ADAPTIVE ATTACK COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Success: {final_state.get('is_successful', False)}")
    logger.info(f"Iterations: {final_state.get('iteration', 0) + 1}")
    logger.info(f"Best score: {final_state.get('best_score', 0.0):.2f}")
    logger.info(f"Best iteration: {final_state.get('best_iteration', 0)}")
    logger.info("=" * 70 + "\n")

    # Log final result to turn logger
    get_turn_logger().log_result(
        is_successful=final_state.get("is_successful", False),
        total_iterations=final_state.get("iteration", 0) + 1,
        best_score=final_state.get("best_score", 0.0),
        best_iteration=final_state.get("best_iteration", 0),
    )

    return final_state
