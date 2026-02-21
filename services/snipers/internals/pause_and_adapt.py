"""Pause handling and strategy adaptation for the attack loop."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator

from libs.persistence import CheckpointStatus
from services.snipers.core.components.pause_signal import clear_pause
from services.snipers.infrastructure.persistence.s3_adapter import set_checkpoint_status
from services.snipers.internals.adaptation import run_adaptation
from services.snipers.internals.evaluation import determine_failure_cause
from services.snipers.internals.events import make_event

if TYPE_CHECKING:
    from services.snipers.internals.state import LoopState

logger = logging.getLogger(__name__)


async def adapt_strategy(
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
            discovered_parameters=state.discovered_parameters or None,
        )
        state.converters = adaptation["converter_names"] or state.converters
        state.framings = adaptation["framing_types"] or state.framings
        state.custom_framing = adaptation["custom_framing"]
        state.recon_custom_framing = adaptation["recon_custom_framing"]
        state.payload_guidance = adaptation["payload_guidance"]
        state.adaptation_reasoning = adaptation["adaptation_reasoning"] or ""
        if adaptation.get("discovered_parameters"):
            state.discovered_parameters.update(adaptation["discovered_parameters"])
        if adaptation.get("avoid_terms"):
            state.avoid_terms = adaptation["avoid_terms"]
        if adaptation.get("emphasize_terms"):
            state.emphasize_terms = adaptation["emphasize_terms"]

        yield make_event(
            "adaptation", "Adapting strategy for next iteration",
            data={"adaptation_reasoning": state.adaptation_reasoning[:500],
                  "next_framing": state.framings,
                  "next_converters": state.converters},
        )
    except Exception as e:
        logger.exception(f"Adaptation failed, keeping current params: {e}")
        yield make_event(
            "adaptation_error", f"Adaptation failed: {e}, retrying with same strategy",
            data={"error": str(e), "error_type": type(e).__name__},
        )


async def handle_pause(
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
