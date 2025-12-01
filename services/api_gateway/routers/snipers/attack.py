"""
Full Attack & Adaptive Attack Router.

Purpose: HTTP endpoints for complete attack execution
Role: Orchestrates all three phases or adaptive loop
Dependencies: entrypoint functions, Attack schemas
"""

import logging
import uuid

from fastapi import APIRouter, HTTPException

from services.api_gateway.schemas.snipers import (
    FullAttackRequest,
    FullAttackResponse,
    AdaptiveAttackRequest,
    AdaptiveAttackResponse,
    Phase1Response,
    Phase2Response,
    Phase3Response,
    ConverterChainResponse,
    ConvertedPayloadResponse,
    AttackResponseItem,
    ScorerResultItem,
    CompositeScoreResponse,
    IterationHistoryItem,
)
from services.snipers.entrypoint import execute_full_attack, execute_adaptive_attack

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attack", tags=["snipers-attack"])


def _build_phase1_response(result) -> Phase1Response:
    """Build Phase1Response from FullAttackResult."""
    phase1 = result.phase1
    selected_chain = None
    if phase1.selected_chain:
        selected_chain = ConverterChainResponse(
            chain_id=phase1.selected_chain.chain_id,
            converter_names=phase1.selected_chain.converter_names,
            defense_patterns=phase1.selected_chain.defense_patterns or [],
        )
    return Phase1Response(
        campaign_id=phase1.campaign_id,
        selected_chain=selected_chain,
        articulated_payloads=phase1.articulated_payloads,
        framing_type=phase1.framing_type,
        framing_types_used=phase1.framing_types_used,
        context_summary=phase1.context_summary,
        garak_objective=phase1.garak_objective,
        defense_patterns=phase1.defense_patterns,
        tools_detected=phase1.tools_detected,
    )


def _build_phase2_response(result) -> Phase2Response:
    """Build Phase2Response from FullAttackResult."""
    phase2 = result.phase2
    payloads = [
        ConvertedPayloadResponse(
            original=p.original,
            converted=p.converted,
            chain_id=p.chain_id,
            converters_applied=p.converters_applied,
            errors=p.errors,
        )
        for p in phase2.payloads
    ]
    return Phase2Response(
        chain_id=phase2.chain_id,
        converter_names=phase2.converter_names,
        payloads=payloads,
        success_count=phase2.success_count,
        error_count=phase2.error_count,
    )


def _build_phase3_response(result) -> Phase3Response:
    """Build Phase3Response from FullAttackResult."""
    phase3 = result.phase3
    attack_responses = [
        AttackResponseItem(
            payload_index=r.payload_index,
            payload=r.payload,
            response=r.response,
            status_code=r.status_code,
            latency_ms=r.latency_ms,
            error=r.error,
        )
        for r in phase3.attack_responses
    ]

    scorer_results = {
        name: ScorerResultItem(
            severity=sr.severity.value,
            confidence=sr.confidence,
            reasoning=sr.reasoning if hasattr(sr, 'reasoning') else None,
        )
        for name, sr in phase3.composite_score.scorer_results.items()
    }

    composite_score = CompositeScoreResponse(
        overall_severity=phase3.composite_score.overall_severity.value,
        total_score=phase3.composite_score.total_score,
        is_successful=phase3.composite_score.is_successful,
        scorer_results=scorer_results,
    )

    learned_chain = None
    if phase3.learned_chain:
        learned_chain = ConverterChainResponse(
            chain_id=phase3.learned_chain.chain_id,
            converter_names=phase3.learned_chain.converter_names,
            defense_patterns=phase3.learned_chain.defense_patterns or [],
        )

    return Phase3Response(
        campaign_id=phase3.campaign_id,
        target_url=phase3.target_url,
        attack_responses=attack_responses,
        composite_score=composite_score,
        is_successful=phase3.is_successful,
        overall_severity=phase3.overall_severity,
        total_score=phase3.total_score,
        learned_chain=learned_chain,
        failure_analysis=phase3.failure_analysis,
        adaptation_strategy=phase3.adaptation_strategy,
    )


