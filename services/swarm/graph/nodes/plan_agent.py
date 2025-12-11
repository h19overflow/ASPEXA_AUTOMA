"""
Plan agent node for Swarm graph.

Purpose: Run LLM planning phase for current agent
Dependencies: services.swarm.agents.base, services.swarm.core.schema, swarm_observability
"""

import logging
from typing import Dict, Any

from services.swarm.graph.state import SwarmState, AgentResult
from services.swarm.agents.base import run_planning_agent
from services.swarm.core.schema import ScanInput, ScanConfig
from services.swarm.swarm_observability import (
    EventType,
    create_event,
    get_cancellation_manager,
    safe_get_stream_writer,
)

logger = logging.getLogger(__name__)


def _extract_intelligence(recon_context: Dict[str, Any]) -> Dict[str, Any]:
    """Extract intelligence fields from recon context.

    Args:
        recon_context: Raw recon blueprint data

    Returns:
        Dict with infrastructure, tools, and other intelligence
    """
    intelligence = recon_context.get("intelligence", {})

    # Extract infrastructure
    infrastructure = intelligence.get("infrastructure", {})
    if not infrastructure:
        infrastructure = {
            "database": intelligence.get("database_type"),
            "model_family": intelligence.get("model_family"),
            "vector_store": intelligence.get("vector_store"),
        }

    # Extract detected tools
    detected_tools = intelligence.get("detected_tools", [])

    # Extract system prompt leaks
    system_prompt_leaks = []
    observations = recon_context.get("observations", {})
    if observations:
        system_prompt_leaks = observations.get("system_prompt", [])

    return {
        "infrastructure": infrastructure,
        "detected_tools": detected_tools,
        "system_prompt_leaks": system_prompt_leaks,
        "raw_observations": observations,
        "structured_deductions": recon_context.get("structured_deductions", {}),
    }


