"""HTTP entrypoint for Snipers exploitation service.

Exposes exploitation logic for direct invocation via API gateway.
Supports three attack modes: Guided, Manual, Sweep with SSE streaming.
"""
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from services.snipers.agent.core import ExploitAgent
from services.snipers.agent.state import create_initial_state
from services.snipers.models import AttackEvent, AttackMode, ExploitStreamRequest
from services.snipers.flows import run_manual_attack, run_sweep_attack, run_guided_attack
from services.snipers.persistence.s3_adapter import (
    load_campaign_intel,
    persist_exploit_result,
    format_exploit_result,
)
from services.snipers.tools import (
    extract_vulnerable_probes,
    extract_examples_by_probe,
    aggregate_exploit_results,
)

logger = logging.getLogger(__name__)


async def execute_exploit(
    campaign_id: str,
    target_url: Optional[str] = None,
    probe_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute exploitation for a campaign.

    Args:
        campaign_id: Campaign identifier
        target_url: Optional target URL override
        probe_name: Optional specific probe to exploit

    Returns:
        Dict with exploit results and scan_id
    """
    start_time = time.time()
    logger.info(f"[Snipers] Starting exploitation for: {campaign_id}")

    try:
        intel = await load_campaign_intel(campaign_id)
    except ValueError as e:
        return {"status": "error", "error": str(e)}

    recon_data = intel.get("recon", {})
    garak_data = intel.get("garak", {})

    if not target_url:
        target_url = recon_data.get("target_url", "http://localhost/chat")

    vulnerable_probes = extract_vulnerable_probes(garak_data)
    if not vulnerable_probes:
        return {"status": "no_targets", "message": "No vulnerable probes found"}

    examples_by_probe = extract_examples_by_probe(garak_data)
    probes_to_exploit = (
        [probe_name] if probe_name else [p["probe_name"] for p in vulnerable_probes]
    )

    all_results: List[Dict[str, Any]] = []
    agent = ExploitAgent()

    for probe in probes_to_exploit:
        examples = examples_by_probe.get(probe, [])
        if not examples:
            logger.warning(f"[Snipers] No examples for {probe}, skipping")
            continue

        state = create_initial_state(
            probe_name=probe,
            example_findings=examples,
            target_url=target_url,
            recon_intelligence=recon_data.get("intelligence"),
            campaign_id=campaign_id,
        )

        try:
            result = agent.execute(state)
            all_results.append({
                "probe_name": probe,
                "result": result,
                "success": result.get("completed", False),
            })
        except Exception as e:
            logger.error(f"[Snipers] Exploit failed for {probe}: {e}")
            all_results.append({"probe_name": probe, "error": str(e), "success": False})

    execution_time = time.time() - start_time
    aggregated_state = aggregate_exploit_results(all_results, campaign_id, target_url)

    scan_id = f"exploit-{campaign_id}"
    exploit_result = format_exploit_result(
        state=aggregated_state,
        audit_id=campaign_id,
        target_url=target_url,
        execution_time=execution_time,
    )

    persisted = False
    try:
        await persist_exploit_result(
            campaign_id=campaign_id,
            scan_id=scan_id,
            exploit_result=exploit_result,
            target_url=target_url,
        )
        persisted = True
        logger.info(f"[Snipers] Persisted results: {scan_id}")
    except Exception as e:
        logger.warning(f"[Snipers] Persistence failed: {e}")

    return {
        "status": "success",
        "campaign_id": campaign_id,
        "scan_id": scan_id,
        "probes_exploited": len(probes_to_exploit),
        "successful_attacks": exploit_result.get("successful_attacks", 0),
        "failed_attacks": exploit_result.get("failed_attacks", 0),
        "execution_time_seconds": round(execution_time, 2),
        "persisted": persisted,
    }


# ============================================================================
# Streaming Mode Router (New Multi-Mode Support)
# ============================================================================

async def execute_exploit_stream(
    request: ExploitStreamRequest,
) -> AsyncGenerator[AttackEvent, None]:
    """
    Execute exploitation with SSE streaming.

    Routes to appropriate flow based on attack mode:
    - GUIDED: Pattern-learning from Garak findings
    - MANUAL: Custom payload with converters
    - SWEEP: All probes in selected categories

    Args:
        request: ExploitStreamRequest with mode and parameters

    Yields:
        AttackEvent objects for SSE streaming
    """
    logger.info(f"[Snipers] Starting {request.mode.value} attack: target={request.target_url}")

    # Load campaign intel if provided (for guided mode)
    garak_findings = None
    if request.campaign_id and request.mode == AttackMode.GUIDED:
        try:
            intel = await load_campaign_intel(request.campaign_id)
            garak_data = intel.get("garak", {})
            garak_findings = _extract_garak_findings(garak_data)
        except Exception as e:
            logger.warning(f"Failed to load campaign intel: {e}")

    # Route to appropriate flow
    if request.mode == AttackMode.MANUAL:
        async for event in run_manual_attack(request):
            yield event

    elif request.mode == AttackMode.SWEEP:
        async for event in run_sweep_attack(request):
            yield event

    elif request.mode == AttackMode.GUIDED:
        async for event in run_guided_attack(request, garak_findings):
            yield event

    else:
        yield AttackEvent(
            type="error",
            data={"message": f"Unknown attack mode: {request.mode}"},
        )


def _extract_garak_findings(garak_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract vulnerability findings from Garak data for guided mode."""
    findings = []

    # Handle different Garak data formats
    if "results" in garak_data:
        for result in garak_data["results"]:
            if result.get("status") == "fail":
                findings.append({
                    "probe_name": result.get("probe_name", ""),
                    "prompt": result.get("prompt", ""),
                    "output": result.get("output", ""),
                    "status": result.get("status", ""),
                    "detector_name": result.get("detector_name", ""),
                    "detector_score": result.get("detector_score", 0.0),
                })

    elif "vulnerability_clusters" in garak_data:
        for cluster in garak_data["vulnerability_clusters"]:
            for finding in cluster.get("findings", []):
                findings.append(finding)

    return findings
