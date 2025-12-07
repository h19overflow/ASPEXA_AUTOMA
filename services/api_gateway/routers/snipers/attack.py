"""
Full Attack & Adaptive Attack Router.

Purpose: HTTP endpoints for complete attack execution
Role: Orchestrates all three phases or adaptive loop
Dependencies: entrypoint functions, Attack schemas
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from services.api_gateway.schemas.snipers import (
    FullAttackRequest,
    AdaptiveAttackRequest,
)
from services.api_gateway.utils import serialize_event
from services.snipers.entrypoint import (
    execute_full_attack_streaming,
    execute_adaptive_attack_streaming,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attack", tags=["snipers-attack"])


@router.post("/full/stream")
async def run_full_attack_stream(request: FullAttackRequest) -> StreamingResponse:
    """
    Execute complete single-shot attack with SSE streaming.

    Returns Server-Sent Events for real-time monitoring of each phase:
    - attack_started: Initial attack configuration
    - phase1_start/progress/complete: Payload articulation events
    - payload_generated: Each generated payload
    - phase2_start/progress/complete: Conversion events
    - payload_converted: Each converted payload
    - phase3_start/progress/complete: Attack execution events
    - attack_sent: Each attack sent to target
    - response_received: Each target response
    - score_calculated: Each scorer result
    - attack_complete: Final result with all data
    - error: Any errors during execution

    Results are persisted to S3 and campaign stage is updated.
    """
    try:
        # Convert framing types to strings
        framing_types = None
        if request.framing_types:
            framing_types = [f.value for f in request.framing_types]

        async def event_generator() -> AsyncGenerator[str, None]:
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
                # Yield error event before closing stream
                error_event = {
                    "type": "error",
                    "message": f"Stream error: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__},
                }
                yield f"data: {serialize_event(error_event)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except ValueError as e:
        logger.error(f"Full attack stream validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Full attack stream setup error: {e}")
        raise HTTPException(status_code=500, detail=f"Full attack stream failed: {e}")


@router.post("/adaptive/stream")
async def run_adaptive_attack_stream(request: AdaptiveAttackRequest) -> StreamingResponse:
    """
    Execute adaptive attack with SSE streaming.

    Returns Server-Sent Events for real-time monitoring of each iteration:
    - attack_started: Initial attack configuration
    - iteration_start: New iteration starting
    - phase1_start/complete: Payload articulation events
    - payload_generated: Each generated payload
    - phase2_start/complete: Conversion events
    - payload_converted: Each converted payload
    - phase3_start/complete: Attack execution events
    - attack_sent: Each attack sent to target
    - response_received: Each target response
    - score_calculated: Each scorer result
    - iteration_complete: Iteration result summary
    - adaptation: Strategy adaptation between iterations
    - attack_complete: Final result with all data
    - error: Any errors during execution

    Results are persisted to S3 and campaign stage is updated.
    """
    try:
        # Convert enums to strings
        framing_types = None
        if request.framing_types:
            framing_types = [f.value for f in request.framing_types]

        success_scorers = None
        if request.success_scorers:
            success_scorers = [s.value for s in request.success_scorers]

        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                async for event in execute_adaptive_attack_streaming(
                    campaign_id=request.campaign_id,
                    target_url=request.target_url,
                    max_iterations=request.max_iterations,
                    payload_count=request.payload_count,
                    framing_types=framing_types,
                    converter_names=request.converter_names,
                    success_scorers=success_scorers,
                    success_threshold=request.success_threshold,
                ):
                    yield f"data: {serialize_event(event)}\n\n"
            except Exception as e:
                # Yield error event before closing stream
                error_event = {
                    "type": "error",
                    "message": f"Stream error: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__},
                }
                yield f"data: {serialize_event(error_event)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except ValueError as e:
        logger.error(f"Adaptive attack stream validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Adaptive attack stream setup error: {e}")
        raise HTTPException(status_code=500, detail=f"Adaptive attack stream failed: {e}")
