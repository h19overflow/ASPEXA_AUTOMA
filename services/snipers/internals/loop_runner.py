"""Core loop logic for the adaptive attack loop."""

import logging
from typing import Any, AsyncGenerator

from libs.persistence import CheckpointConfig, CheckpointStatus
from services.snipers.core.components.pause_signal import clear_pause, is_pause_requested
from services.snipers.infrastructure.persistence.s3_adapter import (
    create_checkpoint,
    set_checkpoint_status,
)
from services.snipers.internals.checkpoints import save_checkpoint_events
from services.snipers.internals.evaluation import check_success, determine_failure_cause
from services.snipers.internals.events import build_complete_event, make_event
from services.snipers.internals.adaptation import run_adaptation
from services.snipers.internals.phase_runners import run_phase1, run_phase2, run_phase3

logger = logging.getLogger(__name__)


class LoopState:
    """Mutable state for the attack loop."""

    def __init__(self, converters: list[str], framings: list[str]) -> None:
        self.converters = converters
        self.framings = framings
        self.custom_framing: dict | None = None
        self.recon_custom_framing: dict | None = None
        self.payload_guidance: str | None = None
        self.adaptation_reasoning: str = ""
        self.chain_context = None
        self.tried_framings: list[str] = []
        self.tried_converters: list[list[str]] = []
        self.iteration_history: list[dict[str, Any]] = []
        self.best_score: float = 0.0
        self.best_iteration: int = 0
        self.phase1_result = None
        self.phase2_result = None
        self.phase3_result = None


async def create_initial_checkpoint(
    campaign_id: str, scan_id: str, target_url: str,
    max_iterations: int, payload_count: int,
    success_scorers: list[str], success_threshold: float,
) -> None:
    """Create the initial S3 checkpoint for a new attack run."""
    try:
        await create_checkpoint(
            campaign_id=campaign_id, scan_id=scan_id, target_url=target_url,
            config=CheckpointConfig(
                max_iterations=max_iterations, payload_count=payload_count,
                success_scorers=success_scorers, success_threshold=success_threshold,
            ),
        )
    except Exception as e:
        logger.warning(f"Failed to create initial checkpoint: {e}")


async def run_loop(
    campaign_id: str, target_url: str, scan_id: str,
    max_iterations: int, payload_count: int,
    success_scorers: list[str], success_threshold: float,
    enable_checkpoints: bool, state: LoopState,
) -> AsyncGenerator[dict[str, Any], None]:
    """Execute the main while-loop: Phase 1->2->3, evaluate, adapt."""
    iteration = 0
    is_successful = False

    while iteration < max_iterations and not is_successful:
        iter_num = iteration + 1
        yield make_event("iteration_start", f"Iteration {iter_num} started",
                         iteration=iter_num,
                         data={"iteration": iter_num, "max_iterations": max_iterations})

        if not await _run_phases(campaign_id, target_url, payload_count, iter_num, state):
            break

        is_successful, scorer_confidences = check_success(
            state.phase3_result, success_scorers, success_threshold,
        )
        state.iteration_history.append({
            "iteration": iter_num, "score": state.phase3_result.total_score,
            "is_successful": is_successful, "framing": state.framings,
            "converters": state.converters, "scorer_confidences": scorer_confidences,
        })
        yield make_event(
            "iteration_complete",
            f"Iteration {iter_num}: {'SUCCESS' if is_successful else 'blocked'}",
            iteration=iter_num,
            data={"iteration": iter_num, "is_successful": is_successful,
                  "total_score": state.phase3_result.total_score,
                  "best_score": state.best_score, "best_iteration": state.best_iteration},
        )

        if enable_checkpoints:
            async for event in save_checkpoint_events(
                campaign_id, scan_id, iteration, state.phase2_result,
                state.phase3_result, is_successful, state.best_score,
                state.best_iteration, state.framings, state.converters,
                state.tried_framings, state.tried_converters,
                state.adaptation_reasoning, scorer_confidences,
            ):
                yield event

        if is_pause_requested(scan_id):
            async for event in _handle_pause(
                campaign_id, scan_id, enable_checkpoints,
                iter_num, state.best_score, state.best_iteration,
            ):
                yield event
            return

        iteration += 1
        if not is_successful and iteration < max_iterations:
            async for event in _adapt_strategy(state):
                yield event

    yield build_complete_event(
        campaign_id, target_url, is_successful, iteration,
        state.best_score, state.best_iteration, state.iteration_history,
        state.adaptation_reasoning, state.phase1_result, state.phase2_result,
        state.phase3_result,
    )
