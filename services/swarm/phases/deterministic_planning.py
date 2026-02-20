"""
Phase 2: Deterministic probe selection for current agent.

Purpose: Select probes from DEFAULT_PROBES table — no LLM call
Dependencies: services.swarm.core.config, services.swarm.core.schema
"""

import logging
from typing import Awaitable, Callable, Dict, Any

from services.swarm.core.config import get_agent_probe_pool
from services.swarm.core.schema import ScanState, ScanConfig, ScanPlan
from services.swarm.swarm_observability import (
    EventType,
    create_event,
)

logger = logging.getLogger(__name__)


async def run_deterministic_planning(
    state: ScanState,
    emit: Callable[[Dict[str, Any]], Awaitable[None]],
) -> None:
    """Select probes for current agent and store plan in state.

    Phase: DETERMINISTIC_PLANNING
    Modifies state.current_plan and state.cancelled in place.

    Args:
        state: Current scan state (state.current_agent must be set)
        emit: Async callback that sends an SSE event dict to the client
    """
    agent_type = state.current_agent
    base_progress = state.current_agent_index / max(state.total_agents, 1)

    await emit(create_event(
        EventType.NODE_ENTER,
        node="deterministic_planning",
        agent=agent_type,
        message=f"Starting deterministic planning for {agent_type}",
        progress=base_progress,
    ).model_dump())

    await emit(create_event(
        EventType.PLAN_START,
        agent=agent_type,
        message=f"Planning scan for {agent_type}",
        progress=base_progress,
    ).model_dump())

    approach = state.scan_config.get("approach", "standard")
    max_probes = state.scan_config.get("max_probes", 3)
    
    # Extract infrastructure for dynamic probe selection
    infrastructure = None
    if state.recon_context and "intelligence" in state.recon_context:
        intel = state.recon_context["intelligence"]
        if "infrastructure" in intel:
            infrastructure = intel["infrastructure"]

    probe_pool = get_agent_probe_pool(agent_type, approach, infrastructure=infrastructure)
    selected = probe_pool[:max_probes]

    plan = ScanPlan(
        audit_id=state.audit_id,
        agent_type=agent_type,
        target_url=state.target_url,
        selected_probes=selected,
        scan_config=ScanConfig(**state.scan_config),
    )

    probe_progress = base_progress + (0.1 / state.total_agents)

    await emit(create_event(
        EventType.PLAN_COMPLETE,
        agent=agent_type,
        message=f"Planning complete: {len(plan.selected_probes)} probes selected",
        data={
            "probes": plan.selected_probes,
            "probe_count": len(plan.selected_probes),
        },
        progress=probe_progress,
    ).model_dump())

    await emit(create_event(
        EventType.NODE_EXIT,
        node="deterministic_planning",
        agent=agent_type,
        message=f"Deterministic planning complete for {agent_type}",
        progress=probe_progress,
    ).model_dump())

    logger.info(f"[{agent_type}] Plan: {len(plan.selected_probes)} probes selected")
    state.current_plan = plan.model_dump()
