"""
Phase 1: Payload Articulation Router.

Purpose: HTTP endpoints for payload generation from campaign intelligence
Role: First phase of composable attack flow
Dependencies: PayloadArticulation, Phase1 schemas
"""

import logging
from fastapi import APIRouter, HTTPException

from services.api_gateway.schemas.snipers import (
    Phase1Request,
    Phase1Response,
    ConverterChainResponse,
)
from services.snipers.attack_phases import PayloadArticulation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/phase1", tags=["snipers-phase1"])


def _chain_to_response(chain) -> ConverterChainResponse | None:
    """Convert ConverterChain to response model."""
    if chain is None:
        return None
    return ConverterChainResponse(
        chain_id=chain.chain_id,
        converter_names=chain.converter_names,
        defense_patterns=chain.defense_patterns or [],
    )


@router.post("", response_model=Phase1Response)
async def execute_phase1(request: Phase1Request) -> Phase1Response:
    """
    Execute Phase 1: Payload Articulation.

    Loads campaign intelligence from S3, selects optimal converter chain,
    and generates articulated payloads with framing strategies.

    Returns payloads ready for Phase 2 conversion.
    """
    try:
        phase1 = PayloadArticulation()

        # Convert framing types to strings
        framing_types = None
        if request.framing_types:
            framing_types = [f.value for f in request.framing_types]

        # Convert custom framing to dict
        custom_framing = None
        if request.custom_framing:
            custom_framing = request.custom_framing.model_dump()

        result = await phase1.execute(
            campaign_id=request.campaign_id,
            payload_count=request.payload_count,
            framing_types=framing_types,
            custom_framing=custom_framing,
        )

        return Phase1Response(
            campaign_id=result.campaign_id,
            selected_chain=_chain_to_response(result.selected_chain),
            articulated_payloads=result.articulated_payloads,
            framing_type=result.framing_type,
            framing_types_used=result.framing_types_used,
            context_summary=result.context_summary,
            garak_objective=result.garak_objective,
            defense_patterns=result.defense_patterns,
            tools_detected=result.tools_detected,
        )

    except ValueError as e:
        logger.error(f"Phase 1 validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Phase 1 execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Phase 1 execution failed: {e}")


@router.get("/framing-types")
async def list_framing_types() -> dict:
    """List available framing types for payload articulation."""
    return {
        "framing_types": [
            {
                "name": "qa_testing",
                "description": "Frame as QA testing scenario",
            },
            {
                "name": "compliance_audit",
                "description": "Frame as compliance audit",
            },
            {
                "name": "documentation",
                "description": "Frame as documentation request",
            },
            {
                "name": "debugging",
                "description": "Frame as debugging session",
            },
            {
                "name": "educational",
                "description": "Frame as educational content",
            },
            {
                "name": "research",
                "description": "Frame as security research",
            },
        ]
    }
