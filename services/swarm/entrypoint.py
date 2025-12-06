"""HTTP entrypoint for Swarm scanning service.

Purpose: Thin HTTP layer that invokes the LangGraph workflow
Dependencies: graph.swarm_graph, graph.state

Architecture:
- Graph-based orchestration with nodes for each phase
- State machine handles agent loop, planning, execution, persistence
- Entrypoint just builds initial state and streams events
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from libs.contracts.scanning import ScanJobDispatch
from libs.monitoring import observe
from services.swarm.core.config import AgentType
from services.swarm.graph import SwarmState, get_swarm_graph
from services.swarm.persistence.s3_adapter import load_recon_for_campaign

logger = logging.getLogger(__name__)


@observe()
async def execute_scan_streaming(
    request: ScanJobDispatch,
    agent_types: Optional[List[str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute scanning with graph-based orchestration and streaming.

    Thin wrapper that:
    1. Builds initial state from request
    2. Invokes LangGraph workflow
    3. Yields events from state updates

    Args:
        request: Scan job dispatch with target info and config
        agent_types: Optional list of agent types to run

    Yields:
        SSE event dictionaries for real-time UI updates
    """
    if agent_types is None:
        agent_types = [
            AgentType.SQL.value,
            AgentType.AUTH.value,
            AgentType.JAILBREAK.value,
        ]

    yield {"type": "log", "message": f"Starting scan with {len(agent_types)} agents"}

    # Load recon data - either from request or from S3
    blueprint_data = request.blueprint_context
    if not blueprint_data and request.campaign_id:
        yield {
            "type": "log",
            "message": f"Loading recon from S3 for campaign: {request.campaign_id}",
        }
        try:
            blueprint_data = await load_recon_for_campaign(request.campaign_id)
            if not blueprint_data:
                yield {
                    "type": "log",
                    "level": "error",
                    "message": f"No recon data found for campaign {request.campaign_id}",
                }
                return
            yield {"type": "log", "message": "Recon data loaded from S3"}
        except Exception as e:
            yield {
                "type": "log",
                "level": "error",
                "message": f"Failed to load recon from S3: {e}",
            }
            return

    if not blueprint_data:
        yield {
            "type": "log",
            "level": "error",
            "message": "No blueprint_context or campaign_id provided",
        }
        return

    # Extract audit_id and target_url
    audit_id = blueprint_data.get("audit_id", "unknown")
    target_url = (
        request.target_url
        or blueprint_data.get("target_url")
        or "https://api.target.local/v1/chat"
    )

    # Build safety policy dict
    safety_policy = None
    if request.safety_policy:
        safety_policy = {
            "blocked_attack_vectors": request.safety_policy.blocked_attack_vectors or [],
        }

    # Build scan config
    scan_config = {
        "approach": request.scan_config.approach if request.scan_config else "standard",
        "timeout": request.scan_config.request_timeout if request.scan_config else 30,
        "headers": {},
    }

    # Build initial state
    initial_state = SwarmState(
        audit_id=audit_id,
        target_url=target_url,
        agent_types=agent_types,
        recon_context=blueprint_data,
        scan_config=scan_config,
        safety_policy=safety_policy,
    )

    # Get compiled graph
    graph = get_swarm_graph()

    # Stream graph execution
    try:
        async for state_update in graph.astream(initial_state):
            # Each state_update is a dict with node name as key
            for node_name, node_output in state_update.items():
                # Yield events from this node
                if isinstance(node_output, dict) and "events" in node_output:
                    for event in node_output["events"]:
                        yield event

    except Exception as e:
        logger.error(f"Graph execution error: {e}", exc_info=True)
        yield {
            "type": "log",
            "level": "error",
            "message": f"Scan failed: {e}",
        }
        yield {
            "type": "complete",
            "data": {
                "audit_id": audit_id,
                "agents": {},
                "error": str(e),
            },
        }
