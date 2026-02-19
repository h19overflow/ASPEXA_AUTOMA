"""
Adaptive Attack Loop.

Purpose: Iterative attack loop that analyzes failures and evolves strategy
Role: Orchestrates Phase 1->2->3 with LLM-powered adaptation between iterations
Dependencies: Phase implementations, LLM agents, S3 persistence

Simple while loop replacing the former LangGraph state machine.
Same functionality, fewer abstractions.
"""

import logging
from typing import Any, AsyncGenerator

from libs.persistence import CheckpointStatus
from services.snipers.core.components.pause_signal import clear_pause
from services.snipers.infrastructure.persistence.s3_adapter import (
    load_checkpoint as load_checkpoint_from_s3,
    set_checkpoint_status,
)
from services.snipers.internals.constants import ALL_SCORERS, FRAMING_TYPES
from services.snipers.internals.events import make_event
from services.snipers.internals.loop_runner import LoopState, create_initial_checkpoint, run_loop

# Backward-compatible re-exports
from services.snipers.internals.evaluation import check_success  # noqa: F401

logger = logging.getLogger(__name__)


async def run_adaptive_attack_streaming(
    campaign_id: str,
    target_url: str,
    scan_id: str,
    max_iterations: int = 5,
    payload_count: int = 2,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
    enable_checkpoints: bool = True,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Run adaptive attack loop with SSE streaming and checkpoint support.

    Simple while loop: each iteration runs Phase 1->2->3, evaluates,
    then adapts strategy via LLM agents if not successful.
    """
    success_scorers = success_scorers or []
    clear_pause(scan_id)

    if enable_checkpoints:
        await create_initial_checkpoint(
            campaign_id, scan_id, target_url,
            max_iterations, payload_count, success_scorers, success_threshold,
        )

    yield make_event(
        "attack_started", f"Starting adaptive attack on {target_url}",
        data={"campaign_id": campaign_id, "target_url": target_url,
              "scan_id": scan_id, "max_iterations": max_iterations,
              "payload_count": payload_count},
    )

    state = LoopState(
        converters=converter_names or ["rot13"],
        framings=framing_types or [FRAMING_TYPES[0]],
    )

    try:
        async for event in run_loop(
            campaign_id, target_url, scan_id, max_iterations,
            payload_count, success_scorers, success_threshold,
            enable_checkpoints, state,
        ):
            yield event
    except Exception as e:
        logger.exception(f"Adaptive attack failed: {e}")
        yield make_event("error", f"Adaptive attack failed: {str(e)}",
                         data={"error": str(e), "error_type": type(e).__name__})
        raise


async def run_adaptive_attack(
    campaign_id: str,
    target_url: str,
    max_iterations: int = 5,
    payload_count: int = 2,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
) -> dict[str, Any]:
    """Run adaptive attack (non-streaming). Returns final state dict."""
    import uuid

    scan_id = f"{campaign_id}-adaptive-{uuid.uuid4().hex[:8]}"
    final_event: dict[str, Any] = {}

    async for event in run_adaptive_attack_streaming(
        campaign_id=campaign_id, target_url=target_url, scan_id=scan_id,
        max_iterations=max_iterations, payload_count=payload_count,
        framing_types=framing_types, converter_names=converter_names,
        success_scorers=success_scorers, success_threshold=success_threshold,
        enable_checkpoints=False,
    ):
        if event.get("type") == "attack_complete":
            final_event = event.get("data", {})

    return final_event


async def resume_adaptive_attack_streaming(
    campaign_id: str,
    scan_id: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """Resume an adaptive attack from a checkpoint."""
    checkpoint = await load_checkpoint_from_s3(campaign_id, scan_id)
    if not checkpoint:
        yield make_event("error", f"Checkpoint not found: {campaign_id}/{scan_id}",
                         data={"error": "Checkpoint not found"})
        return

    if checkpoint.status not in [CheckpointStatus.PAUSED, CheckpointStatus.RUNNING]:
        yield make_event("error",
                         f"Cannot resume: status {checkpoint.status.value}",
                         data={"error": f"Invalid status: {checkpoint.status.value}"})
        return

    await set_checkpoint_status(campaign_id, scan_id, CheckpointStatus.RUNNING)

    yield make_event(
        "attack_resumed",
        f"Resuming attack from iteration {checkpoint.current_iteration}",
        iteration=checkpoint.current_iteration,
        data={"scan_id": scan_id, "campaign_id": campaign_id,
              "resuming_from_iteration": checkpoint.current_iteration,
              "best_score": checkpoint.best_score,
              "target_url": checkpoint.target_url},
    )

    remaining = checkpoint.config.max_iterations - checkpoint.current_iteration
    if remaining <= 0:
        yield make_event("attack_complete", "Already at max iterations",
                         data={"scan_id": scan_id,
                               "is_successful": checkpoint.is_successful,
                               "total_iterations": checkpoint.current_iteration,
                               "best_score": checkpoint.best_score})
        return

    async for event in run_adaptive_attack_streaming(
        campaign_id=campaign_id, target_url=checkpoint.target_url,
        scan_id=scan_id, max_iterations=remaining,
        payload_count=checkpoint.config.payload_count,
        success_scorers=checkpoint.config.success_scorers or None,
        success_threshold=checkpoint.config.success_threshold,
        enable_checkpoints=True,
    ):
        yield event
