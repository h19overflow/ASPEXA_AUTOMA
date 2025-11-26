"""Scanning router - HTTP endpoints for Swarm service."""
from fastapi import APIRouter
from typing import Any, Dict

from libs.contracts.scanning import ScanJobDispatch, SafetyPolicy, ScanConfigContract
from services.swarm.entrypoint import execute_scan, execute_scan_for_campaign
from services.api_gateway.schemas import ScanStartRequest

router = APIRouter(prefix="/scan", tags=["scanning"])


def _build_scan_config(request: ScanStartRequest) -> ScanConfigContract:
    """Convert API request config to contract config."""
    if not request.config:
        return ScanConfigContract()

    cfg = request.config
    return ScanConfigContract(
        approach=cfg.approach,
        generations=cfg.generations,
        custom_probes=cfg.custom_probes or [],
        allow_agent_override=cfg.allow_agent_override,
        max_probes=cfg.max_probes,
        max_generations=cfg.max_generations,
        enable_parallel_execution=cfg.enable_parallel_execution,
        max_concurrent_probes=cfg.max_concurrent_probes,
        max_concurrent_generations=cfg.max_concurrent_generations,
        requests_per_second=cfg.requests_per_second,
        max_concurrent_connections=cfg.max_concurrent_connections,
        request_timeout=cfg.request_timeout,
        max_retries=cfg.max_retries,
        retry_backoff=cfg.retry_backoff,
        connection_type=cfg.connection_type,
    )


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
    scan_config = _build_scan_config(request)

    # Use campaign_id path (auto-load recon)
    if request.campaign_id:
        return await execute_scan_for_campaign(
            campaign_id=request.campaign_id,
            agent_types=request.agent_types,
            safety_policy=safety_policy,
            scan_config=scan_config,
            target_url=request.target_url,
        )

    # Use manual blueprint_context
    scan_dispatch = ScanJobDispatch(
        job_id=request.campaign_id or "manual",
        blueprint_context=request.blueprint_context,
        safety_policy=safety_policy,
        scan_config=scan_config,
        target_url=request.target_url,
    )
    return await execute_scan(scan_dispatch, request.agent_types)
