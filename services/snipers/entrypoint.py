"""Public API for the Snipers service.

Three execution modes:
- execute_full_attack_streaming()      One-shot Phase 1→2→3, emits SSE events
- execute_adaptive_attack_streaming()  Adaptive while-loop; iterates until success or max_iterations
- resume_adaptive_attack_streaming()   Resume a paused adaptive attack from S3 checkpoint
"""

import logging
import time
import uuid
from typing import Any, AsyncGenerator

from libs.persistence import CheckpointStatus
from services.snipers.core.components.pause_signal import clear_pause
from services.snipers.core.loop.adaptation.constants import FRAMING_TYPES
from services.snipers.core.loop.adaptation.evaluation import check_success  # noqa: F401
from services.snipers.core.loop.events.builders import make_event
from services.snipers.core.loop.runner.loop_runner import run_loop
from services.snipers.core.loop.runner.state import LoopState, create_initial_checkpoint
from services.snipers.core.phases import (
    PayloadArticulation,
    Conversion,
    AttackExecution,
)
from services.snipers.infrastructure.persistence.s3_adapter import (
    load_checkpoint as load_checkpoint_from_s3,
    set_checkpoint_status,
)
from services.snipers.core.loop.entrypoint_helpers import (
    FullAttackResult,
    make_stream_event,
    persist_full_attack_result,
    persist_adaptive_streaming_result,
    stream_phase1_events,
    stream_phase2_events,
    stream_phase3_events,
)

logger = logging.getLogger(__name__)


async def execute_full_attack_streaming(
    campaign_id: str,
    target_url: str,
    payload_count: int = 3,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    max_concurrent: int = 3,
) -> AsyncGenerator[dict[str, Any], None]:
    """Execute complete three-phase attack with SSE streaming events."""
    start_time = time.time()
    scan_id = f"{campaign_id}-{uuid.uuid4().hex[:8]}"

    # Attack started
    yield make_stream_event(
        "attack_started",
        f"Starting attack on {target_url}",
        data={
            "campaign_id": campaign_id,
            "target_url": target_url,
            "scan_id": scan_id,
            "payload_count": payload_count,
        },
    )

    result1 = None
    result2 = None
    result3 = None

    try:
        # Phase 1: Payload Articulation
        yield make_stream_event("phase1_start", "Phase 1: Loading intelligence and generating payloads", phase="phase1", progress=0.0)
        phase1 = PayloadArticulation()
        yield make_stream_event("phase1_progress", "Loading campaign intelligence from S3", phase="phase1", progress=0.2)
        
        result1 = await phase1.execute(
            campaign_id=campaign_id,
            payload_count=payload_count,
            framing_types=framing_types,
        )
        
        async for event in stream_phase1_events(result1):
            yield event

        # Phase 2: Conversion
        yield make_stream_event("phase2_start", "Phase 2: Applying converter chain transformations", phase="phase2", progress=0.0)
        phase2 = Conversion()
        result2 = await phase2.execute(
            payloads=result1.articulated_payloads,
            chain=result1.selected_chain if not converter_names else None,
            converter_names=converter_names,
        )
        
        async for event in stream_phase2_events(result2):
            yield event

        # Phase 3: Attack Execution
        yield make_stream_event("phase3_start", f"Phase 3: Executing attacks against {target_url}", phase="phase3", data={"target_url": target_url, "payloads_count": len(result2.payloads)}, progress=0.0)
        phase3 = AttackExecution(target_url=target_url)
        result3 = await phase3.execute(
            campaign_id=campaign_id,
            payloads=result2.payloads,
            chain=result1.selected_chain,
            max_concurrent=max_concurrent,
        )
        
        async for event in stream_phase3_events(result3):
            yield event

        # Persist and Complete
        full_result = FullAttackResult(
            campaign_id=campaign_id,
            target_url=target_url,
            phase1=result1,
            phase2=result2,
            phase3=result3,
            is_successful=result3.is_successful,
            overall_severity=result3.overall_severity,
            total_score=result3.total_score,
            payloads_generated=len(result1.articulated_payloads),
            payloads_sent=len(result3.attack_responses),
        )

        await persist_full_attack_result(
            full_result, campaign_id, target_url, start_time, scan_id=scan_id
        )

        yield make_stream_event(
            "attack_complete",
            f"Attack complete: {'BREACH DETECTED' if result3.is_successful else 'Target secure'}",
            data={
                "scan_id": scan_id,
                "campaign_id": campaign_id,
                "is_successful": result3.is_successful,
                "overall_severity": result3.overall_severity,
                "total_score": result3.total_score,
                "payloads_generated": len(result1.articulated_payloads),
                "payloads_sent": len(result3.attack_responses),
            },
        )

    except Exception as e:
        logger.exception(f"Streaming attack failed: {e}")
        yield make_stream_event(
            "error",
            f"Attack failed: {str(e)}",
            phase="phase1" if result1 is None else ("phase2" if result2 is None else "phase3"),
            data={"error": str(e), "error_type": type(e).__name__},
        )
        raise


async def execute_adaptive_attack_streaming(
    campaign_id: str,
    target_url: str,
    max_iterations: int = 5,
    payload_count: int = 2,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
) -> AsyncGenerator[dict[str, Any], None]:
    """Execute adaptive attack with SSE streaming events."""
    start_time = time.time()
    scan_id = f"{campaign_id}-adaptive-{uuid.uuid4().hex[:8]}"
    final_state: dict[str, Any] | None = None
    was_paused = False

    async for event in _run_adaptive_loop(
        campaign_id=campaign_id,
        target_url=target_url,
        scan_id=scan_id,
        max_iterations=max_iterations,
        payload_count=payload_count,
        framing_types=framing_types,
        converter_names=converter_names,
        success_scorers=success_scorers,
        success_threshold=success_threshold,
        enable_checkpoints=True,
    ):
        if event.get("type") == "attack_paused":
            was_paused = True
        if event.get("type") == "attack_complete":
            final_state = event.get("data", {})
            if event.get("data"):
                event["data"]["scan_id"] = scan_id
        yield event

    if final_state and not was_paused:
        await persist_adaptive_streaming_result(
            final_state, scan_id, campaign_id, target_url, start_time
        )


async def resume_adaptive_attack_streaming(
    campaign_id: str,
    scan_id: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """Resume an adaptive attack from an S3 checkpoint."""
    checkpoint = await load_checkpoint_from_s3(campaign_id, scan_id)
    if not checkpoint:
        yield make_event("error", f"Checkpoint not found: {campaign_id}/{scan_id}",
                         data={"error": "Checkpoint not found"})
        return

    if checkpoint.status not in [CheckpointStatus.PAUSED, CheckpointStatus.RUNNING]:
        yield make_event("error", f"Cannot resume: status {checkpoint.status.value}",
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

    async for event in _run_adaptive_loop(
        campaign_id=campaign_id,
        target_url=checkpoint.target_url,
        scan_id=scan_id,
        max_iterations=remaining,
        payload_count=checkpoint.config.payload_count,
        success_scorers=checkpoint.config.success_scorers or None,
        success_threshold=checkpoint.config.success_threshold,
        enable_checkpoints=True,
    ):
        yield event


async def _run_adaptive_loop(
    campaign_id: str,
    target_url: str,
    scan_id: str,
    max_iterations: int,
    payload_count: int,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
    enable_checkpoints: bool = True,
) -> AsyncGenerator[dict[str, Any], None]:
    """Initialise loop state and run the adaptive while-loop."""
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



