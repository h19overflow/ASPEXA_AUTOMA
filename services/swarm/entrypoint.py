"""HTTP entrypoint for Swarm scanning service.

Purpose: Thin HTTP layer that invokes the LangGraph workflow
Dependencies: graph.swarm_graph, graph.state, swarm_observability

Architecture:
- Graph-based orchestration with nodes for each phase
- State machine handles agent loop, planning, execution, persistence
- Multi-mode streaming for real-time UI updates

Streaming Modes:
- "values": Legacy mode, yields events from state.events accumulator
- "custom": StreamWriter events only (recommended for production)
- "debug": Both state events and StreamWriter events
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional

from libs.contracts.scanning import ScanJobDispatch
from libs.monitoring import observe, CallbackHandler
from services.swarm.core.config import AgentType
from services.swarm.graph import SwarmState, get_swarm_graph
from services.swarm.persistence.s3_adapter import load_recon_for_campaign
from services.swarm.swarm_observability import (
    get_cancellation_manager,
    remove_cancellation_manager,
    get_checkpointer,
    get_active_scan_ids,
)

logger = logging.getLogger(__name__)

# Streaming mode type
StreamMode = Literal["values", "custom", "debug"]


@observe()
async def execute_scan_streaming(
    request: ScanJobDispatch,
    agent_types: Optional[List[str]] = None,
    stream_mode: StreamMode = "custom",
    enable_checkpointing: bool = False,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute scanning with multi-mode streaming.

    Thin wrapper that:
    1. Builds initial state from request
    2. Registers cancellation manager for pause/resume/cancel
    3. Invokes LangGraph workflow with selected streaming mode
    4. Yields events based on stream_mode

    Args:
        request: Scan job dispatch with target info and config
        agent_types: Optional list of agent types to run
        stream_mode: Streaming mode
            - "values": Legacy events from state.events
            - "custom": Real-time StreamWriter events (default)
            - "debug": Both state and StreamWriter events
        enable_checkpointing: Enable state persistence for resume capability

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

    # Register cancellation manager for this scan
    manager = get_cancellation_manager(audit_id)
    logger.info(f"Registered cancellation manager for scan {audit_id}")

    # Get checkpointer if enabled
    checkpointer = get_checkpointer(persistent=False) if enable_checkpointing else None

    # Get compiled graph (with or without checkpointer)
    graph = get_swarm_graph(checkpointer=checkpointer)

    # Initialize Langfuse callback handler for tracing
    langfuse_handler = CallbackHandler()

    # Build config with thread_id for checkpointing and monitoring
    config = {
        "configurable": {"thread_id": audit_id},
        "callbacks": [langfuse_handler],
        "run_name": "SwarmScan",
    }

    # Stream graph execution
    try:
        if stream_mode == "values":
            # Legacy mode: events from state.events accumulator
            async for state_update in graph.astream(initial_state, config=config):
                for node_name, node_output in state_update.items():
                    if isinstance(node_output, dict) and "events" in node_output:
                        for event in node_output["events"]:
                            yield event

        elif stream_mode == "custom":
            # Custom mode: StreamWriter events only (real-time)
            async for event in graph.astream(
                initial_state,
                config=config,
                stream_mode="custom",
            ):
                yield event

        elif stream_mode == "debug":
            # Debug mode: Both state events and StreamWriter events
            async for chunk in graph.astream(
                initial_state,
                config=config,
                stream_mode=["values", "custom"],
            ):
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, data = chunk
                    if mode == "custom":
                        yield data
                    elif mode == "values":
                        for node_name, node_output in data.items():
                            if isinstance(node_output, dict) and "events" in node_output:
                                for event in node_output["events"]:
                                    yield {"_mode": "state", **event}
                else:
                    yield chunk

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
    finally:
        # Cleanup cancellation manager
        remove_cancellation_manager(audit_id)
        logger.info(f"Cleaned up cancellation manager for scan {audit_id}")


# Control functions for API endpoints
def cancel_scan(scan_id: str) -> Dict[str, Any]:
    """Cancel a running scan.

    Args:
        scan_id: Unique identifier for the scan (audit_id)

    Returns:
        Status dict with scan_id and cancelled state
    """
    if scan_id not in get_active_scan_ids():
        return {"scan_id": scan_id, "found": False, "message": "Scan not found"}

    manager = get_cancellation_manager(scan_id)
    manager.cancel()
    logger.info(f"Cancelled scan {scan_id}")
    return {"scan_id": scan_id, "cancelled": True}


def pause_scan(scan_id: str) -> Dict[str, Any]:
    """Pause a running scan at the next checkpoint.

    Args:
        scan_id: Unique identifier for the scan (audit_id)

    Returns:
        Status dict with scan_id and paused state
    """
    if scan_id not in get_active_scan_ids():
        return {"scan_id": scan_id, "found": False, "message": "Scan not found"}

    manager = get_cancellation_manager(scan_id)
    manager.pause()
    logger.info(f"Paused scan {scan_id}")
    return {"scan_id": scan_id, "paused": True}


def resume_scan(scan_id: str) -> Dict[str, Any]:
    """Resume a paused scan.

    Args:
        scan_id: Unique identifier for the scan (audit_id)

    Returns:
        Status dict with scan_id and resumed state
    """
    if scan_id not in get_active_scan_ids():
        return {"scan_id": scan_id, "found": False, "message": "Scan not found"}

    manager = get_cancellation_manager(scan_id)
    manager.resume()
    logger.info(f"Resumed scan {scan_id}")
    return {"scan_id": scan_id, "paused": False}


def get_scan_status(scan_id: str) -> Dict[str, Any]:
    """Get the current status of a scan.

    Args:
        scan_id: Unique identifier for the scan (audit_id)

    Returns:
        Status dict with scan_id, cancelled, paused, and found states
    """
    if scan_id not in get_active_scan_ids():
        return {"scan_id": scan_id, "found": False, "message": "Scan not found"}

    manager = get_cancellation_manager(scan_id)
    return {
        "scan_id": scan_id,
        "found": True,
        "cancelled": manager.is_cancelled,
        "paused": manager.is_paused,
    }
