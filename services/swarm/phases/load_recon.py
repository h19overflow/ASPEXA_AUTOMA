"""
Phase 1: Load and validate recon data.

Purpose: Validate recon_context exists and has a valid ReconBlueprint structure
Dependencies: libs.contracts.recon, swarm_observability
"""

import logging
from typing import Awaitable, Callable, Dict, Any

from libs.contracts.recon import ReconBlueprint
from services.swarm.core.schema import ScanState
from services.swarm.swarm_observability import (
    EventType,
    create_event,
)

logger = logging.getLogger(__name__)


async def load_recon(
    state: ScanState,
    emit: Callable[[Dict[str, Any]], Awaitable[None]],
) -> None:
    """Validate recon context and emit SCAN_STARTED.

    Phase: LOAD_RECON
    Modifies state.cancelled and state.errors in place.

    Args:
        state: Current scan state
        emit: Async callback that sends an SSE event dict to the client
    """
    await emit(create_event(
        EventType.SCAN_STARTED,
        node="load_recon",
        message=f"Starting scan for audit: {state.audit_id}",
        data={
            "audit_id": state.audit_id,
            "target_url": state.target_url,
            "agent_types": state.agent_types,
        },
    ).model_dump())

    if not state.recon_context:
        logger.warning(f"No recon context for audit {state.audit_id}")
        await emit(create_event(
            EventType.NODE_EXIT,
            node="load_recon",
            message="Recon validation failed — no context",
        ).model_dump())
        state.errors.append("No recon context provided")
        return

    try:
        blueprint = ReconBlueprint(**state.recon_context)
        tool_count = len(blueprint.intelligence.detected_tools or [])
        logger.info(f"Recon validated for {state.audit_id}: {tool_count} tools")
    except Exception as e:
        logger.error(f"Invalid recon for {state.audit_id}: {e}")
        await emit(create_event(
            EventType.NODE_EXIT,
            node="load_recon",
            message=f"Recon validation failed: {e}",
        ).model_dump())
        state.errors.append(f"Invalid recon blueprint: {e}")
        return

    await emit(create_event(
        EventType.NODE_EXIT,
        node="load_recon",
        message="Recon validation complete",
        progress=0.05,
    ).model_dump())
