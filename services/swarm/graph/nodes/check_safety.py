"""
Safety check node for Swarm graph.

Purpose: Check if current agent is blocked by safety policy
Dependencies: services.swarm.core.config
"""

import logging
from typing import Dict, Any

from services.swarm.graph.state import SwarmState, AgentResult
from services.swarm.core.config import AgentType

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
    agent_type = state.current_agent
    events = []

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

    return {"events": events}
