"""
LangGraph definition for Swarm scanning workflow.

Purpose: Define the scanning workflow as a state machine
Dependencies: langgraph, graph.state, graph.nodes
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

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
    """
    if state.has_fatal_error:
        return "persist"
    if state.is_complete:
        return "persist"
    return "check_safety"


def route_after_safety(state: SwarmState) -> Literal["plan", "check_safety", "persist"]:
    """Route after safety check.

    If agent was blocked, move to next agent.
    Otherwise proceed to planning.
    """
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

    If planning failed, move to next agent.
    Otherwise proceed to execution.
    """
    # Check if planning failed (current_plan would be None)
    if state.current_plan is None:
        if state.is_complete:
            return "persist"
        return "check_safety"

    return "execute"


def route_after_execute(state: SwarmState) -> Literal["check_safety", "persist"]:
    """Route after execution phase.

    Continue to next agent or persist if all done.
    """
    if state.is_complete:
        return "persist"
    return "check_safety"


def build_swarm_graph() -> StateGraph:
    """Build the Swarm scanning graph.

    Graph structure:
    ```
    START -> load_recon -> check_safety -> plan -> execute -> check_safety (loop)
                              |                       |
                              v                       v
                           persist <-----------------+
                              |
                             END
    ```

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

    return graph.compile()


# Singleton instance for reuse
_graph = None


def get_swarm_graph() -> StateGraph:
    """Get or create the Swarm graph singleton.

    Returns:
        Compiled LangGraph workflow
    """
    global _graph
    if _graph is None:
        logger.info("Building Swarm graph...")
        _graph = build_swarm_graph()
        logger.info("Swarm graph built successfully")
    return _graph
