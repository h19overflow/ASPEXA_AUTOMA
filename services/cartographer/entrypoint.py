
"""HTTP entrypoint for Cartographer service.

Exposes reconnaissance logic for direct invocation via API gateway.
"""
import logging
from datetime import datetime
from typing import Any, Dict

from libs.contracts.recon import ReconRequest, ReconBlueprint, Intelligence
from services.cartographer.agent.graph import run_reconnaissance
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
    )

    system_prompts = list(dict.fromkeys(observations.get("system_prompt", [])))

    blueprint = ReconBlueprint(
        audit_id=request.audit_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        intelligence=Intelligence(
            system_prompt_leak=system_prompts,
            detected_tools=extract_detected_tools(observations.get("tools", [])),
            infrastructure=extract_infrastructure_intel(
                observations.get("infrastructure", []) + observations.get("tools", [])
            ),
            auth_structure=extract_auth_structure(observations.get("authorization", [])),
        ),
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
