"""Scanning router - HTTP endpoints for Swarm service."""
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from libs.contracts.scanning import ScanJobDispatch, SafetyPolicy, ScanConfigContract
from services.swarm.entrypoint import execute_scan_streaming
from services.api_gateway.schemas import ScanStartRequest

router = APIRouter(prefix="/scan", tags=["scanning"])


def _build_scan_config(request: ScanStartRequest) -> ScanConfigContract:
    """Convert API request config to contract config."""
    if not request.config:
        return ScanConfigContract()

    cfg = request.config
    return ScanConfigContract(
        approach=cfg.approach,
        generations=cfg.generations,
        custom_probes=cfg.custom_probes or [],
        allow_agent_override=cfg.allow_agent_override,
        max_probes=cfg.max_probes,
        max_generations=cfg.max_generations,
        enable_parallel_execution=cfg.enable_parallel_execution,
        max_concurrent_probes=cfg.max_concurrent_probes,
        max_concurrent_generations=cfg.max_concurrent_generations,
        requests_per_second=cfg.requests_per_second,
        max_concurrent_connections=cfg.max_concurrent_connections,
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
        async for event in execute_scan_streaming(scan_dispatch, request.agent_types):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
