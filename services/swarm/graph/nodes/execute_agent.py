"""
Execute agent node for Swarm graph.

Purpose: Execute probes using the scanner with streaming
Dependencies: services.swarm.garak_scanner, services.swarm.core.schema, swarm_observability
"""

import logging
from typing import Dict, Any, List

from services.swarm.graph.state import SwarmState, AgentResult
from services.swarm.garak_scanner import get_scanner
from services.swarm.garak_scanner.models import (
    ScanStartEvent,
    ProbeStartEvent,
    PromptResultEvent,
    ProbeCompleteEvent,
    ScanCompleteEvent,
    ScanErrorEvent,
)
from services.swarm.core.schema import ScanPlan
from services.swarm.swarm_observability import (
    EventType,
    create_event,
    get_cancellation_manager,
    safe_get_stream_writer,
)

logger = logging.getLogger(__name__)


async def execute_agent(state: SwarmState) -> Dict[str, Any]:
    """Execute probes for current agent using scanner.

    Node: EXECUTE_AGENT
    Runs the scanner with the plan from planning phase.
    Includes cancellation checks between probes for graceful stopping.

    Args:
        state: Current graph state with current_plan

    Returns:
        Dict with agent_results and events from execution
    """
    writer = safe_get_stream_writer()
    manager = get_cancellation_manager(state.audit_id)
    agent_type = state.current_agent
    events = []
    probe_results_list: List[Dict[str, Any]] = []

    # Calculate base progress for this agent
    base_progress = state.current_agent_index / max(state.total_agents, 1)
    agent_progress_share = 0.9 / state.total_agents  # 90% for execution

    # Emit NODE_ENTER
    writer(create_event(
        EventType.NODE_ENTER,
        node="execute_agent",
        agent=agent_type,
        message=f"Starting execution for {agent_type}",
        progress=base_progress + 0.1 / state.total_agents,
    ).model_dump())

    # Check cancellation before execution
    if await manager.checkpoint():
        writer(create_event(
            EventType.SCAN_CANCELLED,
            node="execute_agent",
            agent=agent_type,
            message="Scan cancelled by user before execution",
        ).model_dump())
        return {"cancelled": True, "events": events}

    # Verify plan exists
    if not state.current_plan:
        logger.error(f"[{agent_type}] No plan available for execution")
        writer(create_event(
            EventType.NODE_EXIT,
            node="execute_agent",
            agent=agent_type,
            message="No plan available for execution",
        ).model_dump())
        return {
            "agent_results": [AgentResult(
                agent_type=agent_type,
                status="failed",
                error="No plan available for execution",
                phase="execution",
            )],
            "events": [{
                "type": "error",
                "agent": agent_type,
                "phase": "execution",
                "message": "No plan available",
            }],
            "current_agent_index": state.current_agent_index + 1,
            "current_plan": None,
        }

    events.append({
        "type": "execution_start",
        "agent": agent_type,
    })

    events.append({
        "type": "log",
        "message": f"[{agent_type}] Executing scan with streaming...",
    })

    # Reconstruct ScanPlan from dict
    try:
        plan = ScanPlan(**state.current_plan)
    except Exception as e:
        logger.error(f"[{agent_type}] Invalid plan structure: {e}")
        return {
            "agent_results": [AgentResult(
                agent_type=agent_type,
                status="error",
                error=f"Invalid plan: {e}",
                phase="execution",
            )],
            "events": events,
            "current_agent_index": state.current_agent_index + 1,
            "current_plan": None,
        }

    scan_id = f"garak-{state.audit_id}-{agent_type}"
    total_pass = 0
    total_fail = 0
    total_error = 0
    total_probes = 0
    current_probe_index = 0

    try:
        scanner = get_scanner()

        async for event in scanner.scan_with_streaming(plan):
            # Check cancellation between probe processing
            if await manager.checkpoint():
                # Save snapshot for potential resumption
                manager.save_snapshot({
                    "agent": agent_type,
                    "completed_probes": current_probe_index,
                    "results": probe_results_list,
                    "total_pass": total_pass,
                    "total_fail": total_fail,
                })
                writer(create_event(
                    EventType.SCAN_CANCELLED,
                    node="execute_agent",
                    agent=agent_type,
                    message=f"Scan cancelled after {current_probe_index} probes",
                    data={
                        "completed_probes": current_probe_index,
                        "partial_results": len(probe_results_list),
                    },
                ).model_dump())
                return {
                    "cancelled": True,
                    "agent_results": [AgentResult(
                        agent_type=agent_type,
                        status="cancelled",
                        scan_id=scan_id,
                        plan=state.current_plan,
                        results=probe_results_list,
                        vulnerabilities_found=total_fail,
                    )],
                    "events": events,
                    "current_agent_index": state.current_agent_index + 1,
                    "current_plan": None,
                }

            if isinstance(event, ScanStartEvent):
                total_probes = event.total_probes
                events.append({
                    "type": "log",
                    "message": f"[{agent_type}] Scanner initialized: {event.total_probes} probes",
                })

            elif isinstance(event, ProbeStartEvent):
                current_probe_index = event.probe_index
                # Calculate probe progress within this agent's share
                probe_progress = base_progress + (0.1 / state.total_agents) + \
                    (agent_progress_share * event.probe_index / max(event.total_probes, 1))

                writer(create_event(
                    EventType.PROBE_START,
                    agent=agent_type,
                    message=f"Starting probe: {event.probe_name}",
                    data={
                        "probe_name": event.probe_name,
                        "probe_index": event.probe_index,
                        "total_probes": event.total_probes,
                    },
                    progress=probe_progress,
                ).model_dump())

                events.append({
                    "type": "probe_start",
                    "agent": agent_type,
                    "probe_name": event.probe_name,
                    "probe_description": event.probe_description,
                    "category": event.probe_category,
                    "probe_index": event.probe_index,
                    "total_probes": event.total_probes,
                    "total_prompts": event.total_prompts,
                    "generations": event.generations,
                })

            elif isinstance(event, PromptResultEvent):
                # Track statistics
                if event.status == "pass":
                    total_pass += 1
                elif event.status == "fail":
                    total_fail += 1
                else:
                    total_error += 1

                # Store result for persistence
                probe_results_list.append({
                    "probe_name": event.probe_name,
                    "category": "security",
                    "status": event.status,
                    "detector_name": event.detector_name,
                    "detector_score": event.detector_score,
                    "detection_reason": event.detection_reason,
                    "prompt": event.prompt,
                    "output": event.output,
                })

                # Emit PROBE_RESULT via StreamWriter
                writer(create_event(
                    EventType.PROBE_RESULT,
                    agent=agent_type,
                    data={
                        "probe_name": event.probe_name,
                        "status": event.status,
                        "detector_name": event.detector_name,
                        "detector_score": event.detector_score,
                    },
                ).model_dump())

                # Emit with truncated preview
                events.append({
                    "type": "probe_result",
                    "agent": agent_type,
                    "probe_name": event.probe_name,
                    "prompt_index": event.prompt_index,
                    "total_prompts": event.total_prompts,
                    "status": event.status,
                    "detector_name": event.detector_name,
                    "detector_score": event.detector_score,
                    "detection_reason": event.detection_reason,
                    "prompt_preview": _truncate(event.prompt, 200),
                    "output_preview": _truncate(event.output, 200),
                    "generation_duration_ms": event.generation_duration_ms,
                    "evaluation_duration_ms": event.evaluation_duration_ms,
                })

            elif isinstance(event, ProbeCompleteEvent):
                # Emit PROBE_COMPLETE via StreamWriter
                writer(create_event(
                    EventType.PROBE_COMPLETE,
                    agent=agent_type,
                    message=f"Probe complete: {event.probe_name}",
                    data={
                        "probe_name": event.probe_name,
                        "probe_index": event.probe_index,
                        "total_probes": event.total_probes,
                        "pass_count": event.pass_count,
                        "fail_count": event.fail_count,
                    },
                ).model_dump())

                events.append({
                    "type": "probe_complete",
                    "agent": agent_type,
                    "probe_name": event.probe_name,
                    "probe_index": event.probe_index,
                    "total_probes": event.total_probes,
                    "results_count": event.results_count,
                    "pass_count": event.pass_count,
                    "fail_count": event.fail_count,
                    "error_count": event.error_count,
                    "duration_seconds": event.duration_seconds,
                })

            elif isinstance(event, ScanCompleteEvent):
                # Emit AGENT_COMPLETE via StreamWriter
                writer(create_event(
                    EventType.AGENT_COMPLETE,
                    agent=agent_type,
                    message=f"Agent {agent_type} complete",
                    data={
                        "total_probes": event.total_probes,
                        "total_results": event.total_results,
                        "total_pass": event.total_pass,
                        "total_fail": event.total_fail,
                        "vulnerabilities_found": event.vulnerabilities_found,
                    },
                    progress=base_progress + (1.0 / state.total_agents),
                ).model_dump())

                events.append({
                    "type": "agent_complete",
                    "agent": agent_type,
                    "status": "success",
                    "total_probes": event.total_probes,
                    "total_results": event.total_results,
                    "total_pass": event.total_pass,
                    "total_fail": event.total_fail,
                    "total_error": event.total_error,
                    "duration_seconds": event.duration_seconds,
                    "vulnerabilities": event.vulnerabilities_found,
                })

            elif isinstance(event, ScanErrorEvent):
                writer(create_event(
                    EventType.SCAN_ERROR,
                    node="execute_agent",
                    agent=agent_type,
                    message=event.error_message,
                    data={
                        "error_type": event.error_type,
                        "probe_name": event.probe_name,
                        "recoverable": event.recoverable,
                    },
                ).model_dump())

                events.append({
                    "type": "error",
                    "agent": agent_type,
                    "phase": "execution",
                    "error_type": event.error_type,
                    "message": event.error_message,
                    "probe_name": event.probe_name,
                    "recoverable": event.recoverable,
                })

                if not event.recoverable:
                    writer(create_event(
                        EventType.NODE_EXIT,
                        node="execute_agent",
                        agent=agent_type,
                        message=f"Execution failed: {event.error_message}",
                    ).model_dump())
                    return {
                        "agent_results": [AgentResult(
                            agent_type=agent_type,
                            status="error",
                            scan_id=scan_id,
                            plan=state.current_plan,
                            results=probe_results_list,
                            vulnerabilities_found=total_fail,
                            error=event.error_message,
                            phase="execution",
                        )],
                        "events": events,
                        "current_agent_index": state.current_agent_index + 1,
                        "current_plan": None,
                    }

        # Execution successful
        logger.info(f"[{agent_type}] Execution complete: {total_fail} vulnerabilities found")

        # Emit NODE_EXIT
        writer(create_event(
            EventType.NODE_EXIT,
            node="execute_agent",
            agent=agent_type,
            message=f"Execution complete for {agent_type}",
            progress=base_progress + (1.0 / state.total_agents),
        ).model_dump())

        return {
            "agent_results": [AgentResult(
                agent_type=agent_type,
                status="success",
                scan_id=scan_id,
                plan=state.current_plan,
                results=probe_results_list,
                vulnerabilities_found=total_fail,
            )],
            "events": events,
            "current_agent_index": state.current_agent_index + 1,
            "current_plan": None,
        }

    except Exception as e:
        logger.error(f"[{agent_type}] Execution error: {e}", exc_info=True)

        writer(create_event(
            EventType.SCAN_ERROR,
            node="execute_agent",
            agent=agent_type,
            message=f"Execution error: {e}",
            data={"phase": "execution", "error": str(e)},
        ).model_dump())

        events.append({
            "type": "log",
            "level": "error",
            "message": f"[{agent_type}] Execution error: {e}",
        })

        writer(create_event(
            EventType.NODE_EXIT,
            node="execute_agent",
            agent=agent_type,
            message=f"Execution failed for {agent_type}",
        ).model_dump())

        return {
            "agent_results": [AgentResult(
                agent_type=agent_type,
                status="error",
                scan_id=scan_id,
                plan=state.current_plan,
                results=probe_results_list,
                vulnerabilities_found=total_fail,
                error=str(e),
                phase="execution",
            )],
            "events": events,
            "current_agent_index": state.current_agent_index + 1,
            "current_plan": None,
        }


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text
