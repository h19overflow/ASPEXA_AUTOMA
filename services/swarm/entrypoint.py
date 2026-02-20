"""HTTP entrypoint for Swarm scanning service.

Purpose: Orchestrate sequential scan phases with async streaming
Dependencies: phases/, core/schema.py, swarm_observability, persistence

Architecture:
- Sequential phases: load_recon → run_deterministic_planning → run_probe_execution → persist_results
- ScanState is a plain dataclass (no LangGraph)
- emit() callback passes events directly to the async generator
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
    run_deterministic_planning,
    run_probe_execution,
    persist_results,
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

    Orchestrates four sequential phases per scan category:
    1. load_recon — validate recon context
    2. run_deterministic_planning — select probes deterministically
    3. run_probe_execution — run scanner, stream probe/prompt events
    4. persist_results — save to S3, emit SCAN_COMPLETE

    Args:
        request: Scan job dispatch with target info and config
        agent_types: Agent types to run (defaults to SQL, AUTH, JAILBREAK)

    Yields:
        SSE event dicts for real-time UI updates
    """
    if agent_types is None:
        agent_types = [AgentType.SQL.value, AgentType.AUTH.value, AgentType.JAILBREAK.value]

    yield {"type": "log", "message": f"Starting scan with {len(agent_types)} categories"}

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

    event_queue: List[Dict[str, Any]] = []

    async def emit(event: Dict[str, Any]) -> None:
        event_queue.append(event)

    try:
        # Phase 1: Load and validate recon
        await load_recon(state, emit)
        while event_queue:
            yield event_queue.pop(0)

        if state.has_fatal_error:
            await persist_results(state, emit)
            while event_queue:
                yield event_queue.pop(0)
            return

        # Phase 2–3: Plan and execute per category
        for _agent_type in state.agent_types:
            await run_deterministic_planning(state, emit)
            while event_queue:
                yield event_queue.pop(0)

            if not state.current_plan:
                break

            await run_probe_execution(state, emit)
            while event_queue:
                yield event_queue.pop(0)

            state.current_agent_index += 1
            state.current_plan = None

        # Phase 4: Persist results (always runs)
        await persist_results(state, emit)
        while event_queue:
            yield event_queue.pop(0)

    except Exception as e:
        logger.error(f"Scan orchestration error: {e}", exc_info=True)
        yield {"type": "log", "level": "error", "message": f"Scan failed: {e}"}
        yield {"type": "complete", "data": {"audit_id": audit_id, "agents": {}, "error": str(e)}}
