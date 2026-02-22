"""Main while-loop: Phase 1->2->3, evaluate, checkpoint, adapt."""

import logging
from typing import Any, AsyncGenerator

from services.snipers.core.components.pause_signal import is_pause_requested
from services.snipers.core.phases.articulation.components.effectiveness_tracker import (
    EffectivenessTracker,
)
from services.snipers.core.phases.articulation.models.framing_strategy import FramingType
from services.snipers.internals.checkpoints import save_checkpoint_events
from services.snipers.internals.evaluation import check_success
from services.snipers.internals.events import build_complete_event, make_event
from services.snipers.internals.pause_and_adapt import adapt_strategy, handle_pause
from services.snipers.internals.phase_runners import run_phase1, run_phase2, run_phase3
from services.snipers.internals.state import LoopState

logger = logging.getLogger(__name__)


async def run_loop(
    campaign_id: str, target_url: str, scan_id: str,
    max_iterations: int, payload_count: int,
    success_scorers: list[str], success_threshold: float,
    enable_checkpoints: bool, state: LoopState,
) -> AsyncGenerator[dict[str, Any], None]:
    """Execute the main while-loop: Phase 1->2->3, evaluate, adapt."""
    iteration = 0
    is_successful = False

    # Single tracker instance shared across all iterations so framing selection
    # improves based on outcomes recorded within this run.
    tracker = EffectivenessTracker(campaign_id=campaign_id)
    try:
        await tracker.load_history()
    except Exception as e:
        logger.debug(f"Could not load effectiveness history: {e}")

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
                tracker=tracker,
                avoid_terms=state.avoid_terms,
                emphasize_terms=state.emphasize_terms,
            )
            for e in events:
                yield e
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}", exc_info=True)
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

        # Record outcome so FramingLibrary makes better choices next iteration
        domain = state.phase3_result.target_url
        framing_str = state.phase1_result.framing_type if state.phase1_result else "unknown"
        try:
            framing_enum = FramingType(framing_str)
        except ValueError:
            framing_enum = FramingType.QA_TESTING
        first_payload = (
            state.phase1_result.articulated_payloads[0]
            if state.phase1_result and state.phase1_result.articulated_payloads
            else ""
        )
        tracker.record_attempt(
            framing_type=framing_enum,
            format_control="",
            domain=domain,
            success=is_successful,
            score=state.phase3_result.total_score,
            payload_preview=first_payload,
        )
        try:
            await tracker.save()
        except Exception as e:
            logger.warning(f"Failed to save effectiveness history: {e}")

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
            async for event in handle_pause(
                campaign_id, scan_id, enable_checkpoints,
                iter_num, state.best_score, state.best_iteration,
            ):
                yield event
            return

        iteration += 1
        if not is_successful and iteration < max_iterations:
            async for event in adapt_strategy(state):
                yield event

    yield build_complete_event(
        campaign_id, target_url, is_successful, iteration,
        state.best_score, state.best_iteration, state.iteration_history,
        state.adaptation_reasoning, state.phase1_result, state.phase2_result,
        state.phase3_result,
    )
