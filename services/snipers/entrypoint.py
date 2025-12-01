"""
HTTP entrypoint for Snipers exploitation service.

Purpose: Chain the three-phase attack flow for automated exploitation
Role: Orchestrates Phase 1 → Phase 2 → Phase 3 execution
Dependencies: PayloadArticulation, Conversion, AttackExecution

Three execution modes:
1. Single-shot: execute_full_attack() - One iteration through all phases
2. Streaming: execute_full_attack_streaming() - SSE events for real-time monitoring
3. Adaptive: execute_adaptive_attack() - LangGraph loop with auto-adaptation

Three-Phase Attack Flow:
1. Phase 1 (Payload Articulation) - Load intel, select chain, generate payloads
2. Phase 2 (Conversion) - Apply converter chain transformations
3. Phase 3 (Attack Execution) - Send attacks, score responses, record learnings

Usage:
    # Single-shot attack
    from services.snipers.entrypoint import execute_full_attack

    result = await execute_full_attack(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        payload_count=3,
    )

    # Streaming attack with SSE events
    from services.snipers.entrypoint import execute_full_attack_streaming

    async for event in execute_full_attack_streaming(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        payload_count=3,
    ):
        print(event)  # SniperStreamEvent dict

    # Adaptive attack with auto-retry
    from services.snipers.entrypoint import execute_adaptive_attack

    result = await execute_adaptive_attack(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        max_iterations=5,
    )

    # Adaptive attack with custom success criteria
    result = await execute_adaptive_attack(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        max_iterations=10,
        success_scorers=["jailbreak"],  # Only succeed on jailbreak
        success_threshold=1.0,           # Require 100% confidence
    )
"""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from services.snipers.attack_phases import (
    PayloadArticulation,
    Conversion,
    AttackExecution,
)
from services.snipers.models import Phase1Result, Phase2Result, Phase3Result
from services.snipers.adaptive_attack import (
    run_adaptive_attack,
    run_adaptive_attack_streaming,
    AdaptiveAttackState,
)
from services.snipers.persistence.s3_adapter import (
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

    # Summary fields
    is_successful: bool
    overall_severity: str
    total_score: float
    payloads_generated: int
    payloads_sent: int


async def execute_full_attack(
    campaign_id: str,
    target_url: str,
    payload_count: int = 3,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    max_concurrent: int = 3,
) -> FullAttackResult:
    """
    Execute complete three-phase attack flow.

    Args:
        campaign_id: Campaign ID to load intelligence from S3
        target_url: Target URL to attack
        payload_count: Number of payloads to generate (1-6)
        framing_types: Specific framing types (None = auto-select)
        converter_names: Override converter chain (None = use Phase 1 selection)
        max_concurrent: Max concurrent attack requests

    Returns:
        FullAttackResult with all phase results and summary
    """
    start_time = time.time()

    logger.info("\n" + "=" * 70)
    logger.info("SNIPERS: FULL ATTACK EXECUTION")
    logger.info("=" * 70)
    logger.info(f"Campaign: {campaign_id}")
    logger.info(f"Target: {target_url}")
    logger.info(f"Payloads: {payload_count}")
    logger.info("=" * 70 + "\n")

    # Phase 1: Payload Articulation
    phase1 = PayloadArticulation()
    result1 = await phase1.execute(
        campaign_id=campaign_id,
        payload_count=payload_count,
        framing_types=framing_types,
    )

    # Phase 2: Conversion
    phase2 = Conversion()
    result2 = await phase2.execute(
        payloads=result1.articulated_payloads,
        chain=result1.selected_chain if not converter_names else None,
        converter_names=converter_names,
    )

    # Phase 3: Attack Execution
    phase3 = AttackExecution(target_url=target_url)
    result3 = await phase3.execute(
        campaign_id=campaign_id,
        payloads=result2.payloads,
        chain=result1.selected_chain,
        max_concurrent=max_concurrent,
    )

    execution_time = time.time() - start_time

    # Build complete result
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

    # Persist to S3 and update campaign stage
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

    logger.info("\n" + "=" * 70)
    logger.info("ATTACK COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Success: {full_result.is_successful}")
    logger.info(f"Severity: {full_result.overall_severity}")
    logger.info(f"Score: {full_result.total_score:.2f}")
    logger.info(f"Scan ID: {scan_id}")
    logger.info("=" * 70 + "\n")

    return full_result


async def execute_full_attack_streaming(
    campaign_id: str,
    target_url: str,
    payload_count: int = 3,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    max_concurrent: int = 3,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Execute complete three-phase attack with SSE streaming events.

    Yields SniperStreamEvent dicts for real-time monitoring of each phase.

    Args:
        campaign_id: Campaign ID to load intelligence from S3
        target_url: Target URL to attack
        payload_count: Number of payloads to generate (1-6)
        framing_types: Specific framing types (None = auto-select)
        converter_names: Override converter chain (None = use Phase 1 selection)
        max_concurrent: Max concurrent attack requests

    Yields:
        Dict representation of SniperStreamEvent for SSE streaming
    """
    start_time = time.time()
    scan_id = f"{campaign_id}-{uuid.uuid4().hex[:8]}"

    def make_event(
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

    # Attack started
    yield make_event(
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
        # ========== Phase 1: Payload Articulation ==========
        yield make_event(
            "phase1_start",
            "Phase 1: Loading intelligence and generating payloads",
            phase="phase1",
            progress=0.0,
        )

        phase1 = PayloadArticulation()

        yield make_event(
            "phase1_progress",
            "Loading campaign intelligence from S3",
            phase="phase1",
            progress=0.2,
        )

        result1 = await phase1.execute(
            campaign_id=campaign_id,
            payload_count=payload_count,
            framing_types=framing_types,
        )

        # Emit each generated payload
        for i, payload in enumerate(result1.articulated_payloads):
            yield make_event(
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

        yield make_event(
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

        # ========== Phase 2: Conversion ==========
        yield make_event(
            "phase2_start",
            "Phase 2: Applying converter chain transformations",
            phase="phase2",
            progress=0.0,
        )

        phase2 = Conversion()
        result2 = await phase2.execute(
            payloads=result1.articulated_payloads,
            chain=result1.selected_chain if not converter_names else None,
            converter_names=converter_names,
        )

        # Emit each converted payload
        for i, converted in enumerate(result2.payloads):
            yield make_event(
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

        yield make_event(
            "phase2_complete",
            f"Phase 2 complete: {result2.success_count} payloads converted",
            phase="phase2",
            data={
                "chain_id": result2.chain_id,
                "converter_names": result2.converter_names,
                "success_count": result2.success_count,
                "error_count": result2.error_count,
            },
            progress=1.0,
        )

        # ========== Phase 3: Attack Execution ==========
        yield make_event(
            "phase3_start",
            f"Phase 3: Executing attacks against {target_url}",
            phase="phase3",
            data={"target_url": target_url, "payloads_count": len(result2.payloads)},
            progress=0.0,
        )

        phase3 = AttackExecution(target_url=target_url)

        # Execute attacks - this happens inside execute(), so we stream progress after
        result3 = await phase3.execute(
            campaign_id=campaign_id,
            payloads=result2.payloads,
            chain=result1.selected_chain,
            max_concurrent=max_concurrent,
        )

        # Emit each attack response
        total_attacks = len(result3.attack_responses)
        for i, resp in enumerate(result3.attack_responses):
            yield make_event(
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

            yield make_event(
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

        # Emit scoring results
        for scorer_name, score_result in result3.composite_score.scorer_results.items():
            yield make_event(
                "score_calculated",
                f"Scorer '{scorer_name}': {score_result.severity.value}",
                phase="phase3",
                data={
                    "scorer_name": scorer_name,
                    "severity": score_result.severity.value,
                    "confidence": score_result.confidence,
                    "reasoning": getattr(score_result, 'reasoning', None),
                },
            )

        yield make_event(
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

        # ========== Persist and Complete ==========
        execution_time = time.time() - start_time

        # Build full result for persistence
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

        # Persist to S3
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

        yield make_event(
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
                "execution_time_ms": int(execution_time * 1000),
                # Include full result data for frontend
                "phase1": {
                    "framing_type": result1.framing_type,
                    "framing_types_used": result1.framing_types_used,
                    "payloads": result1.articulated_payloads,
                },
                "phase2": {
                    "converter_names": result2.converter_names,
                    "payloads": [
                        {"original": p.original, "converted": p.converted, "converters_applied": p.converters_applied}
                        for p in result2.payloads
                    ],
                },
                "phase3": {
                    "attack_responses": [
                        {
                            "payload_index": r.payload_index,
                            "payload": r.payload,
                            "response": r.response,
                            "status_code": r.status_code,
                            "latency_ms": r.latency_ms,
                            "error": r.error,
                        }
                        for r in result3.attack_responses
                    ],
                    "composite_score": {
                        "overall_severity": result3.composite_score.overall_severity.value,
                        "total_score": result3.composite_score.total_score,
                        "is_successful": result3.composite_score.is_successful,
                        "scorer_results": {
                            name: {
                                "severity": sr.severity.value,
                                "confidence": sr.confidence,
                                "reasoning": getattr(sr, 'reasoning', None),
                            }
                            for name, sr in result3.composite_score.scorer_results.items()
                        },
                    },
                },
            },
        )

    except Exception as e:
        logger.exception(f"Streaming attack failed: {e}")
        yield make_event(
            "error",
            f"Attack failed: {str(e)}",
            phase="phase1" if result1 is None else ("phase2" if result2 is None else "phase3"),
            data={"error": str(e), "error_type": type(e).__name__},
        )
        raise


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
    """
    Execute adaptive attack with SSE streaming events.

    Yields streaming events for real-time monitoring of each iteration.

    Args:
        campaign_id: Campaign ID to load intelligence from S3
        target_url: Target URL to attack
        max_iterations: Maximum adaptation iterations (default 5)
        payload_count: Initial number of payloads (1-6)
        framing_types: Initial framing types (None = auto-select)
        converter_names: Initial converter chain (None = auto-select)
        success_scorers: Scorers that must succeed (e.g., ["jailbreak"])
        success_threshold: Minimum confidence for success (0.0-1.0)

    Yields:
        Dict representation of streaming events for SSE
    """
    async for event in run_adaptive_attack_streaming(
        campaign_id=campaign_id,
        target_url=target_url,
        max_iterations=max_iterations,
        payload_count=payload_count,
        framing_types=framing_types,
        converter_names=converter_names,
        success_scorers=success_scorers,
        success_threshold=success_threshold,
    ):
        yield event


async def execute_adaptive_attack(
    campaign_id: str,
    target_url: str,
    max_iterations: int = 5,
    payload_count: int = 2,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
) -> AdaptiveAttackState:
    """
    Execute adaptive attack with automatic parameter adjustment.

    Uses LangGraph state machine to iterate through attack phases,
    automatically adapting framing/converters based on failure analysis.

    Args:
        campaign_id: Campaign ID to load intelligence from S3
        target_url: Target URL to attack
        max_iterations: Maximum adaptation iterations (default 5)
        payload_count: Initial number of payloads (1-6)
        framing_types: Initial framing types (None = auto-select)
        converter_names: Initial converter chain (None = auto-select)
        success_scorers: Scorers that must succeed (e.g., ["jailbreak"])
            Options: jailbreak, prompt_leak, data_leak, tool_abuse, pii_exposure
        success_threshold: Minimum confidence for success (0.0-1.0)

    Returns:
        AdaptiveAttackState with final results and iteration history
    """
    start_time = time.time()

    result = await run_adaptive_attack(
        campaign_id=campaign_id,
        target_url=target_url,
        max_iterations=max_iterations,
        payload_count=payload_count,
        framing_types=framing_types,
        converter_names=converter_names,
        success_scorers=success_scorers,
        success_threshold=success_threshold,
    )

    execution_time = time.time() - start_time

    # Persist to S3 and update campaign stage
    scan_id = f"{campaign_id}-adaptive-{uuid.uuid4().hex[:8]}"
    state_dict = _adaptive_result_to_state_dict(result)
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
    logger.info(f"Persisted adaptive attack result: {scan_id}")

    return result


def _adaptive_result_to_state_dict(state: AdaptiveAttackState) -> dict:
    """Convert AdaptiveAttackState to state dict for format_exploit_result."""
    phase3 = state.get("phase3_result")
    phase1 = state.get("phase1_result")

    # Build attack results from phase3 if available
    attack_results = []
    if phase3:
        for resp in phase3.attack_responses:
            attack_results.append({
                "success": resp.error is None and state.get("is_successful", False),
                "payload": resp.payload,
                "response": resp.response,
            })

    # Get converter selection from chain selection result or phase1
    converter_selection = None
    chain_selection = state.get("chain_selection_result")
    if chain_selection:
        converter_selection = {
            "selected_converters": chain_selection.selected_chain or [],
        }
    elif phase1 and phase1.selected_chain:
        converter_selection = {
            "selected_converters": phase1.selected_chain.converter_names,
        }

    return {
        "probe_name": phase1.framing_type if phase1 else "adaptive",
        "pattern_analysis": phase1.context_summary if phase1 else {},
        "converter_selection": converter_selection,
        "attack_results": attack_results,
        "recon_intelligence": phase1.context_summary.get("recon_used") if phase1 else None,
        # Adaptive-specific fields for logging
        "iteration_count": state.get("iteration", 0) + 1,
        "best_score": state.get("best_score", 0.0),
        "best_iteration": state.get("best_iteration", 0),
        "adaptation_reasoning": state.get("adaptation_reasoning", ""),
    }


