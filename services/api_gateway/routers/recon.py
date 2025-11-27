"""Reconnaissance router - HTTP endpoints for Cartographer service."""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from libs.contracts.recon import ReconRequest, TargetConfig, ScopeConfig
from libs.contracts.common import DepthLevel
from services.cartographer.entrypoint import  execute_recon_streaming
from services.api_gateway.schemas import ReconStartRequest

router = APIRouter(prefix="/recon", tags=["reconnaissance"])


@router.post("/start/stream")
async def start_recon_stream(request: ReconStartRequest) -> StreamingResponse:
    """Start reconnaissance with real-time log streaming via SSE.

    Returns Server-Sent Events with log messages and final result.
    """
    try:
        depth = DepthLevel(request.depth)
    except ValueError:
        raise HTTPException(400, f"Invalid depth: {request.depth}")

    recon_request = ReconRequest(
        audit_id=request.audit_id,
        target=TargetConfig(url=request.target_url, auth_headers=request.auth_headers),
        scope=ScopeConfig(
            depth=depth,
            max_turns=request.max_turns,
            forbidden_keywords=request.forbidden_keywords,
        ),
        special_instructions=request.special_instructions,
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in execute_recon_streaming(recon_request):
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
