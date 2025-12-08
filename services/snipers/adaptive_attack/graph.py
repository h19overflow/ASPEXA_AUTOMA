"""
Adaptive Attack LangGraph.

Purpose: StateGraph for adaptive attack loop with conditional routing
Role: Orchestrates attack phases with feedback-driven adaptation
Dependencies: LangGraph, node implementations, state

Graph structure:
    START → adapt → articulate → convert → execute → evaluate → [adapt|END]
               ↑                                          ↓
               └──────────────────────────────────────────┘

Routing logic:
- adapt → articulate: Generate strategy and select chain (single source of truth)
- evaluate → END: if is_successful or max_iterations reached
- evaluate → adapt: if failure, continue adapting
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, START, END
from libs.monitoring import CallbackHandler

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
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

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
    # adapt_node runs FIRST to select initial chain (single source of truth)
    builder.add_edge(START, "adapt")
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


def get_adaptive_attack_graph():
    """
    Get or create the compiled adaptive attack graph.

    Returns:
        Compiled graph (singleton)
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

    # Calculate recursion limit: 5 nodes per iteration + buffer
    # Each iteration visits: articulate → convert → execute → evaluate → adapt
    recursion_limit = (max_iterations * 5) + 10

    # Initialize Langfuse callback handler for tracing
    langfuse_handler = CallbackHandler()

    # Run graph to completion
    final_state = await graph.ainvoke(
        initial_state,
        config={
            "recursion_limit": recursion_limit,
            "callbacks": [langfuse_handler],
            "run_name": "AdaptiveAttack",
        },
    )

    # Log final result to turn logger
    get_turn_logger().log_result(
        is_successful=final_state.get("is_successful", False),
        total_iterations=final_state.get("iteration", 0) + 1,
        best_score=final_state.get("best_score", 0.0),
        best_iteration=final_state.get("best_iteration", 0),
    )

    return final_state


