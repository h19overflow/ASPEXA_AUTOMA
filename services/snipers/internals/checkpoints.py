"""Checkpoint persistence for the adaptive attack loop."""

import logging
from typing import Any, AsyncGenerator

from libs.persistence import (
    CheckpointIteration,
    CheckpointResumeState,
    CheckpointStatus,
)
from services.snipers.infrastructure.persistence.s3_adapter import update_checkpoint
from services.snipers.internals.events import make_event
from services.snipers.models import Phase3Result

logger = logging.getLogger(__name__)


async def save_checkpoint_events(
    campaign_id: str,
    scan_id: str,
    iteration: int,
    phase2_result: Any,
    phase3_result: Phase3Result | None,
    is_successful: bool,
    best_score: float,
    best_iteration: int,
    current_framings: list[str],
    current_converters: list[str],
    tried_framings: list[str],
    tried_converters: list[list[str]],
    adaptation_reasoning: str,
    scorer_confidences: dict[str, float],
) -> AsyncGenerator[dict[str, Any], None]:
    """Save checkpoint and yield checkpoint_saved event."""
    try:
        iteration_data = _build_iteration_data(
            iteration, phase2_result, phase3_result, is_successful,
            current_framings, current_converters, scorer_confidences,
            adaptation_reasoning,
        )
        resume_state = CheckpointResumeState(
            tried_framings=tried_framings,
            tried_converters=tried_converters,
            chain_discovery_context=None,
            custom_framing=None,
            defense_analysis={},
            target_responses=[],
        )
        status = CheckpointStatus.COMPLETED if is_successful else CheckpointStatus.RUNNING

        await update_checkpoint(
            campaign_id=campaign_id,
            scan_id=scan_id,
            iteration=iteration_data,
            resume_state=resume_state,
            best_score=best_score,
            best_iteration=best_iteration,
            is_successful=is_successful,
            status=status,
        )

        yield make_event(
            "checkpoint_saved",
            f"Progress saved (iteration {iteration + 1})",
            iteration=iteration + 1,
            data={"scan_id": scan_id, "can_resume": True},
        )
    except Exception as e:
        logger.warning(f"Failed to save checkpoint: {e}")


def _build_iteration_data(
    iteration: int,
    phase2_result: Any,
    phase3_result: Phase3Result | None,
    is_successful: bool,
    current_framings: list[str],
    current_converters: list[str],
    scorer_confidences: dict[str, float],
    adaptation_reasoning: str,
) -> CheckpointIteration:
    payloads = []
    if phase2_result:
        payloads = [{"original": p.original, "converted": p.converted}
                    for p in phase2_result.payloads]
    responses = []
    if phase3_result:
        responses = [{"response": r.response, "status_code": r.status_code,
                      "latency_ms": r.latency_ms}
                     for r in phase3_result.attack_responses]

    return CheckpointIteration(
        iteration=iteration + 1,
        score=phase3_result.total_score if phase3_result else 0.0,
        is_successful=is_successful,
        framing=current_framings,
        converters=current_converters,
        scorer_confidences=scorer_confidences,
        payloads=payloads,
        responses=responses,
        adaptation_reasoning=adaptation_reasoning,
        error=None,
    )
