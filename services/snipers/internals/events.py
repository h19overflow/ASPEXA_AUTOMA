"""SSE event builders for the adaptive attack loop."""

from datetime import datetime, timezone
from typing import Any

from services.snipers.models import Phase1Result, Phase3Result


def make_event(
    event_type: str,
    message: str,
    phase: str | None = None,
    iteration: int | None = None,
    data: dict | None = None,
    progress: float | None = None,
) -> dict[str, Any]:
    """Create a stream event dict for SSE."""
    return {
        "type": event_type,
        "phase": phase,
        "iteration": iteration,
        "message": message,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "progress": progress,
    }


def build_complete_event(
    campaign_id: str,
    target_url: str,
    is_successful: bool,
    iteration: int,
    best_score: float,
    best_iteration: int,
    iteration_history: list[dict[str, Any]],
    adaptation_reasoning: str,
    phase1_result: Phase1Result | None,
    phase2_result: Any,
    phase3_result: Phase3Result | None,
) -> dict[str, Any]:
    """Build the final attack_complete SSE event."""
    phase1_data = _build_phase1_data(phase1_result)
    phase2_data = _build_phase2_data(phase2_result)
    phase3_data = _build_phase3_data(phase3_result)

    return make_event(
        "attack_complete",
        f"Adaptive attack complete: {'SUCCESS' if is_successful else 'Target secure'}",
        data={
            "campaign_id": campaign_id,
            "target_url": target_url,
            "is_successful": is_successful,
            "total_iterations": iteration,
            "best_score": best_score,
            "best_iteration": best_iteration,
            "overall_severity": (
                phase3_result.overall_severity if phase3_result else "none"
            ),
            "total_score": phase3_result.total_score if phase3_result else 0.0,
            "iteration_history": iteration_history,
            "adaptation_reasoning": adaptation_reasoning,
            "phase1": phase1_data,
            "phase2": phase2_data,
            "phase3": phase3_data,
        },
    )


def _build_phase1_data(phase1_result: Phase1Result | None) -> dict | None:
    if not phase1_result:
        return None
    return {
        "framing_type": phase1_result.framing_type,
        "framing_types_used": phase1_result.framing_types_used,
        "payloads": phase1_result.articulated_payloads,
    }


def _build_phase2_data(phase2_result: Any) -> dict | None:
    if not phase2_result:
        return None
    return {
        "converter_names": phase2_result.converter_names,
        "payloads": [
            {"original": p.original, "converted": p.converted,
             "converters_applied": p.converters_applied}
            for p in phase2_result.payloads
        ],
    }


def _build_phase3_data(phase3_result: Phase3Result | None) -> dict | None:
    if not phase3_result:
        return None
    return {
        "attack_responses": [
            {"payload_index": r.payload_index, "payload": r.payload,
             "response": r.response, "status_code": r.status_code,
             "latency_ms": r.latency_ms, "error": r.error}
            for r in phase3_result.attack_responses
        ],
        "composite_score": {
            "overall_severity": phase3_result.composite_score.overall_severity.value,
            "total_score": phase3_result.composite_score.total_score,
            "is_successful": phase3_result.composite_score.is_successful,
            "scorer_results": {
                name: {"severity": sr.severity.value,
                       "confidence": sr.confidence,
                       "reasoning": getattr(sr, "reasoning", None)}
                for name, sr in phase3_result.composite_score.scorer_results.items()
            },
        },
    }
