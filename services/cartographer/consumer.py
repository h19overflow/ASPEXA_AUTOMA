"""Cartographer service consumer - Integrates recon agent with event bus.

Purpose: FastStream event handler for reconnaissance requests
Role: Receives events from message bus, orchestrates recon, publishes results
Dependencies: libs.events.publisher, libs.contracts.recon, agent.graph, persistence
"""

import logging
from datetime import datetime

from libs.events.publisher import broker, publish_recon_finished, CMD_RECON_START
from libs.contracts.recon import ReconRequest, ReconBlueprint, Intelligence

from services.cartographer.agent.graph import run_reconnaissance
from services.cartographer.persistence.s3_adapter import persist_recon_result
from services.cartographer.intelligence import (
    extract_infrastructure_intel,
    extract_auth_structure,
    extract_detected_tools,
)

logger = logging.getLogger(__name__)


@broker.subscriber(CMD_RECON_START)
async def handle_recon_request(message: dict):
    """Handle reconnaissance request from event bus."""
    try:
        # Validate and parse IF-01 request
        request = ReconRequest(**message)

        print(f"[Cartographer] Starting reconnaissance for audit: {request.audit_id}")

        # Run reconnaissance
        observations = await run_reconnaissance(
            audit_id=request.audit_id,
            target_url=request.target.url,
            auth_headers=request.target.auth_headers,
            scope={
                "depth": request.scope.depth.value,
                "max_turns": request.scope.max_turns,
                "forbidden_keywords": request.scope.forbidden_keywords
            }
        )

        print(f"[Cartographer] Reconnaissance complete. Observations collected:")
        print(f"  - System Prompt: {len(observations.get('system_prompt', []))}")
        print(f"  - Tools: {len(observations.get('tools', []))}")
        print(f"  - Authorization: {len(observations.get('authorization', []))}")
        print(f"  - Infrastructure: {len(observations.get('infrastructure', []))}")

        # Deduplicate system prompts
        system_prompts = list(dict.fromkeys(observations.get("system_prompt", [])))

        # Map observations to IF-02 blueprint
        blueprint = ReconBlueprint(
            audit_id=request.audit_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            intelligence=Intelligence(
                system_prompt_leak=system_prompts,
                detected_tools=extract_detected_tools(observations.get("tools", [])),
                infrastructure=extract_infrastructure_intel(
                    observations.get("infrastructure", []) + observations.get("tools", [])
                ),
                auth_structure=extract_auth_structure(observations.get("authorization", []))
            )
        )

        # Persist to S3 and update campaign stage
        scan_id = f"recon-{request.audit_id}"
        try:
            await persist_recon_result(
                campaign_id=request.audit_id,
                scan_id=scan_id,
                blueprint=blueprint.model_dump(),
                target_url=request.target.url,
            )
            print(f"[Cartographer] Persisted recon to S3: {scan_id}")
        except Exception as e:
            logger.warning(f"Persistence failed (continuing): {e}")

        # Publish IF-02 blueprint with scan_id reference
        payload = blueprint.model_dump()
        payload["recon_scan_id"] = scan_id
        await publish_recon_finished(payload)

        print(f"[Cartographer] Published reconnaissance blueprint for audit: {request.audit_id}")

    except Exception as e:
        print(f"[Cartographer] Error processing reconnaissance request: {e}")
        import traceback
        traceback.print_exc()
