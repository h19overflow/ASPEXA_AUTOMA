"""
HTTP entrypoint for Snipers exploitation service.

Purpose: Chain the three-phase attack flow for automated exploitation
Role: Orchestrates Phase 1 → Phase 2 → Phase 3 execution via SSE streams
Dependencies: PayloadArticulation, Conversion, AttackExecution

Two execution modes:
1. Streaming One-Shot: execute_full_attack_streaming() - SSE events for real-time monitoring
2. Adaptive: execute_adaptive_attack_streaming() - LangGraph loop with auto-adaptation

Three-Phase Attack Flow:
1. Phase 1 (Payload Articulation) - Load intel, select chain, generate payloads
2. Phase 2 (Conversion) - Apply converter chain transformations
3. Phase 3 (Attack Execution) - Send attacks, score responses, record learnings

Usage:
    # Streaming attack with SSE events
    from services.snipers.entrypoint import execute_full_attack_streaming

    async for event in execute_full_attack_streaming(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        payload_count=3,
    ):
        print(event)  # SniperStreamEvent dict

    # Adaptive attack with auto-retry
    from services.snipers.entrypoint import execute_adaptive_attack_streaming

    async for event in execute_adaptive_attack_streaming(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        max_iterations=5,
    ):
        print(event)

    # Adaptive attack with custom success criteria
    async for event in execute_adaptive_attack_streaming(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        max_iterations=10,
        success_scorers=["jailbreak"],  # Only succeed on jailbreak
        success_threshold=1.0,           # Require 100% confidence
    ):
        print(event)
"""

import logging
import time
import uuid
from typing import Any, AsyncGenerator

from services.snipers.core.phases import (
    PayloadArticulation,
    Conversion,
    AttackExecution,
)
from services.snipers.adaptive_loop import run_adaptive_attack_streaming
from services.snipers.internals.entrypoint_helpers import (
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

    async for event in run_adaptive_attack_streaming(
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



