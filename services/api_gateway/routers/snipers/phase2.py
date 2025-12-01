"""
Phase 2: Conversion Router.

Purpose: HTTP endpoints for payload conversion through converter chains
Role: Second phase of composable attack flow
Dependencies: Conversion, Phase2 schemas
"""

import logging
from fastapi import APIRouter, HTTPException

from services.api_gateway.schemas.snipers import (
    Phase2Request,
    Phase2WithChainRequest,
    Phase2Response,
    ConvertedPayloadResponse,
    AvailableConvertersResponse,
)
from services.snipers.attack_phases import Conversion
from services.snipers.chain_discovery.models import ConverterChain

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/phase2", tags=["snipers-phase2"])


def _result_to_response(result) -> Phase2Response:
    """Convert Phase2Result to response model."""
    payloads = [
        ConvertedPayloadResponse(
            original=p.original,
            converted=p.converted,
            chain_id=p.chain_id,
            converters_applied=p.converters_applied,
            errors=p.errors,
        )
        for p in result.payloads
    ]
    return Phase2Response(
        chain_id=result.chain_id,
        converter_names=result.converter_names,
        payloads=payloads,
        success_count=result.success_count,
        error_count=result.error_count,
    )


@router.post("", response_model=Phase2Response)
async def execute_phase2(request: Phase2Request) -> Phase2Response:
    """
    Execute Phase 2: Conversion.

    Applies converter chain to payloads.
    Can be used standalone with manual payloads and converters.

    Returns converted payloads ready for Phase 3.
    """
    try:
        phase2 = Conversion()

        result = await phase2.execute(
            payloads=request.payloads,
            converter_names=request.converter_names,
            converter_params=request.converter_params,
        )

        return _result_to_response(result)

    except ValueError as e:
        logger.error(f"Phase 2 validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Phase 2 execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Phase 2 execution failed: {e}")


@router.post("/with-phase1", response_model=Phase2Response)
async def execute_phase2_with_chain(request: Phase2WithChainRequest) -> Phase2Response:
    """
    Execute Phase 2 using Phase 1 result.

    Automatically uses the chain selected in Phase 1.
    Optionally override with custom converters.
    """
    try:
        phase2 = Conversion()

        # Build chain from Phase 1 response if no override
        chain = None
        converter_names = request.override_converters

        if converter_names is None and request.phase1_response.selected_chain:
            chain = ConverterChain.from_converter_names(
                converter_names=request.phase1_response.selected_chain.converter_names,
            )

        result = await phase2.execute(
            payloads=request.phase1_response.articulated_payloads,
            chain=chain,
            converter_names=converter_names,
        )

        return _result_to_response(result)

    except ValueError as e:
        logger.error(f"Phase 2 validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Phase 2 execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Phase 2 execution failed: {e}")


@router.get("/converters", response_model=AvailableConvertersResponse)
async def list_converters() -> AvailableConvertersResponse:
    """List all available converters for manual chain building."""
    phase2 = Conversion()
    converters = phase2.list_available_converters()
    return AvailableConvertersResponse(converters=converters)


@router.post("/preview")
async def preview_conversion(
    payload: str,
    converters: list[str],
) -> ConvertedPayloadResponse:
    """
    Preview conversion on a single payload.

    Useful for testing converter combinations before full execution.
    """
    try:
        phase2 = Conversion()
        result = await phase2.execute(
            payloads=[payload],
            converter_names=converters,
        )

        if not result.payloads:
            raise HTTPException(status_code=500, detail="No payload converted")

        p = result.payloads[0]
        return ConvertedPayloadResponse(
            original=p.original,
            converted=p.converted,
            chain_id=p.chain_id,
            converters_applied=p.converters_applied,
            errors=p.errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Preview conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
