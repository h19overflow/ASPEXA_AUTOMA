"""
Phase 3: Attack Execution Router.

Purpose: HTTP endpoints for attack execution and response scoring
Role: Third phase of composable attack flow
Dependencies: AttackExecution, Phase3 schemas
"""

import logging
from fastapi import APIRouter, HTTPException

from services.api_gateway.schemas.snipers import (
    Phase3Request,
    Phase3WithPhase2Request,
    Phase3Response,
    AttackResponseItem,
    ScorerResultItem,
    CompositeScoreResponse,
    ConverterChainResponse,
)
from services.snipers.attack_phases import AttackExecution
from services.snipers.models import ConvertedPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/phase3", tags=["snipers-phase3"])


def _result_to_response(result) -> Phase3Response:
    """Convert Phase3Result to response model."""
    attack_responses = [
        AttackResponseItem(
            payload_index=r.payload_index,
            payload=r.payload,
            response=r.response,
            status_code=r.status_code,
            latency_ms=r.latency_ms,
            error=r.error,
        )
        for r in result.attack_responses
    ]

    scorer_results = {
        name: ScorerResultItem(
            severity=sr.severity.value,
            confidence=sr.confidence,
            reasoning=sr.reasoning if hasattr(sr, 'reasoning') else None,
        )
        for name, sr in result.composite_score.scorer_results.items()
    }

    composite_score = CompositeScoreResponse(
        overall_severity=result.composite_score.overall_severity.value,
        total_score=result.composite_score.total_score,
        is_successful=result.composite_score.is_successful,
        scorer_results=scorer_results,
    )

    learned_chain = None
    if result.learned_chain:
        learned_chain = ConverterChainResponse(
            chain_id=result.learned_chain.chain_id,
            converter_names=result.learned_chain.converter_names,
            defense_patterns=result.learned_chain.defense_patterns or [],
        )

    return Phase3Response(
        campaign_id=result.campaign_id,
        target_url=result.target_url,
        attack_responses=attack_responses,
        composite_score=composite_score,
        is_successful=result.is_successful,
        overall_severity=result.overall_severity,
        total_score=result.total_score,
        learned_chain=learned_chain,
        failure_analysis=result.failure_analysis,
        adaptation_strategy=result.adaptation_strategy,
    )


@router.post("", response_model=Phase3Response)
async def execute_phase3(request: Phase3Request) -> Phase3Response:
    """
    Execute Phase 3: Attack Execution.

    Sends converted payloads to target, scores responses, and records learnings.
    Can be used standalone with manual payloads.
    """
    try:
        phase3 = AttackExecution(
            target_url=request.target_url,
            headers=request.headers,
            timeout=request.timeout,
        )

        # Convert request payloads to ConvertedPayload
        payloads = [
            ConvertedPayload(
                original=p.original,
                converted=p.converted,
                chain_id=p.chain_id,
                converters_applied=p.converters_applied,
                errors=p.errors,
            )
            for p in request.payloads
        ]

        result = await phase3.execute(
            campaign_id=request.campaign_id,
            payloads=payloads,
            max_concurrent=request.max_concurrent,
        )

        return _result_to_response(result)

    except ValueError as e:
        logger.error(f"Phase 3 validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Phase 3 execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Phase 3 execution failed: {e}")


@router.post("/with-phase2", response_model=Phase3Response)
async def execute_phase3_with_phase2(request: Phase3WithPhase2Request) -> Phase3Response:
    """
    Execute Phase 3 using Phase 2 result.

    Automatically uses payloads from Phase 2.
    """
    try:
        phase3 = AttackExecution(
            target_url=request.target_url,
            headers=request.headers,
            timeout=request.timeout,
        )

        # Convert Phase 2 response payloads to ConvertedPayload
        payloads = [
            ConvertedPayload(
                original=p.original,
                converted=p.converted,
                chain_id=p.chain_id,
                converters_applied=p.converters_applied,
                errors=p.errors,
            )
            for p in request.phase2_response.payloads
        ]

        result = await phase3.execute(
            campaign_id=request.campaign_id,
            payloads=payloads,
            max_concurrent=request.max_concurrent,
        )

        return _result_to_response(result)

    except ValueError as e:
        logger.error(f"Phase 3 validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Phase 3 execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Phase 3 execution failed: {e}")


@router.get("/scorers")
async def list_scorers() -> dict:
    """List available scorers for attack evaluation."""
    return {
        "scorers": [
            {
                "name": "jailbreak",
                "description": "Detects jailbreak/bypass attempts",
            },
            {
                "name": "prompt_leak",
                "description": "Detects system prompt leakage",
            },
            {
                "name": "data_leak",
                "description": "Detects sensitive data exposure",
            },
            {
                "name": "tool_abuse",
                "description": "Detects tool/function call abuse",
            },
            {
                "name": "pii_exposure",
                "description": "Detects PII (Personally Identifiable Information) exposure",
            },
        ]
    }
