"""
Safety check node for Swarm graph.

Purpose: Check if current agent is blocked by safety policy
Dependencies: services.swarm.core.config, swarm_observability
"""

import logging
from typing import Dict, Any

from services.swarm.graph.state import SwarmState, AgentResult
from services.swarm.core.config import AgentType
from services.swarm.swarm_observability import (
    EventType,
    create_event,
    get_cancellation_manager,
    safe_get_stream_writer,
)

logger = logging.getLogger(__name__)

# Map agent types to their attack vectors for safety filtering
AGENT_VECTORS: Dict[str, list] = {
    AgentType.SQL.value: ["injection", "xss"],
    AgentType.AUTH.value: ["bola", "bypass"],
    AgentType.JAILBREAK.value: ["jailbreak", "prompt_injection"],
}


async def check_safety(state: SwarmState) -> Dict[str, Any]:
    """Check if current agent is blocked by safety policy.

    Node: CHECK_SAFETY
    Evaluates safety policy before planning/execution.

    Args:
        state: Current graph state with safety_policy

    Returns:
        Dict with agent_results if blocked, otherwise empty events
    """
    writer = safe_get_stream_writer()
    manager = get_cancellation_manager(state.audit_id)
    agent_type = state.current_agent
    events = []

    # Calculate progress based on agent index
    progress = state.current_agent_index / max(state.total_agents, 1)

    # Emit NODE_ENTER
    writer(create_event(
        EventType.NODE_ENTER,
        node="check_safety",
        agent=agent_type,
        message=f"Checking safety policy for {agent_type}",
        progress=progress,
    ).model_dump())

    # Check cancellation
    if await manager.checkpoint():
        writer(create_event(
            EventType.SCAN_CANCELLED,
            node="check_safety",
            agent=agent_type,
            message="Scan cancelled by user",
        ).model_dump())
        return {"cancelled": True, "events": events}

    # Emit AGENT_START
    writer(create_event(
        EventType.AGENT_START,
        agent=agent_type,
        data={
            "index": state.current_agent_index + 1,
            "total": state.total_agents,
        },
        progress=progress,
    ).model_dump())

    events.append({
        "type": "agent_start",
        "agent": agent_type,
        "index": state.current_agent_index + 1,
        "total": state.total_agents,
    })

    # Check safety policy
    if state.safety_policy:
        blocked_vectors = state.safety_policy.get("blocked_attack_vectors", [])

        try:
            agent_vectors = AGENT_VECTORS.get(agent_type, [])
            if any(v in blocked_vectors for v in agent_vectors):
                logger.info(f"Agent {agent_type} blocked by safety policy")
                events.append({
                    "type": "agent_blocked",
                    "agent": agent_type,
                    "reason": "safety_policy",
                })

                writer(create_event(
                    EventType.NODE_EXIT,
                    node="check_safety",
                    agent=agent_type,
                    message=f"Agent {agent_type} blocked by safety policy",
                ).model_dump())

                return {
                    "agent_results": [AgentResult(
                        agent_type=agent_type,
                        status="blocked",
                        error="Blocked by safety policy",
                    )],
                    "events": events,
                    "current_agent_index": state.current_agent_index + 1,
                }
        except ValueError:
            # Unknown agent type, continue anyway
            pass

    events.append({
        "type": "log",
        "message": f"[{agent_type}] Building scan context...",
    })

    # Emit NODE_EXIT
    writer(create_event(
        EventType.NODE_EXIT,
        node="check_safety",
        agent=agent_type,
        message=f"Safety check passed for {agent_type}",
        progress=progress,
    ).model_dump())

    return {"events": events}
