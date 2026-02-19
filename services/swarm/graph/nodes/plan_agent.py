"""
Plan agent node for Swarm graph.

Purpose: Deterministically select probes for current agent from DEFAULT_PROBES table
Dependencies: services.swarm.agents.base, services.swarm.core.schema, swarm_observability
"""

import logging
from typing import Dict, Any

from services.swarm.graph.state import SwarmState, AgentResult
from services.swarm.agents.base import get_agent_probe_pool
from services.swarm.core.schema import ScanConfig, ScanPlan
from services.swarm.swarm_observability import (
    EventType,
    create_event,
    get_cancellation_manager,
    safe_get_stream_writer,
)

logger = logging.getLogger(__name__)


async def plan_agent(state: SwarmState) -> Dict[str, Any]:
    """Run planning phase for current agent.

    Node: PLAN_AGENT
    Deterministically selects probes from DEFAULT_PROBES table — no LLM call.

    Args:
        state: Current graph state

    Returns:
        Dict with current_plan if successful, agent_results if failed
    """
    writer = safe_get_stream_writer()
    manager = get_cancellation_manager(state.audit_id)
    events: list[Dict[str, Any]] = []

    agent_type = state.current_agent
    if agent_type is None:
        return {
            "events": events,
            "current_agent_index": state.current_agent_index + 1,
            "current_plan": None,
        }

    base_progress = state.current_agent_index / max(state.total_agents, 1)

    writer(create_event(
        EventType.NODE_ENTER,
        node="plan_agent",
        agent=agent_type,
        message=f"Starting planning for {agent_type}",
        progress=base_progress,
    ).model_dump())

    if await manager.checkpoint():
        writer(create_event(
            EventType.SCAN_CANCELLED,
            node="plan_agent",
            agent=agent_type,
            message="Scan cancelled by user before planning",
        ).model_dump())
        return {"cancelled": True, "events": events}

    writer(create_event(
        EventType.PLAN_START,
        agent=agent_type,
        message=f"Planning scan for {agent_type}",
        progress=base_progress,
    ).model_dump())

    events.append({"type": "plan_start", "agent": agent_type})
    events.append({"type": "log", "message": f"[{agent_type}] Selecting probes..."})

    approach = state.scan_config.get("approach", "standard")
    max_probes = state.scan_config.get("max_probes", 3)
    probe_pool = get_agent_probe_pool(agent_type, approach)
    selected = probe_pool[:max_probes]

    plan = ScanPlan(
        audit_id=state.audit_id,
        agent_type=agent_type,
        target_url=state.target_url,
        selected_probes=selected,
        scan_config=ScanConfig(**state.scan_config),
    )
    duration_ms = 0

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
        "estimated_duration": len(plan.selected_probes) * 2,
        "duration_ms": duration_ms,
    })

    events.append({
        "type": "log",
        "message": f"[{agent_type}] Plan complete: {len(plan.selected_probes)} probes",
    })

    logger.info(f"[{agent_type}] Deterministic planning: {len(plan.selected_probes)} probes selected")

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
        "current_plan_duration_ms": duration_ms,
    }
