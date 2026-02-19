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
from services.snipers.internals.constants import FRAMING_TYPES
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

        # Phase 1
        yield make_event("phase1_start", "Phase 1: Payload Articulation",
                         phase="phase1", iteration=iter_num, progress=0.0)
        try:
            state.phase1_result, events = await run_phase1(
                campaign_id, payload_count, state.framings, state.custom_framing,
                state.recon_custom_framing, state.payload_guidance,
                state.chain_context, iter_num, state.tried_framings,
            )
            for e in events:
                yield e
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            yield make_event("error", f"Phase 1 failed: {e}", phase="phase1",
                             iteration=iter_num, data={"error": str(e), "node": "articulate"})
            break

        # Phase 2
        yield make_event("phase2_start", "Phase 2: Payload Conversion",
                         phase="phase2", iteration=iter_num, progress=0.0)
        try:
            state.phase2_result, events = await run_phase2(
                state.phase1_result.articulated_payloads, state.converters,
                iter_num, state.tried_converters,
            )
            for e in events:
                yield e
        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            yield make_event("error", f"Phase 2 failed: {e}", phase="phase2",
                             iteration=iter_num, data={"error": str(e), "node": "convert"})
            break

        # Phase 3
        yield make_event("phase3_start", f"Phase 3: Attacking {target_url}",
                         phase="phase3", iteration=iter_num,
                         data={"target_url": target_url}, progress=0.0)
        try:
            state.phase3_result, events = await run_phase3(
                campaign_id, target_url, state.phase2_result.payloads, iter_num,
            )
            if state.phase3_result.total_score > state.best_score:
                state.best_score = state.phase3_result.total_score
                state.best_iteration = iter_num
            for e in events:
                yield e
        except Exception as e:
            logger.error(f"Phase 3 failed: {e}")
            yield make_event("error", f"Phase 3 failed: {e}", phase="phase3",
                             iteration=iter_num, data={"error": str(e), "node": "execute"})
            break

        # Evaluate
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


async def _adapt_strategy(
    state: LoopState,
) -> AsyncGenerator[dict[str, Any], None]:
    """Run LLM adaptation and update state with new strategy."""
    target_responses = [
        r.response for r in state.phase3_result.attack_responses if r.response
    ]
    failure_cause = determine_failure_cause(state.phase3_result)
    try:
        adaptation = await run_adaptation(
            phase3_result=state.phase3_result,
            failure_cause=failure_cause,
            target_responses=target_responses,
            iteration_history=state.iteration_history,
            tried_converters=state.tried_converters,
            tried_framings=state.tried_framings,
            phase1_result=state.phase1_result,
        )
        state.converters = adaptation["converter_names"] or state.converters
        state.framings = adaptation["framing_types"] or state.framings
        state.custom_framing = adaptation["custom_framing"]
        state.recon_custom_framing = adaptation["recon_custom_framing"]
        state.payload_guidance = adaptation["payload_guidance"]
        state.adaptation_reasoning = adaptation["adaptation_reasoning"] or ""

        yield make_event(
            "adaptation", "Adapting strategy for next iteration",
            data={"adaptation_reasoning": state.adaptation_reasoning[:500],
                  "next_framing": state.framings,
                  "next_converters": state.converters},
        )
    except Exception as e:
        logger.warning(f"Adaptation failed: {e}, keeping current params")


async def _handle_pause(
    campaign_id: str, scan_id: str, enable_checkpoints: bool,
    iteration: int, best_score: float, best_iteration: int,
) -> AsyncGenerator[dict[str, Any], None]:
    """Handle pause request: set checkpoint status and yield pause event."""
    if enable_checkpoints:
        try:
            await set_checkpoint_status(campaign_id, scan_id, CheckpointStatus.PAUSED)
        except Exception as e:
            logger.warning(f"Failed to set paused status: {e}")
    yield make_event(
        "attack_paused", f"Attack paused after iteration {iteration}",
        iteration=iteration,
        data={"scan_id": scan_id, "best_score": best_score,
              "best_iteration": best_iteration, "can_resume": True},
    )
    clear_pause(scan_id)
