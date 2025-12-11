"""
LangGraph definition for Swarm scanning workflow.

Purpose: Define the scanning workflow as a state machine
Dependencies: langgraph, graph.state, graph.nodes

Simplified flow: load_recon -> plan -> execute -> persist (loop for each agent)
"""

import logging
from typing import Literal, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from .state import SwarmState
from .nodes import (
    load_recon,
    plan_agent,
    execute_agent,
    persist_results,
)

logger = logging.getLogger(__name__)


def route_after_recon(state: SwarmState) -> Literal["plan", "persist"]:
    """Route after recon loading.

    Goes to plan if agents to process, otherwise persist.
    """
    if state.cancelled:
        return "persist"
    if state.has_fatal_error:
        return "persist"
    if state.is_complete:
        return "persist"
    return "plan"


def route_after_plan(state: SwarmState) -> Literal["execute", "plan", "persist"]:
    """Route after planning phase.

    If planning failed or cancelled, move to next agent or persist.
    Otherwise proceed to execution.
    """
    if state.cancelled:
        return "persist"

    # Check if planning failed (current_plan would be None)
    if state.current_plan is None:
        if state.is_complete:
            return "persist"
        return "plan"

    return "execute"


def route_after_execute(state: SwarmState) -> Literal["plan", "persist"]:
    """Route after execution phase.

    Continue to next agent or persist if all done or cancelled.
    """
    if state.cancelled:
        return "persist"

    if state.is_complete:
        return "persist"
    return "plan"


def build_swarm_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> CompiledStateGraph:
    """Build the Swarm scanning graph with optional checkpointing.

    Simplified graph structure:
    ```
    START -> load_recon -> plan -> execute -> plan (loop for each agent)
                |                     |
                v                     v
             persist <---------------+
                |
               END
    ```

    Args:
        checkpointer: Optional checkpointer for state persistence.

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(SwarmState)

    # Add nodes
    graph.add_node("load_recon", load_recon)
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
            "plan": "plan",
            "persist": "persist",
        },
    )

    graph.add_conditional_edges(
        "plan",
        route_after_plan,
        {
            "execute": "execute",
            "plan": "plan",
            "persist": "persist",
        },
    )

    graph.add_conditional_edges(
        "execute",
        route_after_execute,
        {
            "plan": "plan",
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
