"""Scanning router - HTTP endpoints for Swarm service."""
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from libs.contracts.scanning import ScanJobDispatch, SafetyPolicy, ScanConfigContract
from services.api_gateway.utils import serialize_event
from services.swarm.entrypoint import (
    execute_scan_streaming,
)
from services.api_gateway.schemas import ScanStartRequest

router = APIRouter(prefix="/scan", tags=["scanning"])


def _build_scan_config(request: ScanStartRequest) -> ScanConfigContract:
    """Convert API request config to contract config."""
    if not request.config:
        return ScanConfigContract()

    cfg = request.config
    return ScanConfigContract(
        approach=cfg.approach,
        custom_probes=cfg.custom_probes or [],
        max_probes=cfg.max_probes,
        max_prompts_per_probe=cfg.max_prompts_per_probe,
        requests_per_second=cfg.requests_per_second,
        request_timeout=cfg.request_timeout,
        max_retries=cfg.max_retries,
        retry_backoff=cfg.retry_backoff,
        connection_type=cfg.connection_type,
    )


@router.post("/start/stream")
async def start_scan_stream(request: ScanStartRequest) -> StreamingResponse:
    """Start vulnerability scanning with real-time log streaming via SSE.

    Returns Server-Sent Events with probe results and progress.

    Accepts either:
    - campaign_id: Swarm service loads recon from S3
    - blueprint_context: Direct recon data (for testing/manual runs)
    """
    safety_policy = SafetyPolicy(
        allowed_attack_vectors=request.allowed_attack_vectors,
        blocked_attack_vectors=request.blocked_attack_vectors,
        aggressiveness=request.aggressiveness,
    )
    scan_config = _build_scan_config(request)

    # Build dispatch - Swarm service handles recon loading via campaign_id
    scan_dispatch = ScanJobDispatch(
        job_id=request.campaign_id or "manual",
        campaign_id=request.campaign_id,
        blueprint_context=request.blueprint_context,
        safety_policy=safety_policy,
        scan_config=scan_config,
        target_url=request.target_url,
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in execute_scan_streaming(
            scan_dispatch,
            agent_types=request.agent_types,
        ):
            yield f"data: {serialize_event(event)}\n\n"

    # Use campaign_id as scan_id hint (actual scan_id is audit_id from recon)
    scan_id_hint = request.campaign_id or "unknown"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Scan-Id": scan_id_hint,
        },
    )