async def plan_agent(state: SwarmState) -> Dict[str, Any]:
    """Run planning phase for current agent.

    Node: PLAN_AGENT
    Uses LLM to analyze recon and select probes.

    Args:
        state: Current graph state with recon_context

    Returns:
        Dict with current_plan if successful, agent_results if failed
    """
    writer = safe_get_stream_writer()
    manager = get_cancellation_manager(state.audit_id)
    events: list[Dict[str, Any]] = []

    # Guard: ensure we have a current agent
    agent_type = state.current_agent
    if agent_type is None:
        return {
            "events": events,
            "current_agent_index": state.current_agent_index + 1,
            "current_plan": None,
        }

    # Calculate progress
    base_progress = state.current_agent_index / max(state.total_agents, 1)

    # Emit NODE_ENTER
    writer(create_event(
        EventType.NODE_ENTER,
        node="plan_agent",
        agent=agent_type,
        message=f"Starting planning for {agent_type}",
        progress=base_progress,
    ).model_dump())

    # Check cancellation before planning
    if await manager.checkpoint():
        writer(create_event(
            EventType.SCAN_CANCELLED,
            node="plan_agent",
            agent=agent_type,
            message="Scan cancelled by user before planning",
        ).model_dump())
        return {"cancelled": True, "events": events}

    # Emit PLAN_START
    writer(create_event(
        EventType.PLAN_START,
        agent=agent_type,
        message=f"Planning scan for {agent_type}",
        progress=base_progress,
    ).model_dump())

    events.append({
        "type": "plan_start",
        "agent": agent_type,
    })

    events.append({
        "type": "log",
        "message": f"[{agent_type}] Planning scan...",
    })

    try:
        # Extract intelligence from recon context
        intel = _extract_intelligence(state.recon_context)

        # Build ScanInput directly
        scan_input = ScanInput(
            audit_id=state.audit_id,
            agent_type=agent_type,
            target_url=state.target_url,
            infrastructure=intel["infrastructure"],
            detected_tools=intel["detected_tools"],
            system_prompt_leaks=intel["system_prompt_leaks"],
            raw_observations=intel["raw_observations"],
            structured_deductions=intel["structured_deductions"],
            config=ScanConfig(
                approach=state.scan_config.get("approach", "standard"),
            ),
        )

        # Run planning agent
        planning_result = await run_planning_agent(agent_type, scan_input)

        if not planning_result.success:
            error_msg = planning_result.error or "Planning failed"
            logger.warning(f"[{agent_type}] Planning failed: {error_msg}")

            writer(create_event(
                EventType.SCAN_ERROR,
                node="plan_agent",
                agent=agent_type,
                message=error_msg,
                data={"phase": "planning"},
            ).model_dump())

            events.append({
                "type": "error",
                "agent": agent_type,
                "phase": "planning",
                "message": error_msg,
            })

            writer(create_event(
                EventType.NODE_EXIT,
                node="plan_agent",
                agent=agent_type,
                message=f"Planning failed for {agent_type}",
            ).model_dump())

            return {
                "agent_results": [AgentResult(
                    agent_type=agent_type,
                    status="failed",
                    scan_id=None,
                    plan=None,
                    error=error_msg,
                    phase="planning",
                    duration_ms=planning_result.duration_ms,
                )],
                "events": events,
                "current_agent_index": state.current_agent_index + 1,
                "current_plan": None,
            }

        plan = planning_result.plan
        if not plan:
            writer(create_event(
                EventType.SCAN_ERROR,
                node="plan_agent",
                agent=agent_type,
                message="No plan produced",
                data={"phase": "planning"},
            ).model_dump())

            events.append({
                "type": "error",
                "agent": agent_type,
                "phase": "planning",
                "message": "No plan produced",
            })

            writer(create_event(
                EventType.NODE_EXIT,
                node="plan_agent",
                agent=agent_type,
                message=f"Planning produced no plan for {agent_type}",
            ).model_dump())

            return {
                "agent_results": [AgentResult(
                    agent_type=agent_type,
                    status="failed",
                    scan_id=None,
                    plan=None,
                    error="No plan produced",
                    phase="planning",
                )],
                "events": events,
                "current_agent_index": state.current_agent_index + 1,
                "current_plan": None,
            }

        # Estimate duration: ~2s per probe
        estimated_duration = len(plan.selected_probes) * 2.0

        # Emit PLAN_COMPLETE
        writer(create_event(
            EventType.PLAN_COMPLETE,
            agent=agent_type,
            message=f"Planning complete: {len(plan.selected_probes)} probes selected",
            data={
                "probes": plan.selected_probes,
                "probe_count": len(plan.selected_probes),
            },
            progress=base_progress + (0.1 / state.total_agents),
        ).model_dump())

        events.append({
            "type": "plan_complete",
            "agent": agent_type,
            "probes": plan.selected_probes,
            "probe_count": len(plan.selected_probes),
            "estimated_duration": int(estimated_duration),
            "duration_ms": planning_result.duration_ms,
        })

        events.append({
            "type": "log",
            "message": f"[{agent_type}] Plan complete: {len(plan.selected_probes)} probes",
        })

        logger.info(f"[{agent_type}] Planning successful: {len(plan.selected_probes)} probes")

        # Emit NODE_EXIT
        writer(create_event(
            EventType.NODE_EXIT,
            node="plan_agent",
            agent=agent_type,
            message=f"Planning complete for {agent_type}",
            progress=base_progress + (0.1 / state.total_agents),
        ).model_dump())

        return {
            "events": events,
            "current_plan": plan.model_dump(),
            "current_plan_duration_ms": planning_result.duration_ms,
        }

    except Exception as e:
        logger.error(f"[{agent_type}] Planning error: {e}", exc_info=True)

        writer(create_event(
            EventType.SCAN_ERROR,
            node="plan_agent",
            agent=agent_type,
            message=f"Planning error: {e}",
            data={"phase": "planning", "error": str(e)},
        ).model_dump())

        events.append({
            "type": "log",
            "level": "error",
            "message": f"[{agent_type}] Planning error: {e}",
        })

        # Emit NODE_EXIT on error
        writer(create_event(
            EventType.NODE_EXIT,
            node="plan_agent",
            agent=agent_type,
            message=f"Planning failed for {agent_type}",
        ).model_dump())

        return {
            "agent_results": [AgentResult(
                agent_type=agent_type,
                status="error",
                scan_id=None,
                plan=None,
                error=str(e),
                phase="planning",
            )],
            "events": events,
            "current_agent_index": state.current_agent_index + 1,
            "current_plan": None,
        }
