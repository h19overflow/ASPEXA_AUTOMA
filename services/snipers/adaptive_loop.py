"""
Adaptive Attack Loop.

Purpose: Iterative attack loop that analyzes failures and evolves strategy
Role: Orchestrates Phase 1->2->3 with LLM-powered adaptation between iterations
Dependencies: Phase implementations, LLM agents, S3 persistence

Simple while loop replacing the former LangGraph state machine.
Same functionality, fewer abstractions.
"""

import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from libs.monitoring import CallbackHandler
from libs.persistence import (
    CheckpointConfig,
    CheckpointIteration,
    CheckpointResumeState,
    CheckpointStatus,
)

from services.snipers.core.phases import (
    AttackExecution,
    Conversion,
    PayloadArticulation,
)
from services.snipers.core.agents.chain_discovery_agent import (
    ChainDiscoveryAgent,
)
from services.snipers.core.agents.failure_analyzer_agent import (
    FailureAnalyzerAgent,
)
from services.snipers.core.agents.strategy_generator import (
    StrategyGenerator,
)
from services.snipers.core.components.pause_signal import (
    clear_pause,
    is_pause_requested,
)
from services.snipers.infrastructure.persistence.s3_adapter import (
    create_checkpoint,
    load_checkpoint as load_checkpoint_from_s3,
    set_checkpoint_status,
    update_checkpoint,
)
from services.snipers.models import Phase1Result, Phase3Result

logger = logging.getLogger(__name__)

# Available framing types for initial selection
FRAMING_TYPES = [
    "qa_testing",
    "compliance_audit",
    "documentation",
    "debugging",
    "educational",
    "research",
]

# Available scorer types
ALL_SCORERS = ["jailbreak", "prompt_leak", "data_leak", "tool_abuse", "pii_exposure"]


