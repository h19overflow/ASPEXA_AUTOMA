"""
Phase 3: Execute probes for current agent using the Garak scanner.

Purpose: Run scanner with the plan from plan_agent, stream probe/prompt events
Dependencies: services.swarm.garak_scanner, services.swarm.core.schema
"""

import logging
from typing import Awaitable, Callable, Dict, Any, List

from services.swarm.garak_scanner import get_scanner
from services.swarm.garak_scanner.models import (
    ScanStartEvent,
    ProbeStartEvent,
    PromptResultEvent,
    ProbeCompleteEvent,
    ScanCompleteEvent,
    ScanErrorEvent,
)
from services.swarm.core.schema import ScanState, ScanPlan, AgentResult
from services.swarm.swarm_observability import (
    EventType,
    create_event,
)

logger = logging.getLogger(__name__)


async def run_probe_execution(
    state: ScanState,
    emit: Callable[[Dict[str, Any]], Awaitable[None]],
) -> None:
    """Run the scanner and append an AgentResult to state.agent_results.

    Phase: PROBE_EXECUTION
    Modifies state.agent_results and state.cancelled in place.

    Args:
        state: Current scan state (state.current_plan must be set)
        emit: Async callback that sends an SSE event dict to the client
    """
    agent_type = state.current_agent
    base_progress = state.current_agent_index / max(state.total_agents, 1)
    agent_progress_share = 0.9 / state.total_agents

    await emit(create_event(
        EventType.NODE_ENTER,
        node="probe_execution",
        agent=agent_type,
        message=f"Starting probe execution for category {agent_type}",
        progress=base_progress + 0.1 / state.total_agents,
    ).model_dump())

    if not state.current_plan:
        logger.error(f"[{agent_type}] No plan available for execution")
        await emit(create_event(
            EventType.NODE_EXIT,
            node="probe_execution",
            agent=agent_type,
            message="No plan available for execution",
            progress=base_progress + (1.0 / state.total_agents),
        ).model_dump())
        state.agent_results.append(AgentResult(
            agent_type=agent_type,
            status="failed",
            error="No plan available for execution",
            phase="execution",
        ))
        return

    try:
        plan = ScanPlan(**state.current_plan)
    except Exception as e:
        logger.error(f"[{agent_type}] Invalid plan structure: {e}")
        state.agent_results.append(AgentResult(
            agent_type=agent_type,
            status="error",
            error=f"Invalid plan: {e}",
            phase="execution",
        ))
        return

    scan_id = f"garak-{state.audit_id}-{agent_type}"
    probe_results_list: List[Dict[str, Any]] = []
    total_pass = 0
    total_fail = 0
    current_probe_index = 0

    try:
        scanner = get_scanner()

        async for event in scanner.scan_with_streaming(plan):

            if isinstance(event, ScanStartEvent):
                logger.debug(f"[{agent_type}] Scanner initialized: {event.total_probes} probes")

            elif isinstance(event, ProbeStartEvent):
                current_probe_index = event.probe_index
                probe_progress = (
                    base_progress
                    + (0.1 / state.total_agents)
                    + (agent_progress_share * event.probe_index / max(event.total_probes, 1))
                )
                await emit(create_event(
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

            elif isinstance(event, PromptResultEvent):
                if event.status == "pass":
                    total_pass += 1
                elif event.status == "fail":
                    total_fail += 1

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

                await emit(create_event(
                    EventType.PROBE_RESULT,
                    agent=agent_type,
                    data={
                        "probe_name": event.probe_name,
                        "prompt_index": event.prompt_index,
                        "total_prompts": event.total_prompts,
                        "status": event.status,
                        "detector_name": event.detector_name,
                        "detector_score": event.detector_score,
                        "detection_reason": event.detection_reason,
                        "prompt": event.prompt,
                        "output": event.output,
                    },
                ).model_dump())

            elif isinstance(event, ProbeCompleteEvent):
                await emit(create_event(
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

            elif isinstance(event, ScanCompleteEvent):
                await emit(create_event(
                    EventType.AGENT_COMPLETE,
                    agent=agent_type,
                    message=f"Scan complete for category {agent_type}",
                    data={
                        "total_probes": event.total_probes,
                        "total_results": event.total_results,
                        "total_pass": event.total_pass,
                        "total_fail": event.total_fail,
                        "vulnerabilities_found": event.vulnerabilities_found,
                    },
                    progress=base_progress + (1.0 / state.total_agents),
                ).model_dump())

            elif isinstance(event, ScanErrorEvent):
                await emit(create_event(
                    EventType.SCAN_ERROR,
                    node="probe_execution",
                    agent=agent_type,
                    message=event.error_message,
                    data={
                        "error_type": event.error_type,
                        "probe_name": event.probe_name,
                        "recoverable": event.recoverable,
                    },
                ).model_dump())

                if not event.recoverable:
                    state.agent_results.append(AgentResult(
                        agent_type=agent_type,
                        status="error",
                        scan_id=scan_id,
                        plan=state.current_plan,
                        results=probe_results_list,
                        vulnerabilities_found=total_fail,
                        error=event.error_message,
                        phase="execution",
                    ))
                    return

        logger.info(f"[{agent_type}] Execution complete: {total_fail} vulnerabilities found")

        await emit(create_event(
            EventType.NODE_EXIT,
            node="probe_execution",
            agent=agent_type,
            message=f"Probe execution complete for {agent_type}",
            progress=base_progress + (1.0 / state.total_agents),
        ).model_dump())

        state.agent_results.append(AgentResult(
            agent_type=agent_type,
            status="success",
            scan_id=scan_id,
            plan=state.current_plan,
            results=probe_results_list,
            vulnerabilities_found=total_fail,
        ))

    except Exception as e:
        logger.error(f"[{agent_type}] Execution error: {e}", exc_info=True)

        await emit(create_event(
            EventType.SCAN_ERROR,
            node="probe_execution",
            agent=agent_type,
            message=f"Execution error: {e}",
            data={"phase": "execution", "error": str(e)},
        ).model_dump())

        await emit(create_event(
            EventType.NODE_EXIT,
            node="probe_execution",
            agent=agent_type,
            message=f"Execution failed for {agent_type}",
            progress=base_progress + (1.0 / state.total_agents),
        ).model_dump())

        state.agent_results.append(AgentResult(
            agent_type=agent_type,
            status="error",
            scan_id=scan_id,
            plan=state.current_plan,
            results=probe_results_list,
            vulnerabilities_found=total_fail,
            error=str(e),
            phase="execution",
        ))
