"""
Adaptive Attack Router.

Purpose: HTTP endpoints for adaptive attack execution with pause/resume and checkpoint support
Role: Streams iterative attack loop via SSE; manages pause signals and S3 checkpoints
Dependencies: execute_adaptive_attack_streaming, resume_adaptive_attack_streaming, pause_signal, s3_adapter
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from services.api_gateway.schemas.snipers import (
    AdaptiveAttackRequest,
    CheckpointSummary,
    CheckpointDetail,
    PauseResponse,
)
from services.api_gateway.utils import serialize_event
from services.snipers.entrypoint import execute_adaptive_attack_streaming
from services.snipers.graphs.adaptive_attack.graph import resume_adaptive_attack_streaming
from services.snipers.graphs.adaptive_attack.components.pause_signal import (
    request_pause,
    is_pause_requested,
)
from services.snipers.infrastructure.persistence.s3_adapter import (
    load_checkpoint,
    get_latest_checkpoint,
    list_campaign_checkpoints,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attack", tags=["snipers-attack"])


@router.post("/adaptive/stream")
async def run_adaptive_attack_stream(request: AdaptiveAttackRequest) -> StreamingResponse:
    """
    Execute adaptive attack with SSE streaming.

    Streams iteration markers (iteration_start/complete), per-payload events,
    adaptation events between iterations, checkpoint_saved events, and a
    final attack_complete or error event.
    """
    try:
        framing_types = None
        if request.framing_types:
            framing_types = [f.value for f in request.framing_types]

        success_scorers = None
        if request.success_scorers:
            success_scorers = [s.value for s in request.success_scorers]

        async def event_generator():
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
                yield f"data: {serialize_event({'type': 'error', 'message': f'Stream error: {e}', 'data': {'error': str(e), 'error_type': type(e).__name__}})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    except ValueError as e:
        logger.error(f"Adaptive attack validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Adaptive attack setup error: {e}")
        raise HTTPException(status_code=500, detail=f"Adaptive attack stream failed: {e}")


@router.post("/adaptive/pause/{scan_id}", response_model=PauseResponse)
async def pause_adaptive_attack(scan_id: str) -> PauseResponse:
    """
    Request pause after the current iteration completes.
    Progress is saved to a checkpoint that can be resumed later.
    """
    try:
        if is_pause_requested(scan_id):
            return PauseResponse(
                success=True,
                message="Pause already requested, waiting for iteration to complete",
                scan_id=scan_id,
            )

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


@router.post("/adaptive/resume/{campaign_id}/{scan_id}")
async def resume_adaptive_attack(campaign_id: str, scan_id: str) -> StreamingResponse:
    """
    Resume an adaptive attack from a checkpoint with SSE streaming.
    Emits attack_resumed at start, then continues the normal adaptive stream.
    """
    try:
        async def event_generator():
            try:
                async for event in resume_adaptive_attack_streaming(
                    campaign_id=campaign_id,
                    scan_id=scan_id,
                ):
                    yield f"data: {serialize_event(event)}\n\n"
            except Exception as e:
                yield f"data: {serialize_event({'type': 'error', 'message': f'Resume stream error: {e}', 'data': {'error': str(e), 'error_type': type(e).__name__}})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    except Exception as e:
        logger.exception(f"Resume attack setup error: {e}")
        raise HTTPException(status_code=500, detail=f"Resume attack failed: {e}")


@router.get("/adaptive/checkpoint/{campaign_id}", response_model=CheckpointDetail)
async def get_checkpoint(campaign_id: str) -> CheckpointDetail:
    """Get the latest checkpoint for a campaign. Returns 404 if none exists."""
    try:
        checkpoint = await get_latest_checkpoint(campaign_id)

        if not checkpoint:
            raise HTTPException(status_code=404, detail=f"No checkpoint found for campaign {campaign_id}")

        return _map_checkpoint_detail(checkpoint)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get checkpoint failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get checkpoint failed: {e}")


@router.get("/adaptive/checkpoint/{campaign_id}/{scan_id}", response_model=CheckpointDetail)
async def get_checkpoint_by_scan_id(campaign_id: str, scan_id: str) -> CheckpointDetail:
    """Get a specific checkpoint by campaign and scan ID. Returns 404 if not found."""
    try:
        checkpoint = await load_checkpoint(campaign_id, scan_id)

        if not checkpoint:
            raise HTTPException(status_code=404, detail=f"Checkpoint not found: {campaign_id}/{scan_id}")

        return _map_checkpoint_detail(checkpoint)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get checkpoint by scan_id failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get checkpoint failed: {e}")


@router.get("/adaptive/checkpoints/{campaign_id}", response_model=List[CheckpointSummary])
async def list_checkpoints(campaign_id: str) -> List[CheckpointSummary]:
    """List all checkpoints for a campaign, sorted newest first."""
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


def _map_checkpoint_detail(checkpoint) -> CheckpointDetail:
    """Map a checkpoint domain object to the CheckpointDetail response schema."""
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
        iteration_history=[iter_item.model_dump() for iter_item in checkpoint.iteration_history],
    )
