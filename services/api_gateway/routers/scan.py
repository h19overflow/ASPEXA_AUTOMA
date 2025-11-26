"""Scanning router - HTTP endpoints for Swarm service."""
from fastapi import APIRouter
from typing import Any, Dict

from libs.contracts.scanning import ScanJobDispatch, SafetyPolicy
from services.swarm.entrypoint import execute_scan, execute_scan_for_campaign
from services.api_gateway.schemas import ScanStartRequest

router = APIRouter(prefix="/scan", tags=["scanning"])


@router.post("/start")
async def start_scan(request: ScanStartRequest) -> Dict[str, Any]:
    """Start vulnerability scanning with Trinity agents.

    Provide EITHER:
    - campaign_id: Auto-loads recon from S3
    - blueprint_context: Manual recon data

    Returns:
        Results per agent type with scan_ids
    """
    safety_policy = SafetyPolicy(
        allowed_attack_vectors=request.allowed_attack_vectors,
        blocked_attack_vectors=request.blocked_attack_vectors,
        aggressiveness=request.aggressiveness,
    )

    # Use campaign_id path (auto-load recon)
    if request.campaign_id:
        return await execute_scan_for_campaign(
            campaign_id=request.campaign_id,
            agent_types=request.agent_types,
            safety_policy=safety_policy,
        )

    # Use manual blueprint_context
    scan_dispatch = ScanJobDispatch(
        job_id=request.campaign_id or "manual",
        blueprint_context=request.blueprint_context,
        safety_policy=safety_policy,
    )
    return await execute_scan(scan_dispatch, request.agent_types)
