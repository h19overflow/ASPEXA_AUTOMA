"""
Load recon node for Swarm graph.

Purpose: Load and validate recon data from request or S3
Dependencies: libs.contracts.recon, persistence.s3_adapter, swarm_observability
"""

import logging
from typing import Dict, Any

from libs.contracts.recon import ReconBlueprint
from services.swarm.graph.state import SwarmState
from services.swarm.swarm_observability import (
    EventType,
    create_event,
    get_cancellation_manager,
    safe_get_stream_writer,
)

logger = logging.getLogger(__name__)


async def load_recon(state: SwarmState) -> Dict[str, Any]:
    """Load and validate recon data.

    Node: LOAD_RECON
    Entry point of the graph - validates recon context exists.

    Args:
        state: Current graph state with recon_context or campaign info

    Returns:
        Dict with events list, and errors if validation fails
    """
    writer = safe_get_stream_writer()
    manager = get_cancellation_manager(state.audit_id)
    events = []

    # Emit NODE_ENTER
    writer(create_event(
        EventType.NODE_ENTER,
        node="load_recon",
        message="Starting recon validation",
    ).model_dump())

    # Emit SCAN_STARTED
    writer(create_event(
        EventType.SCAN_STARTED,
        node="load_recon",
        message=f"Starting scan for audit: {state.audit_id}",
        data={
            "audit_id": state.audit_id,
            "target_url": state.target_url,
            "agent_types": state.agent_types,
        },
    ).model_dump())

    events.append({
        "type": "log",
        "message": f"Starting scan for audit: {state.audit_id}",
    })

    events.append({
        "type": "log",
        "message": f"Target: {state.target_url}",
    })

    events.append({
        "type": "log",
        "message": f"Agents to run: {', '.join(state.agent_types)}",
    })

    # Check cancellation before validation
    if await manager.checkpoint():
        writer(create_event(
            EventType.SCAN_CANCELLED,
            node="load_recon",
            message="Scan cancelled by user before recon validation",
        ).model_dump())
        return {"cancelled": True, "events": events}

    # Validate recon context exists
    if not state.recon_context:
        logger.warning(f"No recon context for audit {state.audit_id}")
        writer(create_event(
            EventType.NODE_EXIT,
            node="load_recon",
            message="Recon validation failed - no context",
        ).model_dump())
        return {
            "errors": ["No recon context provided"],
            "events": events + [{
                "type": "log",
                "level": "error",
                "message": "No blueprint_context provided",
            }],
        }

    # Validate recon structure
    try:
        blueprint = ReconBlueprint(**state.recon_context)
        tool_count = len(blueprint.intelligence.detected_tools or [])
        events.append({
            "type": "log",
            "message": f"Recon loaded: {tool_count} tools detected",
        })
        logger.info(f"Recon validated for {state.audit_id}: {tool_count} tools")
    except Exception as e:
        logger.error(f"Invalid recon for {state.audit_id}: {e}")
        writer(create_event(
            EventType.NODE_EXIT,
            node="load_recon",
            message=f"Recon validation failed: {e}",
        ).model_dump())
        return {
            "errors": [f"Invalid recon blueprint: {e}"],
            "events": events + [{
                "type": "log",
                "level": "error",
                "message": f"Invalid blueprint: {e}",
            }],
        }

    # Emit NODE_EXIT
    writer(create_event(
        EventType.NODE_EXIT,
        node="load_recon",
        message="Recon validation complete",
        progress=0.05,
    ).model_dump())

    return {"events": events}
