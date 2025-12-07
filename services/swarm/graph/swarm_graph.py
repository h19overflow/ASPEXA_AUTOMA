"""
LangGraph definition for Swarm scanning workflow.

Purpose: Define the scanning workflow as a state machine
Dependencies: langgraph, graph.state, graph.nodes

Checkpointing:
- Optional checkpointer can be passed for state persistence
- When enabled, graph can resume from interruption point
"""

import logging
from typing import Literal, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from .state import SwarmState
from .nodes import (
    load_recon,
    check_safety,
    plan_agent,
    execute_agent,
    persist_results,
)

logger = logging.getLogger(__name__)


def route_after_recon(state: SwarmState) -> Literal["check_safety", "persist"]:
    """Route after recon loading.

    Goes to check_safety if agents to process, otherwise persist.
    Handles cancellation by routing to persist for partial results.
    """
    if state.cancelled:
        return "persist"
    if state.has_fatal_error:
        return "persist"
    if state.is_complete:
        return "persist"
    return "check_safety"


def route_after_safety(state: SwarmState) -> Literal["plan", "check_safety", "persist"]:
    """Route after safety check.

    If agent was blocked or cancelled, move to next agent or persist.
    Otherwise proceed to planning.
    """
    # Handle cancellation
    if state.cancelled:
        return "persist"

    # Check if we just blocked this agent (results were added)
    if state.agent_results:
        latest = state.agent_results[-1]
        if latest.status == "blocked":
            # Move to next agent
            if state.is_complete:
                return "persist"
            return "check_safety"

    return "plan"


def route_after_plan(state: SwarmState) -> Literal["execute", "check_safety", "persist"]:
    """Route after planning phase.

    If planning failed or cancelled, move to next agent or persist.
    Otherwise proceed to execution.
    """
    # Handle cancellation
    if state.cancelled:
        return "persist"

    # Check if planning failed (current_plan would be None)
    if state.current_plan is None:
        if state.is_complete:
            return "persist"
        return "check_safety"

    return "execute"


def route_after_execute(state: SwarmState) -> Literal["check_safety", "persist"]:
    """Route after execution phase.

    Continue to next agent or persist if all done or cancelled.
    """
    # Handle cancellation - persist partial results
    if state.cancelled:
        return "persist"

    if state.is_complete:
        return "persist"
    return "check_safety"


def build_swarm_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> CompiledStateGraph:
    """Build the Swarm scanning graph with optional checkpointing.

    Graph structure:
    ```
    START -> load_recon -> check_safety -> plan -> execute -> check_safety (loop)
                              |                       |
                              v                       v
                           persist <-----------------+
                              |
                             END
    ```

    Args:
        checkpointer: Optional checkpointer for state persistence.
            Enables resume from cancellation/interruption.

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(SwarmState)

    # Add nodes
    graph.add_node("load_recon", load_recon)
    graph.add_node("check_safety", check_safety)
    graph.add_node("plan", plan_agent)
    graph.add_node("execute", execute_agent)
    graph.add_node("persist", persist_results)

    # Entry point
    graph.set_entry_point("load_recon")

    # Edges with conditional routing
    graph.add_conditional_edges(
        "load_recon",
        route_after_recon,
        {
            "check_safety": "check_safety",
            "persist": "persist",
        },
    )

    graph.add_conditional_edges(
        "check_safety",
        route_after_safety,
        {
            "plan": "plan",
            "check_safety": "check_safety",
            "persist": "persist",
        },
    )

    graph.add_conditional_edges(
        "plan",
        route_after_plan,
        {
            "execute": "execute",
            "check_safety": "check_safety",
            "persist": "persist",
        },
    )

    graph.add_conditional_edges(
        "execute",
        route_after_execute,
        {
            "check_safety": "check_safety",
            "persist": "persist",
        },
    )

    # Terminal edge
    graph.add_edge("persist", END)

    return graph.compile(checkpointer=checkpointer)


# Singleton instance for reuse (without checkpointer)
_graph: Optional[CompiledStateGraph] = None


def get_swarm_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> CompiledStateGraph:
    """Get or create the Swarm graph.

    When checkpointer is provided, returns a fresh graph with checkpointing.
    Without checkpointer, returns cached singleton for performance.

    Args:
        checkpointer: Optional checkpointer for state persistence.

    Returns:
        Compiled LangGraph workflow
    """
    global _graph

    # If checkpointer requested, always build fresh graph
    if checkpointer is not None:
        logger.info("Building Swarm graph with checkpointer...")
        graph = build_swarm_graph(checkpointer)
        logger.info("Swarm graph with checkpointer built successfully")
        return graph

    # Use singleton for non-checkpointed graphs
    if _graph is None:
        logger.info("Building Swarm graph...")
        _graph = build_swarm_graph()
        logger.info("Swarm graph built successfully")
    return _graph