def _make_event(
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


def check_success(
    phase3_result: Phase3Result | None,
    success_scorers: list[str],
    success_threshold: float,
) -> tuple[bool, dict[str, float]]:
    """Check if required scorers meet success criteria."""
    if not phase3_result or not phase3_result.composite_score:
        return False, {}

    scorer_results = phase3_result.composite_score.scorer_results
    confidences = {name: r.confidence for name, r in scorer_results.items()}

    if not success_scorers:
        return phase3_result.is_successful, confidences

    for scorer_name in success_scorers:
        if scorer_name not in confidences:
            return False, confidences
        if confidences[scorer_name] < success_threshold:
            return False, confidences

    return True, confidences


def _extract_recon_intelligence(phase1_result: Phase1Result | None):
    """Extract ReconIntelligence from phase1 context_summary."""
    if not phase1_result or not hasattr(phase1_result, "context_summary"):
        return None
    context = phase1_result.context_summary
    if not isinstance(context, dict):
        return None
    recon_dict = context.get("recon_intelligence")
    if not recon_dict:
        return None
    try:
        from services.snipers.core.phases.articulation.models.tool_intelligence import (
            ReconIntelligence,
        )
        return ReconIntelligence(**recon_dict)
    except Exception as e:
        logger.warning(f"Failed to parse recon intelligence: {e}")
        return None


async def _run_adaptation(
    phase3_result: Phase3Result | None,
    failure_cause: str,
    target_responses: list[str],
    iteration_history: list[dict[str, Any]],
    tried_converters: list[list[str]],
    tried_framings: list[str],
    phase1_result: Phase1Result | None,
) -> dict[str, Any]:
    """
    Run LLM-powered adaptation: FailureAnalyzer -> ChainDiscovery -> Strategy.

    Returns dict with converter_names, framing_types, custom_framing,
    recon_custom_framing, payload_guidance, adaptation_reasoning.
    """
    objective = "test security boundaries"
    if phase1_result and hasattr(phase1_result, "garak_objective"):
        objective = phase1_result.garak_objective or objective

    recon_intelligence = _extract_recon_intelligence(phase1_result)

    failure_agent = FailureAnalyzerAgent()
    chain_context = await failure_agent.analyze(
        phase3_result=phase3_result,
        failure_cause=failure_cause,
        target_responses=target_responses,
        iteration_history=iteration_history,
        tried_converters=tried_converters,
        objective=objective,
        recon_intelligence=recon_intelligence,
        config={"callbacks": [CallbackHandler()], "run_name": "FailureAnalysis"},
    )

    chain_agent = ChainDiscoveryAgent()
    chain_decision = await chain_agent.generate(
        context=chain_context,
        tried_converters=tried_converters,
        objective=objective,
        recon_intelligence=recon_intelligence,
        config={"callbacks": [CallbackHandler()], "run_name": "ChainDiscovery"},
    )
    selection = chain_agent.select_best_chain(chain_decision, chain_context)

    generator = StrategyGenerator()
    gen_config: dict[str, Any] = {
        "callbacks": [CallbackHandler()],
        "run_name": "StrategyGenerator",
    }
    if recon_intelligence:
        gen_config["recon_intelligence"] = recon_intelligence.model_dump()

    decision = await generator.generate(
        responses=target_responses,
        iteration_history=iteration_history,
        tried_framings=tried_framings,
        tried_converters=tried_converters,
        objective=objective,
        pre_analysis={},
        config=gen_config,
        chain_discovery_context=chain_context,
    )

    custom_framing = None
    if decision.use_custom_framing and decision.custom_framing:
        cf = decision.custom_framing
        custom_framing = {
            "name": cf.name,
            "system_context": cf.system_context,
            "user_prefix": cf.user_prefix,
            "user_suffix": cf.user_suffix,
        }

    recon_custom_framing = None
    if decision.recon_custom_framing:
        rcf = decision.recon_custom_framing
        recon_custom_framing = {
            "role": rcf.role,
            "context": rcf.context,
            "justification": rcf.justification,
        }

    framing_types = None
    if not decision.use_custom_framing and decision.preset_framing:
        framing_types = [decision.preset_framing]

    return {
        "converter_names": selection.selected_chain,
        "framing_types": framing_types,
        "custom_framing": custom_framing,
        "recon_custom_framing": recon_custom_framing,
        "payload_guidance": decision.payload_adjustments,
        "adaptation_reasoning": decision.reasoning,
    }


async def run_adaptive_attack_streaming(
    campaign_id: str,
    target_url: str,
    scan_id: str,
    max_iterations: int = 5,
    payload_count: int = 2,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
    enable_checkpoints: bool = True,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Run adaptive attack loop with SSE streaming and checkpoint support.

    Simple while loop: each iteration runs Phase 1->2->3, evaluates,
    then adapts strategy via LLM agents if not successful.
    """
    success_scorers = success_scorers or []
    clear_pause(scan_id)

    if enable_checkpoints:
        try:
            await create_checkpoint(
                campaign_id=campaign_id,
                scan_id=scan_id,
                target_url=target_url,
                config=CheckpointConfig(
                    max_iterations=max_iterations,
                    payload_count=payload_count,
                    success_scorers=success_scorers,
                    success_threshold=success_threshold,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to create initial checkpoint: {e}")

    yield _make_event(
        "attack_started",
        f"Starting adaptive attack on {target_url}",
        data={
            "campaign_id": campaign_id,
            "target_url": target_url,
            "scan_id": scan_id,
            "max_iterations": max_iterations,
            "payload_count": payload_count,
        },
    )

    # Loop state
    iteration = 0
    tried_framings: list[str] = []
    tried_converters: list[list[str]] = []
    iteration_history: list[dict[str, Any]] = []
    best_score = 0.0
    best_iteration = 0
    is_successful = False

    # Current iteration params (defaults for first iteration)
    current_converters = converter_names or ["rot13"]
    current_framings = framing_types or [FRAMING_TYPES[0]]
    custom_framing: dict | None = None
    recon_custom_framing: dict | None = None
    payload_guidance: str | None = None
    adaptation_reasoning: str = ""
    chain_context = None

    # Phase results (persisted across iterations for final event)
    phase1_result = None
    phase2_result = None
    phase3_result = None

    try:
        while iteration < max_iterations and not is_successful:
            yield _make_event(
                "iteration_start",
                f"Iteration {iteration + 1} started",
                iteration=iteration + 1,
                data={"iteration": iteration + 1, "max_iterations": max_iterations},
            )

            # === Phase 1: Articulation ===
            yield _make_event(
                "phase1_start", "Phase 1: Payload Articulation",
                phase="phase1", iteration=iteration + 1, progress=0.0,
            )
            try:
                phase1 = PayloadArticulation()
                phase1_result = await phase1.execute(
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
                if phase1_result.framing_type and phase1_result.framing_type not in tried_framings:
                    tried_framings.append(phase1_result.framing_type)

                for i, p in enumerate(phase1_result.articulated_payloads):
                    yield _make_event(
                        "payload_generated", f"Generated payload {i + 1}",
                        phase="phase1", iteration=iteration + 1,
                        data={"index": i, "payload": p,
                              "framing_type": phase1_result.framing_types_used[i]
                              if i < len(phase1_result.framing_types_used) else None},
                        progress=(i + 1) / len(phase1_result.articulated_payloads),
                    )
                yield _make_event(
                    "phase1_complete",
                    f"Phase 1 complete: {len(phase1_result.articulated_payloads)} payloads",
                    phase="phase1", iteration=iteration + 1,
                    data={"payloads_count": len(phase1_result.articulated_payloads),
                          "framing_type": phase1_result.framing_type,
                          "framing_types_used": phase1_result.framing_types_used},
                    progress=1.0,
                )
            except Exception as e:
                logger.error(f"Phase 1 failed: {e}")
                yield _make_event("error", f"Phase 1 failed: {e}",
                                  phase="phase1", iteration=iteration + 1,
                                  data={"error": str(e), "node": "articulate"})
                break

            # === Phase 2: Conversion ===
            yield _make_event(
                "phase2_start", "Phase 2: Payload Conversion",
                phase="phase2", iteration=iteration + 1, progress=0.0,
            )
            try:
                phase2 = Conversion()
                phase2_result = await phase2.execute(
                    payloads=phase1_result.articulated_payloads,
                    chain=None,
                    converter_names=current_converters,
                )
                if phase2_result.converter_names and phase2_result.converter_names not in tried_converters:
                    tried_converters.append(phase2_result.converter_names)

                for i, c in enumerate(phase2_result.payloads):
                    yield _make_event(
                        "payload_converted", f"Converted payload {i + 1}",
                        phase="phase2", iteration=iteration + 1,
                        data={"index": i, "original": c.original,
                              "converted": c.converted,
                              "converters_applied": c.converters_applied},
                        progress=(i + 1) / len(phase2_result.payloads),
                    )
                yield _make_event(
                    "phase2_complete",
                    f"Phase 2 complete: {phase2_result.success_count} converted",
                    phase="phase2", iteration=iteration + 1,
                    data={"converter_names": phase2_result.converter_names,
                          "success_count": phase2_result.success_count,
                          "error_count": phase2_result.error_count},
                    progress=1.0,
                )
            except Exception as e:
                logger.error(f"Phase 2 failed: {e}")
                yield _make_event("error", f"Phase 2 failed: {e}",
                                  phase="phase2", iteration=iteration + 1,
                                  data={"error": str(e), "node": "convert"})
                break

            # === Phase 3: Execution ===
            yield _make_event(
                "phase3_start", f"Phase 3: Attacking {target_url}",
                phase="phase3", iteration=iteration + 1,
                data={"target_url": target_url}, progress=0.0,
            )
            try:
                phase3 = AttackExecution(target_url=target_url)
                phase3_result = await phase3.execute(
                    campaign_id=campaign_id,
                    payloads=phase2_result.payloads,
                    chain=None,
                    max_concurrent=3,
                )
                if phase3_result.total_score > best_score:
                    best_score = phase3_result.total_score
                    best_iteration = iteration + 1

                total = len(phase3_result.attack_responses)
                for i, resp in enumerate(phase3_result.attack_responses):
                    yield _make_event(
                        "attack_sent", f"Attack {i + 1}/{total} sent",
                        phase="phase3", iteration=iteration + 1,
                        data={"index": i, "payload_index": resp.payload_index,
                              "payload": resp.payload},
                        progress=(i + 0.5) / total,
                    )
                    yield _make_event(
                        "response_received", f"Response {i + 1}/{total} received",
                        phase="phase3", iteration=iteration + 1,
                        data={"index": i, "status_code": resp.status_code,
                              "latency_ms": resp.latency_ms,
                              "response": resp.response, "error": resp.error},
                        progress=(i + 1) / total,
                    )
                for name, sr in phase3_result.composite_score.scorer_results.items():
                    yield _make_event(
                        "score_calculated", f"Scorer '{name}': {sr.severity.value}",
                        phase="phase3", iteration=iteration + 1,
                        data={"scorer_name": name, "severity": sr.severity.value,
                              "confidence": sr.confidence,
                              "reasoning": getattr(sr, "reasoning", None)},
                    )
                yield _make_event(
                    "phase3_complete",
                    f"Phase 3 complete: {'BREACH' if phase3_result.is_successful else 'Blocked'}",
                    phase="phase3", iteration=iteration + 1,
                    data={"is_successful": phase3_result.is_successful,
                          "overall_severity": phase3_result.overall_severity,
                          "total_score": phase3_result.total_score},
                    progress=1.0,
                )
            except Exception as e:
                logger.error(f"Phase 3 failed: {e}")
                yield _make_event("error", f"Phase 3 failed: {e}",
                                  phase="phase3", iteration=iteration + 1,
                                  data={"error": str(e), "node": "execute"})
                break

            # === Evaluate ===
            is_successful, scorer_confidences = check_success(
                phase3_result, success_scorers, success_threshold,
            )
            iteration_history.append({
                "iteration": iteration + 1,
                "score": phase3_result.total_score,
                "is_successful": is_successful,
                "framing": current_framings,
                "converters": current_converters,
                "scorer_confidences": scorer_confidences,
            })

            yield _make_event(
                "iteration_complete",
                f"Iteration {iteration + 1}: {'SUCCESS' if is_successful else 'blocked'}",
                iteration=iteration + 1,
                data={"iteration": iteration + 1, "is_successful": is_successful,
                      "total_score": phase3_result.total_score,
                      "best_score": best_score, "best_iteration": best_iteration},
            )

            # Checkpoint
            if enable_checkpoints:
                yield from _save_checkpoint_events(
                    campaign_id, scan_id, iteration, phase2_result,
                    phase3_result, is_successful, best_score, best_iteration,
                    current_framings, current_converters, tried_framings,
                    tried_converters, adaptation_reasoning, scorer_confidences,
                )

            # Pause check
            if is_pause_requested(scan_id):
                if enable_checkpoints:
                    try:
                        await set_checkpoint_status(campaign_id, scan_id, CheckpointStatus.PAUSED)
                    except Exception as e:
                        logger.warning(f"Failed to set paused status: {e}")
                yield _make_event(
                    "attack_paused",
                    f"Attack paused after iteration {iteration + 1}",
                    iteration=iteration + 1,
                    data={"scan_id": scan_id, "best_score": best_score,
                          "best_iteration": best_iteration, "can_resume": True},
                )
                clear_pause(scan_id)
                return

            iteration += 1

            # === Adapt (if not done) ===
            if not is_successful and iteration < max_iterations:
                target_responses = [
                    r.response for r in phase3_result.attack_responses if r.response
                ]
                failure_cause = _determine_failure_cause(phase3_result)

                try:
                    adaptation = await _run_adaptation(
                        phase3_result=phase3_result,
                        failure_cause=failure_cause,
                        target_responses=target_responses,
                        iteration_history=iteration_history,
                        tried_converters=tried_converters,
                        tried_framings=tried_framings,
                        phase1_result=phase1_result,
                    )
                    current_converters = adaptation["converter_names"] or current_converters
                    current_framings = adaptation["framing_types"] or current_framings
                    custom_framing = adaptation["custom_framing"]
                    recon_custom_framing = adaptation["recon_custom_framing"]
                    payload_guidance = adaptation["payload_guidance"]
                    adaptation_reasoning = adaptation["adaptation_reasoning"] or ""

                    yield _make_event(
                        "adaptation", "Adapting strategy for next iteration",
                        iteration=iteration + 1,
                        data={
                            "adaptation_reasoning": adaptation_reasoning[:500],
                            "next_framing": current_framings,
                            "next_converters": current_converters,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Adaptation failed: {e}, keeping current params")

        # === Final event ===
        yield _build_complete_event(
            campaign_id, target_url, is_successful, iteration,
            best_score, best_iteration, iteration_history,
            adaptation_reasoning, phase1_result, phase2_result, phase3_result,
        )

    except Exception as e:
        logger.exception(f"Adaptive attack failed: {e}")
        yield _make_event(
            "error", f"Adaptive attack failed: {str(e)}",
            data={"error": str(e), "error_type": type(e).__name__},
        )
        raise


def _determine_failure_cause(phase3_result: Phase3Result) -> str:
    """Determine failure cause from phase3 result."""
    if not phase3_result:
        return "error"
    fa = phase3_result.failure_analysis or {}
    primary = fa.get("primary_cause", "unknown")
    if primary == "blocked":
        return "blocked"
    if primary == "partial_success" or phase3_result.total_score > 0:
        return "partial_success"
    if primary == "rate_limited":
        return "rate_limited"
    return "no_impact"


def _save_checkpoint_events(
    campaign_id, scan_id, iteration, phase2_result,
    phase3_result, is_successful, best_score, best_iteration,
    current_framings, current_converters, tried_framings,
    tried_converters, adaptation_reasoning, scorer_confidences,
):
    """Save checkpoint and yield checkpoint_saved event."""
    import asyncio

    try:
        payloads = []
        if phase2_result:
            payloads = [{"original": p.original, "converted": p.converted}
                        for p in phase2_result.payloads]
        responses = []
        if phase3_result:
            responses = [{"response": r.response, "status_code": r.status_code,
                          "latency_ms": r.latency_ms}
                         for r in phase3_result.attack_responses]

        iteration_data = CheckpointIteration(
            iteration=iteration + 1,
            score=phase3_result.total_score if phase3_result else 0.0,
            is_successful=is_successful,
            framing=current_framings,
            converters=current_converters,
            scorer_confidences=scorer_confidences,
            payloads=payloads,
            responses=responses,
            adaptation_reasoning=adaptation_reasoning,
            error=None,
        )
        resume_state = CheckpointResumeState(
            tried_framings=tried_framings,
            tried_converters=tried_converters,
            chain_discovery_context=None,
            custom_framing=None,
            defense_analysis={},
            target_responses=[],
        )
        status = CheckpointStatus.COMPLETED if is_successful else CheckpointStatus.RUNNING

        loop = asyncio.get_event_loop()
        loop.run_until_complete(update_checkpoint(
            campaign_id=campaign_id,
            scan_id=scan_id,
            iteration=iteration_data,
            resume_state=resume_state,
            best_score=best_score,
            best_iteration=best_iteration,
            is_successful=is_successful,
            status=status,
        ))

        yield _make_event(
            "checkpoint_saved",
            f"Progress saved (iteration {iteration + 1})",
            iteration=iteration + 1,
            data={"scan_id": scan_id, "can_resume": True},
        )
    except Exception as e:
        logger.warning(f"Failed to save checkpoint: {e}")


def _build_complete_event(
    campaign_id, target_url, is_successful, iteration,
    best_score, best_iteration, iteration_history,
    adaptation_reasoning, phase1_result, phase2_result, phase3_result,
) -> dict[str, Any]:
    """Build the final attack_complete SSE event."""
    phase1_data = None
    if phase1_result:
        phase1_data = {
            "framing_type": phase1_result.framing_type,
            "framing_types_used": phase1_result.framing_types_used,
            "payloads": phase1_result.articulated_payloads,
        }
    phase2_data = None
    if phase2_result:
        phase2_data = {
            "converter_names": phase2_result.converter_names,
            "payloads": [
                {"original": p.original, "converted": p.converted,
                 "converters_applied": p.converters_applied}
                for p in phase2_result.payloads
            ],
        }
    phase3_data = None
    if phase3_result:
        phase3_data = {
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

    return _make_event(
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


async def run_adaptive_attack(
    campaign_id: str,
    target_url: str,
    max_iterations: int = 5,
    payload_count: int = 2,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
) -> dict[str, Any]:
    """
    Run adaptive attack (non-streaming). Returns final state dict.
    """
    import uuid

    scan_id = f"{campaign_id}-adaptive-{uuid.uuid4().hex[:8]}"
    final_event: dict[str, Any] = {}

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
        enable_checkpoints=False,
    ):
        if event.get("type") == "attack_complete":
            final_event = event.get("data", {})

    return final_event


async def resume_adaptive_attack_streaming(
    campaign_id: str,
    scan_id: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """Resume an adaptive attack from a checkpoint."""
    checkpoint = await load_checkpoint_from_s3(campaign_id, scan_id)
    if not checkpoint:
        yield _make_event("error", f"Checkpoint not found: {campaign_id}/{scan_id}",
                          data={"error": "Checkpoint not found"})
        return

    if checkpoint.status not in [CheckpointStatus.PAUSED, CheckpointStatus.RUNNING]:
        yield _make_event("error",
                          f"Cannot resume: status {checkpoint.status.value}",
                          data={"error": f"Invalid status: {checkpoint.status.value}"})
        return

    await set_checkpoint_status(campaign_id, scan_id, CheckpointStatus.RUNNING)

    yield _make_event(
        "attack_resumed",
        f"Resuming attack from iteration {checkpoint.current_iteration}",
        iteration=checkpoint.current_iteration,
        data={"scan_id": scan_id, "campaign_id": campaign_id,
              "resuming_from_iteration": checkpoint.current_iteration,
              "best_score": checkpoint.best_score,
              "target_url": checkpoint.target_url},
    )

    remaining = checkpoint.config.max_iterations - checkpoint.current_iteration
    if remaining <= 0:
        yield _make_event("attack_complete", "Already at max iterations",
                          data={"scan_id": scan_id,
                                "is_successful": checkpoint.is_successful,
                                "total_iterations": checkpoint.current_iteration,
                                "best_score": checkpoint.best_score})
        return

    async for event in run_adaptive_attack_streaming(
        campaign_id=campaign_id,
        target_url=checkpoint.target_url,
        scan_id=scan_id,
        max_iterations=remaining,
        payload_count=checkpoint.config.payload_count,
        success_scorers=checkpoint.config.success_scorers or None,
        success_threshold=checkpoint.config.success_threshold,
        enable_checkpoints=True,
    ):
        yield event
