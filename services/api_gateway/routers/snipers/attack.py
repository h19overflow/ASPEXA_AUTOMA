"""
Full Attack & Adaptive Attack Router.

Purpose: HTTP endpoints for complete attack execution
Role: Orchestrates all three phases or adaptive loop
Dependencies: entrypoint functions, Attack schemas

Checkpoint support:
- POST /adaptive/pause/{scan_id}: Request pause after current iteration
- POST /adaptive/resume/{scan_id}: Resume from checkpoint (SSE stream)
- GET /adaptive/checkpoint/{campaign_id}: Get latest checkpoint
- GET /adaptive/checkpoints/{campaign_id}: List all checkpoints
"""

import json
import logging
from typing import AsyncGenerator, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from services.api_gateway.schemas.snipers import (
    FullAttackRequest,
    AdaptiveAttackRequest,
    CheckpointSummary,
    CheckpointDetail,
    PauseResponse,
)
from services.api_gateway.utils import serialize_event
from services.snipers.entrypoint import (
    execute_full_attack_streaming,
    execute_adaptive_attack_streaming,
)
from services.snipers.adaptive_attack.graph import (
    resume_adaptive_attack_streaming,
)
from services.snipers.adaptive_attack.components.pause_signal import (
    request_pause,
    is_pause_requested,
)
from services.snipers.utils.persistence.s3_adapter import (
    load_checkpoint,
    get_latest_checkpoint,
    list_campaign_checkpoints,
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


# =============================================================================
# Checkpoint & Pause/Resume Endpoints
# =============================================================================


@router.post("/adaptive/pause/{scan_id}", response_model=PauseResponse)
async def pause_adaptive_attack(scan_id: str) -> PauseResponse:
    """
    Request to pause a running adaptive attack.

    The attack will complete its current iteration and then pause.
    Progress is automatically saved to a checkpoint which can be resumed later.

    Args:
        scan_id: Unique identifier of the running attack

    Returns:
        PauseResponse with success status and message
    """
    try:
        # Check if already requested
        if is_pause_requested(scan_id):
            return PauseResponse(
                success=True,
                message="Pause already requested, waiting for iteration to complete",
                scan_id=scan_id,
            )

        # Request pause
        request_pause(scan_id)
        logger.info(f"Pause requested for attack: {scan_id}")

        return PauseResponse(
            success=True,
            message="Pause requested, attack will stop after current iteration",
            scan_id=scan_id,
        )

    except Exception as e:
        logger.exception(f"Pause request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pause request failed: {e}")


@router.get("/adaptive/checkpoint/{campaign_id}", response_model=CheckpointDetail)
async def get_checkpoint(campaign_id: str) -> CheckpointDetail:
    """
    Get the latest checkpoint for a campaign.

    Returns the most recent checkpoint, useful for resuming interrupted attacks.

    Args:
        campaign_id: Campaign identifier

    Returns:
        CheckpointDetail with full checkpoint information

    Raises:
        404 if no checkpoint exists
    """
    try:
        checkpoint = await get_latest_checkpoint(campaign_id)

        if not checkpoint:
            raise HTTPException(
                status_code=404,
                detail=f"No checkpoint found for campaign {campaign_id}"
            )

        return CheckpointDetail(
            scan_id=checkpoint.scan_id,
            campaign_id=checkpoint.campaign_id,
            target_url=checkpoint.target_url,
            status=checkpoint.status.value,
            created_at=checkpoint.created_at,
            updated_at=checkpoint.updated_at,
            max_iterations=checkpoint.config.max_iterations,
            payload_count=checkpoint.config.payload_count,
            success_scorers=checkpoint.config.success_scorers,
            success_threshold=checkpoint.config.success_threshold,
            current_iteration=checkpoint.current_iteration,
            best_score=checkpoint.best_score,
            best_iteration=checkpoint.best_iteration,
            is_successful=checkpoint.is_successful,
            iteration_history=[
                iter_item.model_dump() for iter_item in checkpoint.iteration_history
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get checkpoint failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get checkpoint failed: {e}")


@router.get("/adaptive/checkpoint/{campaign_id}/{scan_id}", response_model=CheckpointDetail)
async def get_checkpoint_by_scan_id(campaign_id: str, scan_id: str) -> CheckpointDetail:
    """
    Get a specific checkpoint by campaign and scan ID.

    Args:
        campaign_id: Campaign identifier
        scan_id: Scan identifier

    Returns:
        CheckpointDetail with full checkpoint information

    Raises:
        404 if checkpoint doesn't exist
    """
    try:
        checkpoint = await load_checkpoint(campaign_id, scan_id)

        if not checkpoint:
            raise HTTPException(
                status_code=404,
                detail=f"Checkpoint not found: {campaign_id}/{scan_id}"
            )

        return CheckpointDetail(
            scan_id=checkpoint.scan_id,
            campaign_id=checkpoint.campaign_id,
            target_url=checkpoint.target_url,
            status=checkpoint.status.value,
            created_at=checkpoint.created_at,
            updated_at=checkpoint.updated_at,
            max_iterations=checkpoint.config.max_iterations,
            payload_count=checkpoint.config.payload_count,
            success_scorers=checkpoint.config.success_scorers,
            success_threshold=checkpoint.config.success_threshold,
            current_iteration=checkpoint.current_iteration,
            best_score=checkpoint.best_score,
            best_iteration=checkpoint.best_iteration,
            is_successful=checkpoint.is_successful,
            iteration_history=[
                iter_item.model_dump() for iter_item in checkpoint.iteration_history
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get checkpoint by scan_id failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get checkpoint failed: {e}")


@router.get("/adaptive/checkpoints/{campaign_id}", response_model=List[CheckpointSummary])
async def list_checkpoints(campaign_id: str) -> List[CheckpointSummary]:
    """
    List all checkpoints for a campaign.

    Returns summaries of all checkpoints, sorted by creation time (newest first).

    Args:
        campaign_id: Campaign identifier

    Returns:
        List of CheckpointSummary objects
    """
    try:
        checkpoints = await list_campaign_checkpoints(campaign_id)

        return [
            CheckpointSummary(
                scan_id=cp["scan_id"],
                campaign_id=campaign_id,
                status=cp["status"],
                current_iteration=cp["current_iteration"],
                best_score=cp["best_score"],
                is_successful=cp["is_successful"],
                created_at=cp["created_at"],
                updated_at=cp["updated_at"],
            )
            for cp in checkpoints
        ]

    except Exception as e:
        logger.exception(f"List checkpoints failed: {e}")
        raise HTTPException(status_code=500, detail=f"List checkpoints failed: {e}")


@router.post("/adaptive/resume/{campaign_id}/{scan_id}")
async def resume_adaptive_attack(campaign_id: str, scan_id: str) -> StreamingResponse:
    """
    Resume an adaptive attack from a checkpoint with SSE streaming.

    Loads the checkpoint state and continues the attack from where it left off.
    Returns a Server-Sent Events stream similar to the original attack stream.

    New events:
    - attack_resumed: Emitted at start with checkpoint details

    Args:
        campaign_id: Campaign identifier
        scan_id: Scan identifier of the checkpoint to resume

    Returns:
        StreamingResponse with SSE events
    """
    try:
        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                async for event in resume_adaptive_attack_streaming(
                    campaign_id=campaign_id,
                    scan_id=scan_id,
                ):
                    yield f"data: {serialize_event(event)}\n\n"
            except Exception as e:
                error_event = {
                    "type": "error",
                    "message": f"Resume stream error: {str(e)}",
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

    except Exception as e:
        logger.exception(f"Resume attack setup error: {e}")
        raise HTTPException(status_code=500, detail=f"Resume attack failed: {e}")
