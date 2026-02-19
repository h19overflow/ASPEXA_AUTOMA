"""Phase execution runners for the adaptive attack loop."""

import logging
from typing import Any

from services.snipers.core.phases import (
    AttackExecution,
    Conversion,
    PayloadArticulation,
)
from services.snipers.internals.events import make_event
from services.snipers.models import Phase1Result, Phase3Result

logger = logging.getLogger(__name__)


async def run_phase1(
    campaign_id: str,
    payload_count: int,
    current_framings: list[str],
    custom_framing: dict | None,
    recon_custom_framing: dict | None,
    payload_guidance: str | None,
    chain_context: Any,
    iteration: int,
    tried_framings: list[str],
) -> tuple[Phase1Result, list[dict[str, Any]]]:
    """Execute Phase 1 (Payload Articulation). Returns result and events."""
    phase1 = PayloadArticulation()
    result = await phase1.execute(
        campaign_id=campaign_id,
        payload_count=payload_count,
        framing_types=current_framings,
        custom_framing=custom_framing,
        recon_custom_framing=recon_custom_framing,
        payload_guidance=payload_guidance,
        chain_discovery_context=(
            chain_context.model_dump() if chain_context else None
        ),
    )
    if result.framing_type and result.framing_type not in tried_framings:
        tried_framings.append(result.framing_type)

    events = _build_phase1_events(result, iteration)
    return result, events


def _build_phase1_events(
    result: Phase1Result, iteration: int,
) -> list[dict[str, Any]]:
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


async def run_phase2(
    payloads: list[str],
    current_converters: list[str],
    iteration: int,
    tried_converters: list[list[str]],
) -> tuple[Any, list[dict[str, Any]]]:
    """Execute Phase 2 (Payload Conversion). Returns result and events."""
    phase2 = Conversion()
    result = await phase2.execute(
        payloads=payloads,
        chain=None,
        converter_names=current_converters,
    )
    if result.converter_names and result.converter_names not in tried_converters:
        tried_converters.append(result.converter_names)

    events = _build_phase2_events(result, iteration)
    return result, events


def _build_phase2_events(result: Any, iteration: int) -> list[dict[str, Any]]:
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


async def run_phase3(
    campaign_id: str,
    target_url: str,
    payloads: list,
    iteration: int,
) -> tuple[Phase3Result, list[dict[str, Any]]]:
    """Execute Phase 3 (Attack Execution). Returns result and events."""
    phase3 = AttackExecution(target_url=target_url)
    result = await phase3.execute(
        campaign_id=campaign_id,
        payloads=payloads,
        chain=None,
        max_concurrent=3,
    )

    events = _build_phase3_events(result, target_url, iteration)
    return result, events


def _build_phase3_events(
    result: Phase3Result, target_url: str, iteration: int,
) -> list[dict[str, Any]]:
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
