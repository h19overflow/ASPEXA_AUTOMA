"""HTTP entrypoint for Swarm scanning service.

Purpose: Orchestrate sequential scan phases with async streaming
Dependencies: phases/, core/schema.py, swarm_observability, persistence

Architecture:
- Sequential phases: load_recon → plan_agent → execute_agent → persist_results
- ScanState is a plain dataclass (no LangGraph)
- emit() callback passes events directly to the async generator
- CancellationManager handles pause/resume/cancel between probe calls
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from libs.contracts.scanning import ScanJobDispatch
from libs.monitoring import observe
from services.swarm.core.config import AgentType
from services.swarm.core.schema import ScanState
from services.swarm.persistence.s3_adapter import load_recon_for_campaign
from services.swarm.phases import (
    load_recon,
    plan_agent,
    execute_agent,
    persist_results,
)
from services.swarm.swarm_observability import (
    get_cancellation_manager,
    remove_cancellation_manager,
    get_active_scan_ids,
)

logger = logging.getLogger(__name__)

_SCAN_CONFIG_DEFAULTS: Dict[str, Any] = {
    "approach": "standard",
    "max_probes": 3,
    "max_prompts_per_probe": 5,
    "request_timeout": 30,
    "max_retries": 3,
    "retry_backoff": 1.0,
    "connection_type": "http",
}


@observe()
async def execute_scan_streaming(
    request: ScanJobDispatch,
    agent_types: Optional[List[str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute scanning with real-time SSE streaming.

    Orchestrates four sequential phases per agent:
    1. load_recon — validate recon context
    2. plan_agent — select probes deterministically
    3. execute_agent — run scanner, stream probe/prompt events
    4. persist_results — save to S3, emit SCAN_COMPLETE

    Args:
        request: Scan job dispatch with target info and config
        agent_types: Agent types to run (defaults to SQL, AUTH, JAILBREAK)

    Yields:
        SSE event dicts for real-time UI updates
    """
    if agent_types is None:
        agent_types = [AgentType.SQL.value, AgentType.AUTH.value, AgentType.JAILBREAK.value]

    yield {"type": "log", "message": f"Starting scan with {len(agent_types)} agents"}

    # Load recon — from request or S3
    blueprint_data = request.blueprint_context
    if not blueprint_data and request.campaign_id:
        yield {"type": "log", "message": f"Loading recon from S3 for campaign: {request.campaign_id}"}
        try:
            blueprint_data = await load_recon_for_campaign(request.campaign_id)
            if not blueprint_data:
                yield {"type": "log", "level": "error", "message": f"No recon data found for campaign {request.campaign_id}"}
                return
            yield {"type": "log", "message": "Recon data loaded from S3"}
        except Exception as e:
            yield {"type": "log", "level": "error", "message": f"Failed to load recon from S3: {e}"}
            return

    if not blueprint_data:
        yield {"type": "log", "level": "error", "message": "No blueprint_context or campaign_id provided"}
        return

    audit_id = blueprint_data.get("audit_id", "unknown")
    target_url = (
        request.target_url
        or blueprint_data.get("target_url")
        or "https://api.target.local/v1/chat"
    )

    safety_policy = (
        {"blocked_attack_vectors": request.safety_policy.blocked_attack_vectors or []}
        if request.safety_policy else None
    )

    cfg = request.scan_config
    scan_config = {k: getattr(cfg, k, v) for k, v in _SCAN_CONFIG_DEFAULTS.items()} if cfg else _SCAN_CONFIG_DEFAULTS.copy()
    if cfg and cfg.requests_per_second is not None:
        scan_config["requests_per_second"] = cfg.requests_per_second

    state = ScanState(
        audit_id=audit_id,
        target_url=target_url,
        agent_types=agent_types,
        recon_context=blueprint_data,
        scan_config=scan_config,
        safety_policy=safety_policy,
    )

    get_cancellation_manager(audit_id)
    logger.info(f"Registered cancellation manager for scan {audit_id}")

    event_queue: List[Dict[str, Any]] = []

    async def emit(event: Dict[str, Any]) -> None:
        event_queue.append(event)

    try:
        # Phase 1: Load and validate recon
        await load_recon(state, emit)
        while event_queue:
            yield event_queue.pop(0)

        if state.cancelled or state.has_fatal_error:
            await persist_results(state, emit)
            while event_queue:
                yield event_queue.pop(0)
            return

        # Phase 2–3: Plan and execute per agent
        for _agent_type in state.agent_types:
            if state.cancelled:
                break

            await plan_agent(state, emit)
            while event_queue:
                yield event_queue.pop(0)

            if state.cancelled or not state.current_plan:
                break

            await execute_agent(state, emit)
            while event_queue:
                yield event_queue.pop(0)

            state.current_agent_index += 1
            state.current_plan = None

            if state.cancelled:
                break

        # Phase 4: Persist results (always runs)
        await persist_results(state, emit)
        while event_queue:
            yield event_queue.pop(0)

    except Exception as e:
        logger.error(f"Scan orchestration error: {e}", exc_info=True)
        yield {"type": "log", "level": "error", "message": f"Scan failed: {e}"}
        yield {"type": "complete", "data": {"audit_id": audit_id, "agents": {}, "error": str(e)}}
    finally:
        remove_cancellation_manager(audit_id)
        logger.info(f"Cleaned up cancellation manager for scan {audit_id}")


# Control functions for API endpoints

def _get_manager_or_none(scan_id: str):
    """Return (manager, None) if scan exists, or (None, error_dict) if not."""
    if scan_id not in get_active_scan_ids():
        return None, {"scan_id": scan_id, "found": False, "message": "Scan not found"}
    return get_cancellation_manager(scan_id), None


def cancel_scan(scan_id: str) -> Dict[str, Any]:
    """Cancel a running scan."""
    manager, err = _get_manager_or_none(scan_id)
    if err:
        return err
    manager.cancel()
    logger.info(f"Cancelled scan {scan_id}")
    return {"scan_id": scan_id, "cancelled": True}


def pause_scan(scan_id: str) -> Dict[str, Any]:
    """Pause a running scan at the next checkpoint."""
    manager, err = _get_manager_or_none(scan_id)
    if err:
        return err
    manager.pause()
    logger.info(f"Paused scan {scan_id}")
    return {"scan_id": scan_id, "paused": True}


def resume_scan(scan_id: str) -> Dict[str, Any]:
    """Resume a paused scan."""
    manager, err = _get_manager_or_none(scan_id)
    if err:
        return err
    manager.resume()
    logger.info(f"Resumed scan {scan_id}")
    return {"scan_id": scan_id, "paused": False}


def get_scan_status(scan_id: str) -> Dict[str, Any]:
    """Get the current status of a scan."""
    manager, err = _get_manager_or_none(scan_id)
    if err:
        return err
    return {"scan_id": scan_id, "found": True, "cancelled": manager.is_cancelled, "paused": manager.is_paused}
