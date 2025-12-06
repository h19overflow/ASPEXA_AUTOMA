"""
Load recon node for Swarm graph.

Purpose: Load and validate recon data from request or S3
Dependencies: libs.contracts.recon, persistence.s3_adapter
"""

import logging
from typing import Dict, Any

from libs.contracts.recon import ReconBlueprint
from services.swarm.graph.state import SwarmState
from services.swarm.persistence.s3_adapter import load_recon_for_campaign

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
    events = []

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

    # Validate recon context exists
    if not state.recon_context:
        logger.warning(f"No recon context for audit {state.audit_id}")
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
        return {
            "errors": [f"Invalid recon blueprint: {e}"],
            "events": events + [{
                "type": "log",
                "level": "error",
                "message": f"Invalid blueprint: {e}",
            }],
        }

    return {"events": events}
