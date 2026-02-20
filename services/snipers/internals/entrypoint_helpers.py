"""
Helper functions and logic for Snipers entrypoint.

Extracts complex state dict mapping, event generation, and S3 persistence handling
to keep the main orchestration API concise.
"""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from services.snipers.models import Phase1Result, Phase2Result, Phase3Result
from services.snipers.infrastructure.persistence.s3_adapter import (
    persist_exploit_result,
    format_exploit_result,
)

logger = logging.getLogger(__name__)


@dataclass
class FullAttackResult:
    """Complete result from all three phases."""
    campaign_id: str
    target_url: str
    phase1: Phase1Result
    phase2: Phase2Result
    phase3: Phase3Result

    is_successful: bool
    overall_severity: str
    total_score: float
    payloads_generated: int
    payloads_sent: int


def make_stream_event(
    event_type: str,
    message: str,
    phase: str | None = None,
    data: dict | None = None,
    progress: float | None = None,
) -> dict[str, Any]:
    """Create a stream event dict."""
    return {
        "type": event_type,
        "phase": phase,
        "message": message,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "progress": progress,
    }


def _full_result_to_state_dict(result: FullAttackResult) -> dict:
    """Convert FullAttackResult to state dict for format_exploit_result."""
    return {
        "probe_name": result.phase1.framing_type,
        "pattern_analysis": result.phase1.context_summary,
        "converter_selection": {
            "selected_converters": result.phase2.converter_names,
        } if result.phase2 else None,
        "attack_results": [
            {
                "success": resp.error is None and result.is_successful,
                "payload": resp.payload,
                "response": resp.response,
            }
            for resp in result.phase3.attack_responses
        ],
        "recon_intelligence": result.phase1.context_summary.get("recon_used"),
    }




async def persist_full_attack_result(
    full_result: FullAttackResult,
    campaign_id: str,
    target_url: str,
    start_time: float,
    scan_id: str | None = None,
) -> str:
    """Persist full attack result to S3 and return scan_id."""
    execution_time = time.time() - start_time
    if not scan_id:
        scan_id = f"{campaign_id}-{uuid.uuid4().hex[:8]}"
    
    state_dict = _full_result_to_state_dict(full_result)
    exploit_result = format_exploit_result(
        state=state_dict,
        audit_id=campaign_id,
        target_url=target_url,
        execution_time=execution_time,
    )
    
    await persist_exploit_result(
        campaign_id=campaign_id,
        scan_id=scan_id,
        exploit_result=exploit_result,
        target_url=target_url,
    )
    logger.info(f"Persisted exploit result: {scan_id}")
    return scan_id




async def persist_adaptive_streaming_result(
    final_state: dict[str, Any],
    scan_id: str,
    campaign_id: str,
    target_url: str,
    start_time: float,
):
    """Persist adaptive streaming attack result to S3."""
    execution_time = time.time() - start_time

    phase1_data = final_state.get("phase1", {})
    phase3_data = final_state.get("phase3", {})

    state_dict = {
        "probe_name": phase1_data.get("framing_type", "adaptive") if phase1_data else "adaptive",
        "pattern_analysis": {},
        "converter_selection": {
            "selected_converters": final_state.get("phase2", {}).get("converter_names", []) if final_state.get("phase2") else [],
        },
        "attack_results": [
            {
                "success": final_state.get("is_successful", False),
                "payload": r.get("payload", ""),
                "response": r.get("response", ""),
            }
            for r in (phase3_data.get("attack_responses", []) if phase3_data else [])
        ],
        "recon_intelligence": None,
        "iteration_count": final_state.get("total_iterations", 1),
        "best_score": final_state.get("best_score", 0.0),
        "best_iteration": final_state.get("best_iteration", 0),
        "adaptation_reasoning": final_state.get("adaptation_reasoning", ""),
    }

    exploit_result = format_exploit_result(
        state=state_dict,
        audit_id=campaign_id,
        target_url=target_url,
        execution_time=execution_time,
    )

    await persist_exploit_result(
        campaign_id=campaign_id,
        scan_id=scan_id,
        exploit_result=exploit_result,
        target_url=target_url,
    )
    logger.info(f"Persisted adaptive streaming attack result: {scan_id}")


