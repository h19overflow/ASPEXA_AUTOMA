"""SSE event builders for each attack phase."""

from typing import Any

from services.snipers.core.loop.events.builders import make_event
from services.snipers.models import Phase1Result, Phase3Result


def build_phase1_events(
    result: Phase1Result, iteration: int,
) -> list[dict[str, Any]]:
    """Build SSE events for Phase 1 results."""
    events = []
    for i, p in enumerate(result.articulated_payloads):
        events.append(make_event(
            "payload_generated", f"Generated payload {i + 1}",
            phase="phase1", iteration=iteration,
            data={"index": i, "payload": p,
                  "framing_type": result.framing_types_used[i]
                  if i < len(result.framing_types_used) else None},
            progress=(i + 1) / len(result.articulated_payloads),
        ))
    events.append(make_event(
        "phase1_complete",
        f"Phase 1 complete: {len(result.articulated_payloads)} payloads",
        phase="phase1", iteration=iteration,
        data={"payloads_count": len(result.articulated_payloads),
              "framing_type": result.framing_type,
              "framing_types_used": result.framing_types_used},
        progress=1.0,
    ))
    return events


def build_phase2_events(result: Any, iteration: int) -> list[dict[str, Any]]:
    """Build SSE events for Phase 2 results."""
    events = []
    for i, c in enumerate(result.payloads):
        events.append(make_event(
            "payload_converted", f"Converted payload {i + 1}",
            phase="phase2", iteration=iteration,
            data={"index": i, "original": c.original,
                  "converted": c.converted,
                  "converters_applied": c.converters_applied},
            progress=(i + 1) / len(result.payloads),
        ))
    events.append(make_event(
        "phase2_complete",
        f"Phase 2 complete: {result.success_count} converted",
        phase="phase2", iteration=iteration,
        data={"converter_names": result.converter_names,
              "success_count": result.success_count,
              "error_count": result.error_count},
        progress=1.0,
    ))
    return events


def build_phase3_events(
    result: Phase3Result, target_url: str, iteration: int,
) -> list[dict[str, Any]]:
    """Build SSE events for Phase 3 results."""
    events = []
    total = len(result.attack_responses)
    for i, resp in enumerate(result.attack_responses):
        events.append(make_event(
            "attack_sent", f"Attack {i + 1}/{total} sent",
            phase="phase3", iteration=iteration,
            data={"index": i, "payload_index": resp.payload_index,
                  "payload": resp.payload},
            progress=(i + 0.5) / total,
        ))
        events.append(make_event(
            "response_received", f"Response {i + 1}/{total} received",
            phase="phase3", iteration=iteration,
            data={"index": i, "status_code": resp.status_code,
                  "latency_ms": resp.latency_ms,
                  "response": resp.response, "error": resp.error},
            progress=(i + 1) / total,
        ))
    for name, sr in result.composite_score.scorer_results.items():
        events.append(make_event(
            "score_calculated", f"Scorer '{name}': {sr.severity.value}",
            phase="phase3", iteration=iteration,
            data={"scorer_name": name, "severity": sr.severity.value,
                  "confidence": sr.confidence,
                  "reasoning": getattr(sr, "reasoning", None)},
        ))
    events.append(make_event(
        "phase3_complete",
        f"Phase 3 complete: {'BREACH' if result.is_successful else 'Blocked'}",
        phase="phase3", iteration=iteration,
        data={"is_successful": result.is_successful,
              "overall_severity": result.overall_severity,
              "total_score": result.total_score},
        progress=1.0,
    ))
    return events
