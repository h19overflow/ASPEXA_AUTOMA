"""HTTP entrypoint for Cartographer service.

Exposes reconnaissance logic for direct invocation via API gateway.
"""
import logging
from datetime import datetime
from typing import Any, Dict, AsyncGenerator

from libs.contracts.recon import ReconRequest, ReconBlueprint, Intelligence
from services.cartographer.agent.graph import run_reconnaissance, run_reconnaissance_streaming
from services.cartographer.persistence.s3_adapter import persist_recon_result
from services.cartographer.consumer import (
    extract_infrastructure_intel,
    extract_auth_structure,
    extract_detected_tools,
)

logger = logging.getLogger(__name__)


async def execute_recon(request: ReconRequest) -> Dict[str, Any]:
    """Execute reconnaissance and persist results.

    Args:
        request: Validated ReconRequest

    Returns:
        Dict with blueprint data and scan_id
    """
    logger.info(f"[Cartographer] Starting recon for audit: {request.audit_id}")

    observations = await run_reconnaissance(
        audit_id=request.audit_id,
        target_url=request.target.url,
        auth_headers=request.target.auth_headers,
        scope={
            "depth": request.scope.depth.value,
            "max_turns": request.scope.max_turns,
            "forbidden_keywords": request.scope.forbidden_keywords,
        },
        special_instructions=request.special_instructions,
    )

    system_prompts = list(dict.fromkeys(observations.get("system_prompt", [])))

    # Combine all observations for comprehensive extraction
    all_tool_obs = observations.get("tools", []) + observations.get("infrastructure", [])
    all_auth_obs = observations.get("authorization", [])

    blueprint = ReconBlueprint(
        audit_id=request.audit_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        intelligence=Intelligence(
            system_prompt_leak=system_prompts,
            detected_tools=extract_detected_tools(all_tool_obs),
            infrastructure=extract_infrastructure_intel(all_tool_obs),
            auth_structure=extract_auth_structure(all_auth_obs),
        ),
        raw_observations=observations if observations else None,
    )

    scan_id = f"recon-{request.audit_id}"
    persisted = False

    try:
        await persist_recon_result(
            campaign_id=request.audit_id,
            scan_id=scan_id,
            blueprint=blueprint.model_dump(),
            target_url=request.target.url,
        )
        persisted = True
        logger.info(f"[Cartographer] Persisted recon: {scan_id}")
    except Exception as e:
        logger.warning(f"[Cartographer] Persistence failed: {e}")

    return {
        "audit_id": request.audit_id,
        "scan_id": scan_id,
        "blueprint": blueprint.model_dump(),
        "persisted": persisted,
    }


async def execute_recon_streaming(request: ReconRequest) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute reconnaissance with streaming log events.

    Yields log events during execution and final result at end.
    """
    logger.info(f"[Cartographer] Starting streaming recon for audit: {request.audit_id}")

    yield {"type": "log", "message": f"Starting recon for {request.target.url}"}

    observations = {}
    all_deductions = {}

    async for event in run_reconnaissance_streaming(
        audit_id=request.audit_id,
        target_url=request.target.url,
        auth_headers=request.target.auth_headers,
        scope={
            "depth": request.scope.depth.value,
            "max_turns": request.scope.max_turns,
            "forbidden_keywords": request.scope.forbidden_keywords,
        },
        special_instructions=request.special_instructions,
    ):
        if event.get("type") == "observations":
            observations = event.get("data", {})
        elif event.get("type") == "all_deductions":
            # Use comprehensive deductions from graph (replaces incremental collection)
            all_deductions = event.get("data", {})
        elif event.get("type") == "deduction":
            # Stream deduction to frontend as it happens
            yield event
        else:
            yield event

    system_prompts = list(dict.fromkeys(observations.get("system_prompt", [])))

    # Combine all observations for comprehensive extraction
    all_tool_obs = observations.get("tools", []) + observations.get("infrastructure", [])
    all_auth_obs = observations.get("authorization", [])

    blueprint = ReconBlueprint(
        audit_id=request.audit_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        intelligence=Intelligence(
            system_prompt_leak=system_prompts,
            detected_tools=extract_detected_tools(all_tool_obs),
            infrastructure=extract_infrastructure_intel(all_tool_obs),
            auth_structure=extract_auth_structure(all_auth_obs),
        ),
        raw_observations=observations if observations else None,
        structured_deductions=all_deductions if all_deductions else None,
    )

    scan_id = f"recon-{request.audit_id}"
    persisted = False

    try:
        await persist_recon_result(
            campaign_id=request.audit_id,
            scan_id=scan_id,
            blueprint=blueprint.model_dump(),
            target_url=request.target.url,
        )
        persisted = True
        yield {"type": "log", "message": f"Results persisted: {scan_id}"}
    except Exception as e:
        yield {"type": "log", "level": "warning", "message": f"Persistence failed: {e}"}

    yield {
        "type": "complete",
        "data": {
            "audit_id": request.audit_id,
            "scan_id": scan_id,
            "blueprint": blueprint.model_dump(),
            "persisted": persisted,
        },
    }
