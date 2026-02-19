"""
One-Shot Attack Router.

Purpose: HTTP endpoint for single-shot full attack execution (all 3 phases)
Role: Streams phase1 → phase2 → phase3 results via SSE
Dependencies: execute_full_attack_streaming, FullAttackRequest
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from services.api_gateway.schemas.snipers import FullAttackRequest
from services.api_gateway.utils import serialize_event
from services.snipers.entrypoint import execute_full_attack_streaming

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attack", tags=["snipers-attack"])


@router.post("/full/stream")
async def run_full_attack_stream(request: FullAttackRequest) -> StreamingResponse:
    """
    Execute complete single-shot attack with SSE streaming.

    Streams phase markers (phase1_start/complete, phase2_start/complete,
    phase3_start/complete), per-payload events (payload_generated,
    payload_converted, attack_sent, response_received, score_calculated),
    and a final attack_complete or error event.
    """
    try:
        framing_types = None
        if request.framing_types:
            framing_types = [f.value for f in request.framing_types]

        async def event_generator():
            try:
                async for event in execute_full_attack_streaming(
                    campaign_id=request.campaign_id,
                    target_url=request.target_url,
                    payload_count=request.payload_count,
                    framing_types=framing_types,
                    converter_names=request.converter_names,
                    max_concurrent=request.max_concurrent,
                ):
                    yield f"data: {serialize_event(event)}\n\n"
            except Exception as e:
                yield f"data: {serialize_event({'type': 'error', 'message': f'Stream error: {e}', 'data': {'error': str(e), 'error_type': type(e).__name__}})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    except ValueError as e:
        logger.error(f"Full attack validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Full attack setup error: {e}")
        raise HTTPException(status_code=500, detail=f"Full attack stream failed: {e}")