@router.post("/full", response_model=FullAttackResponse)
async def run_full_attack(request: FullAttackRequest) -> FullAttackResponse:
    """
    Execute complete single-shot attack.

    Runs all three phases in sequence:
    1. Payload Articulation
    2. Conversion
    3. Attack Execution

    Results are persisted to S3 and campaign stage is updated.
    """
    try:
        # Convert framing types to strings
        framing_types = None
        if request.framing_types:
            framing_types = [f.value for f in request.framing_types]

        result = await execute_full_attack(
            campaign_id=request.campaign_id,
            target_url=request.target_url,
            payload_count=request.payload_count,
            framing_types=framing_types,
            converter_names=request.converter_names,
            max_concurrent=request.max_concurrent,
        )

        # Generate scan_id for response
        scan_id = f"{request.campaign_id}-{uuid.uuid4().hex[:8]}"

        return FullAttackResponse(
            campaign_id=result.campaign_id,
            target_url=result.target_url,
            scan_id=scan_id,
            phase1=_build_phase1_response(result),
            phase2=_build_phase2_response(result),
            phase3=_build_phase3_response(result),
            is_successful=result.is_successful,
            overall_severity=result.overall_severity,
            total_score=result.total_score,
            payloads_generated=result.payloads_generated,
            payloads_sent=result.payloads_sent,
        )

    except ValueError as e:
        logger.error(f"Full attack validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Full attack execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Full attack failed: {e}")


@router.post("/adaptive", response_model=AdaptiveAttackResponse)
async def run_adaptive_attack(request: AdaptiveAttackRequest) -> AdaptiveAttackResponse:
    """
    Execute adaptive attack with automatic parameter adjustment.

    Uses LangGraph state machine to iterate through attack phases,
    automatically adapting framing/converters based on failure analysis.

    Continues until success or max_iterations reached.
    Results are persisted to S3 and campaign stage is updated.
    """
    try:
        # Convert enums to strings
        framing_types = None
        if request.framing_types:
            framing_types = [f.value for f in request.framing_types]

        success_scorers = None
        if request.success_scorers:
            success_scorers = [s.value for s in request.success_scorers]

        result = await execute_adaptive_attack(
            campaign_id=request.campaign_id,
            target_url=request.target_url,
            max_iterations=request.max_iterations,
            payload_count=request.payload_count,
            framing_types=framing_types,
            converter_names=request.converter_names,
            success_scorers=success_scorers,
            success_threshold=request.success_threshold,
        )

        # Generate scan_id for response
        scan_id = f"{request.campaign_id}-adaptive-{uuid.uuid4().hex[:8]}"

        # Build iteration history
        iteration_history = [
            IterationHistoryItem(
                iteration=entry.get("iteration", 0),
                is_successful=entry.get("is_successful", False),
                score=entry.get("score", 0.0),
                framing=entry.get("framing"),
                converters=entry.get("converters"),
            )
            for entry in result.get("iteration_history", [])
        ]

        # Build final phase3 response if available
        final_phase3 = None
        phase3_result = result.get("phase3_result")
        if phase3_result:
            attack_responses = [
                AttackResponseItem(
                    payload_index=r.payload_index,
                    payload=r.payload,
                    response=r.response,
                    status_code=r.status_code,
                    latency_ms=r.latency_ms,
                    error=r.error,
                )
                for r in phase3_result.attack_responses
            ]

            scorer_results = {
                name: ScorerResultItem(
                    severity=sr.severity.value,
                    confidence=sr.confidence,
                )
                for name, sr in phase3_result.composite_score.scorer_results.items()
            }

            composite_score = CompositeScoreResponse(
                overall_severity=phase3_result.composite_score.overall_severity.value,
                total_score=phase3_result.composite_score.total_score,
                is_successful=phase3_result.composite_score.is_successful,
                scorer_results=scorer_results,
            )

            final_phase3 = Phase3Response(
                campaign_id=phase3_result.campaign_id,
                target_url=phase3_result.target_url,
                attack_responses=attack_responses,
                composite_score=composite_score,
                is_successful=phase3_result.is_successful,
                overall_severity=phase3_result.overall_severity,
                total_score=phase3_result.total_score,
                failure_analysis=phase3_result.failure_analysis,
                adaptation_strategy=phase3_result.adaptation_strategy,
            )

        return AdaptiveAttackResponse(
            campaign_id=result.get("campaign_id", request.campaign_id),
            target_url=result.get("target_url", request.target_url),
            scan_id=scan_id,
            is_successful=result.get("is_successful", False),
            total_iterations=result.get("iteration", 0) + 1,
            best_score=result.get("best_score", 0.0),
            best_iteration=result.get("best_iteration", 0),
            iteration_history=iteration_history,
            final_phase3=final_phase3,
            adaptation_reasoning=result.get("adaptation_reasoning"),
        )

    except ValueError as e:
        logger.error(f"Adaptive attack validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Adaptive attack execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Adaptive attack failed: {e}")