async def run_adaptive_attack_streaming(
    campaign_id: str,
    target_url: str,
    max_iterations: int = 5,
    payload_count: int = 2,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Run adaptive attack loop with streaming events.

    Yields SSE events for real-time monitoring of each iteration and phase.

    Args:
        campaign_id: Campaign ID to load intelligence
        target_url: Target URL to attack
        max_iterations: Maximum adaptation iterations
        payload_count: Initial number of payloads
        framing_types: Initial framing types (None = auto)
        converter_names: Initial converters (None = auto)
        success_scorers: Scorers that must succeed
        success_threshold: Minimum confidence for success

    Yields:
        Dict events for SSE streaming
    """
    def make_event(
        event_type: str,
        message: str,
        phase: str | None = None,
        iteration: int | None = None,
        data: dict | None = None,
        progress: float | None = None,
    ) -> dict[str, Any]:
        """Create a stream event dict."""
        return {
            "type": event_type,
            "phase": phase,
            "iteration": iteration,
            "message": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "progress": progress,
        }

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

    # Emit attack started
    yield make_event(
        "attack_started",
        f"Starting adaptive attack on {target_url}",
        data={
            "campaign_id": campaign_id,
            "target_url": target_url,
            "max_iterations": max_iterations,
            "payload_count": payload_count,
        },
    )

    # Get compiled graph
    graph = get_adaptive_attack_graph()

    # Calculate recursion limit: 5 nodes per iteration + buffer
    # Each iteration visits: articulate → convert → execute → evaluate → adapt
    recursion_limit = (max_iterations * 5) + 10

    # Initialize Langfuse callback handler for tracing
    langfuse_handler = CallbackHandler()

    # Track current iteration for events
    current_iteration = 0
    final_state = initial_state

    try:
        # Use astream to get intermediate states
        async for state_update in graph.astream(
            initial_state,
            config={
                "recursion_limit": recursion_limit,
                "callbacks": [langfuse_handler],
                "run_name": "AdaptiveAttackStream",
            },
        ):
            # state_update is a dict with node name -> output
            for node_name, node_output in state_update.items():
                # Merge updates into final_state tracking
                final_state = {**final_state, **node_output}
                # Emit node-specific events
                if node_name == "articulate":
                    current_iteration = node_output.get("iteration", current_iteration)

                    yield make_event(
                        "iteration_start",
                        f"Iteration {current_iteration + 1} started",
                        iteration=current_iteration + 1,
                        data={"iteration": current_iteration + 1, "max_iterations": max_iterations},
                    )

                    yield make_event(
                        "phase1_start",
                        "Phase 1: Payload Articulation",
                        phase="phase1",
                        iteration=current_iteration + 1,
                        progress=0.0,
                    )

                    # Check for errors first
                    if node_output.get("error"):
                        yield make_event(
                            "error",
                            f"Phase 1 failed: {node_output['error']}",
                            phase="phase1",
                            iteration=current_iteration + 1,
                            data={"error": node_output["error"], "node": "articulate"},
                        )

                    phase1_result = node_output.get("phase1_result")
                    if phase1_result:
                        # Emit each payload
                        for i, payload in enumerate(phase1_result.articulated_payloads):
                            yield make_event(
                                "payload_generated",
                                f"Generated payload {i + 1}",
                                phase="phase1",
                                iteration=current_iteration + 1,
                                data={
                                    "index": i,
                                    "payload": payload,
                                    "framing_type": phase1_result.framing_types_used[i] if i < len(phase1_result.framing_types_used) else None,
                                },
                                progress=(i + 1) / len(phase1_result.articulated_payloads),
                            )

                        yield make_event(
                            "phase1_complete",
                            f"Phase 1 complete: {len(phase1_result.articulated_payloads)} payloads",
                            phase="phase1",
                            iteration=current_iteration + 1,
                            data={
                                "payloads_count": len(phase1_result.articulated_payloads),
                                "framing_type": phase1_result.framing_type,
                                "framing_types_used": phase1_result.framing_types_used,
                            },
                            progress=1.0,
                        )

                elif node_name == "convert":
                    yield make_event(
                        "phase2_start",
                        "Phase 2: Payload Conversion",
                        phase="phase2",
                        iteration=current_iteration + 1,
                        progress=0.0,
                    )

                    # Check for errors first
                    if node_output.get("error"):
                        yield make_event(
                            "error",
                            f"Phase 2 failed: {node_output['error']}",
                            phase="phase2",
                            iteration=current_iteration + 1,
                            data={"error": node_output["error"], "node": "convert"},
                        )

                    phase2_result = node_output.get("phase2_result")
                    if phase2_result:
                        for i, converted in enumerate(phase2_result.payloads):
                            yield make_event(
                                "payload_converted",
                                f"Converted payload {i + 1}",
                                phase="phase2",
                                iteration=current_iteration + 1,
                                data={
                                    "index": i,
                                    "original": converted.original,
                                    "converted": converted.converted,
                                    "converters_applied": converted.converters_applied,
                                },
                                progress=(i + 1) / len(phase2_result.payloads),
                            )

                        yield make_event(
                            "phase2_complete",
                            f"Phase 2 complete: {phase2_result.success_count} converted",
                            phase="phase2",
                            iteration=current_iteration + 1,
                            data={
                                "converter_names": phase2_result.converter_names,
                                "success_count": phase2_result.success_count,
                                "error_count": phase2_result.error_count,
                            },
                            progress=1.0,
                        )

                elif node_name == "execute":
                    yield make_event(
                        "phase3_start",
                        f"Phase 3: Attacking {target_url}",
                        phase="phase3",
                        iteration=current_iteration + 1,
                        data={"target_url": target_url},
                        progress=0.0,
                    )

                    # Check for errors first
                    if node_output.get("error"):
                        yield make_event(
                            "error",
                            f"Phase 3 failed: {node_output['error']}",
                            phase="phase3",
                            iteration=current_iteration + 1,
                            data={"error": node_output["error"], "node": "execute"},
                        )

                    phase3_result = node_output.get("phase3_result")
                    if phase3_result:
                        total = len(phase3_result.attack_responses)
                        for i, resp in enumerate(phase3_result.attack_responses):
                            yield make_event(
                                "attack_sent",
                                f"Attack {i + 1}/{total} sent",
                                phase="phase3",
                                iteration=current_iteration + 1,
                                data={
                                    "index": i,
                                    "payload_index": resp.payload_index,
                                    "payload": resp.payload,
                                },
                                progress=(i + 0.5) / total,
                            )

                            yield make_event(
                                "response_received",
                                f"Response {i + 1}/{total} received",
                                phase="phase3",
                                iteration=current_iteration + 1,
                                data={
                                    "index": i,
                                    "status_code": resp.status_code,
                                    "latency_ms": resp.latency_ms,
                                    "response": resp.response,
                                    "error": resp.error,
                                },
                                progress=(i + 1) / total,
                            )

                        # Emit scorer results
                        for scorer_name, score_result in phase3_result.composite_score.scorer_results.items():
                            yield make_event(
                                "score_calculated",
                                f"Scorer '{scorer_name}': {score_result.severity.value}",
                                phase="phase3",
                                iteration=current_iteration + 1,
                                data={
                                    "scorer_name": scorer_name,
                                    "severity": score_result.severity.value,
                                    "confidence": score_result.confidence,
                                    "reasoning": getattr(score_result, 'reasoning', None),
                                },
                            )

                        yield make_event(
                            "phase3_complete",
                            f"Phase 3 complete: {'BREACH' if phase3_result.is_successful else 'Blocked'}",
                            phase="phase3",
                            iteration=current_iteration + 1,
                            data={
                                "is_successful": phase3_result.is_successful,
                                "overall_severity": phase3_result.overall_severity,
                                "total_score": phase3_result.total_score,
                            },
                            progress=1.0,
                        )

                elif node_name == "evaluate":
                    is_successful = node_output.get("is_successful", False)
                    total_score = node_output.get("total_score", 0.0)

                    yield make_event(
                        "iteration_complete",
                        f"Iteration {current_iteration + 1}: {'SUCCESS' if is_successful else 'blocked'}",
                        iteration=current_iteration + 1,
                        data={
                            "iteration": current_iteration + 1,
                            "is_successful": is_successful,
                            "total_score": total_score,
                            "best_score": node_output.get("best_score", 0.0),
                            "best_iteration": node_output.get("best_iteration", 0),
                        },
                    )

                elif node_name == "adapt":
                    adaptation_reasoning = node_output.get("adaptation_reasoning", "")
                    adaptation_actions = node_output.get("adaptation_actions", [])

                    yield make_event(
                        "adaptation",
                        "Adapting strategy for next iteration",
                        iteration=current_iteration + 1,
                        data={
                            "adaptation_actions": adaptation_actions,
                            "adaptation_reasoning": adaptation_reasoning[:500] if adaptation_reasoning else None,
                            "next_framing": node_output.get("framing_types"),
                            "next_converters": node_output.get("converter_names"),
                        },
                    )

        # Emit attack complete with full results
        phase3_result = final_state.get("phase3_result")
        phase1_result = final_state.get("phase1_result")
        phase2_result = final_state.get("phase2_result")

        yield make_event(
            "attack_complete",
            f"Adaptive attack complete: {'SUCCESS' if final_state.get('is_successful') else 'Target secure'}",
            data={
                "campaign_id": campaign_id,
                "target_url": target_url,
                "is_successful": final_state.get("is_successful", False),
                "total_iterations": final_state.get("iteration", 0) + 1,
                "best_score": final_state.get("best_score", 0.0),
                "best_iteration": final_state.get("best_iteration", 0),
                "overall_severity": final_state.get("overall_severity", "none"),
                "total_score": final_state.get("total_score", 0.0),
                "iteration_history": final_state.get("iteration_history", []),
                "adaptation_reasoning": final_state.get("adaptation_reasoning"),
                # Include phase data for final result
                "phase1": {
                    "framing_type": phase1_result.framing_type if phase1_result else "",
                    "framing_types_used": phase1_result.framing_types_used if phase1_result else [],
                    "payloads": phase1_result.articulated_payloads if phase1_result else [],
                } if phase1_result else None,
                "phase2": {
                    "converter_names": phase2_result.converter_names if phase2_result else [],
                    "payloads": [
                        {"original": p.original, "converted": p.converted, "converters_applied": p.converters_applied}
                        for p in phase2_result.payloads
                    ] if phase2_result else [],
                } if phase2_result else None,
                "phase3": {
                    "attack_responses": [
                        {
                            "payload_index": r.payload_index,
                            "payload": r.payload,
                            "response": r.response,
                            "status_code": r.status_code,
                            "latency_ms": r.latency_ms,
                            "error": r.error,
                        }
                        for r in phase3_result.attack_responses
                    ] if phase3_result else [],
                    "composite_score": {
                        "overall_severity": phase3_result.composite_score.overall_severity.value if phase3_result else "none",
                        "total_score": phase3_result.composite_score.total_score if phase3_result else 0.0,
                        "is_successful": phase3_result.composite_score.is_successful if phase3_result else False,
                        "scorer_results": {
                            name: {
                                "severity": sr.severity.value,
                                "confidence": sr.confidence,
                                "reasoning": getattr(sr, 'reasoning', None),
                            }
                            for name, sr in phase3_result.composite_score.scorer_results.items()
                        } if phase3_result else {},
                    } if phase3_result else None,
                } if phase3_result else None,
            },
        )

        # Log final result
        get_turn_logger().log_result(
            is_successful=final_state.get("is_successful", False),
            total_iterations=final_state.get("iteration", 0) + 1,
            best_score=final_state.get("best_score", 0.0),
            best_iteration=final_state.get("best_iteration", 0),
        )

    except Exception as e:
        logger.exception(f"Streaming adaptive attack failed: {e}")
        yield make_event(
            "error",
            f"Adaptive attack failed: {str(e)}",
            data={"error": str(e), "error_type": type(e).__name__},
        )
        raise