async def stream_phase1_events(result1: Phase1Result) -> Any:
    """Stream payload generation events for Phase 1."""
    for i, payload in enumerate(result1.articulated_payloads):
        yield make_stream_event(
            "payload_generated",
            f"Generated payload {i + 1}/{len(result1.articulated_payloads)}",
            phase="phase1",
            data={
                "index": i,
                "payload": payload[:200] + "..." if len(payload) > 200 else payload,
                "framing_type": result1.framing_types_used[i] if i < len(result1.framing_types_used) else None,
            },
            progress=0.5 + (0.5 * (i + 1) / max(len(result1.articulated_payloads), 1)),
        )

    yield make_stream_event(
        "phase1_complete",
        f"Phase 1 complete: {len(result1.articulated_payloads)} payloads generated",
        phase="phase1",
        data={
            "payloads_count": len(result1.articulated_payloads),
            "framing_type": result1.framing_type,
            "framing_types_used": result1.framing_types_used,
            "selected_chain": result1.selected_chain.converter_names if result1.selected_chain else None,
        },
        progress=1.0,
    )


async def stream_phase2_events(result2: Phase2Result) -> Any:
    """Stream converter application events for Phase 2."""
    for i, converted in enumerate(result2.payloads):
        yield make_stream_event(
            "payload_converted",
            f"Converted payload {i + 1}/{len(result2.payloads)}",
            phase="phase2",
            data={
                "index": i,
                "original": converted.original[:100] + "..." if len(converted.original) > 100 else converted.original,
                "converted": converted.converted[:100] + "..." if len(converted.converted) > 100 else converted.converted,
                "converters_applied": converted.converters_applied,
                "has_errors": bool(converted.errors),
            },
            progress=(i + 1) / max(len(result2.payloads), 1),
        )

    yield make_stream_event(
        "phase2_complete",
        f"Phase 2 complete: {result2.success_count} payloads converted",
        phase="phase2",
        data={
            "chain_id": result2.chain_id,
            "converter_names": result2.converter_names,
            "success_count": result2.success_count,
        },
        progress=1.0,
    )


async def stream_phase3_events(result3: Phase3Result) -> Any:
    """Stream attack execution and scoring events for Phase 3."""
    total_attacks = len(result3.attack_responses)
    for i, resp in enumerate(result3.attack_responses):
        yield make_stream_event(
            "attack_sent",
            f"Attack {i + 1}/{total_attacks} sent",
            phase="phase3",
            data={
                "index": i,
                "payload_index": resp.payload_index,
                "payload": resp.payload[:100] + "..." if len(resp.payload) > 100 else resp.payload,
            },
            progress=(i + 0.5) / max(total_attacks, 1),
        )
        yield make_stream_event(
            "response_received",
            f"Response {i + 1}/{total_attacks} received",
            phase="phase3",
            data={
                "index": i,
                "status_code": resp.status_code,
                "latency_ms": resp.latency_ms,
                "response": resp.response,
                "error": resp.error,
            },
            progress=(i + 1) / max(total_attacks, 1),
        )

    for scorer_name, score_result in result3.composite_score.scorer_results.items():
        severity_val = score_result.severity.value
        if severity_val == "none":
            message = f"Scorer '{scorer_name}': Secure (No finding)"
        else:
            message = f"Scorer '{scorer_name}' detected {severity_val.upper()} risk"
            
        yield make_stream_event(
            "score_calculated",
            message,
            phase="phase3",
            data={
                "scorer_name": scorer_name,
                "severity": severity_val,
                "confidence": score_result.confidence,
            },
        )

    yield make_stream_event(
        "phase3_complete",
        f"Phase 3 complete: {'BREACH DETECTED' if result3.is_successful else 'Target secure'}",
        phase="phase3",
        data={
            "is_successful": result3.is_successful,
            "overall_severity": result3.overall_severity,
            "total_score": result3.total_score,
        },
        progress=1.0,
    )
