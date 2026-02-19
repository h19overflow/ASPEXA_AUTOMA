"""
Phase 2: Converters Router.

Purpose: HTTP endpoint to list available payload converters
Role: Used by OneShot and Adaptive pages to populate converter selection
Dependencies: Conversion, AvailableConvertersResponse schema
"""

import logging
from fastapi import APIRouter, HTTPException

from services.api_gateway.schemas.snipers import AvailableConvertersResponse
from services.snipers.attack_phases import Conversion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/phase2", tags=["snipers-phase2"])


@router.get("/converters", response_model=AvailableConvertersResponse)
async def list_converters() -> AvailableConvertersResponse:
    """List all available converters for payload transformation."""
    try:
        phase2 = Conversion()
        converters = phase2.list_available_converters()
        return AvailableConvertersResponse(converters=converters)
    except Exception as e:
        logger.exception(f"List converters failed: {e}")
        raise HTTPException(status_code=500, detail=f"List converters failed: {e}")
