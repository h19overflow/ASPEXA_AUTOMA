"""Reconnaissance router - HTTP endpoints for Cartographer service."""
from fastapi import APIRouter, HTTPException
from typing import Any, Dict

from libs.contracts.recon import ReconRequest, TargetConfig, ScopeConfig
from libs.contracts.common import DepthLevel
from services.cartographer.entrypoint import execute_recon
from services.api_gateway.schemas import ReconStartRequest

router = APIRouter(prefix="/recon", tags=["reconnaissance"])


@router.post("/start")
async def start_recon(request: ReconStartRequest) -> Dict[str, Any]:
    """Start reconnaissance for a target.

    Returns blueprint with scan_id for tracking.
    """
    try:
        depth = DepthLevel(request.depth)
    except ValueError:
        raise HTTPException(400, f"Invalid depth: {request.depth}")

    recon_request = ReconRequest(
        audit_id=request.audit_id,
        target=TargetConfig(url=request.target_url, auth_headers=request.auth_headers),
        scope=ScopeConfig(
            depth=depth,
            max_turns=request.max_turns,
            forbidden_keywords=request.forbidden_keywords,
        ),
    )

    result = await execute_recon(recon_request)
    return result
