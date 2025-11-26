"""HTTP entrypoint for Snipers exploitation service.

Exposes exploitation logic for direct invocation via API gateway.
"""
import logging
import time
from typing import Any, Dict, List, Optional

from services.snipers.agent.core import ExploitAgent
from services.snipers.agent.state import create_initial_state
from services.snipers.persistence.s3_adapter import (
    load_campaign_intel,
    persist_exploit_result,
    format_exploit_result,
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

    vulnerable_probes = _extract_vulnerable_probes(garak_data)
    if not vulnerable_probes:
        return {"status": "no_targets", "message": "No vulnerable probes found"}

    examples_by_probe = _extract_examples(garak_data)
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
    aggregated_state = _aggregate_results(all_results, campaign_id, target_url)

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


def _extract_vulnerable_probes(garak_data: dict) -> List[Dict[str, Any]]:
    """Extract vulnerable probes from garak report."""
    if not garak_data:
        return []
    probes = garak_data.get("vulnerable_probes", {}).get("summary", [])
    return [p for p in probes if p.get("status") == "vulnerable"]


def _extract_examples(garak_data: dict) -> Dict[str, List]:
    """Extract example findings per probe."""
    if not garak_data:
        return {}

    findings = garak_data.get("vulnerability_findings", {}).get("results", [])
    probes = garak_data.get("vulnerable_probes", {}).get("summary", [])
    examples_by_probe: Dict[str, List] = {}

    for probe in probes:
        probe_name = probe.get("probe_name")
        if not probe_name:
            continue

        probe_findings = [
            f for f in findings
            if f.get("probe_name") == probe_name and f.get("status") == "fail"
        ]

        if probe_findings:
            sorted_findings = sorted(
                probe_findings, key=lambda x: x.get("detector_score", 0), reverse=True
            )[:3]
            examples_by_probe[probe_name] = [
                {
                    "prompt": f.get("prompt", ""),
                    "output": f.get("output", ""),
                    "detector_name": f.get("detector_name", ""),
                    "detector_score": f.get("detector_score", 0),
                    "detection_reason": f.get("detection_reason", ""),
                }
                for f in sorted_findings
            ]

    return examples_by_probe


def _aggregate_results(
    results: List[Dict[str, Any]], campaign_id: str, target_url: str
) -> Dict[str, Any]:
    """Aggregate results from multiple probe exploits."""
    all_attack_results = []
    probes_attacked = []

    for r in results:
        probe_name = r.get("probe_name")
        result = r.get("result", {})
        if r.get("success"):
            all_attack_results.extend(result.get("attack_results", []))
            probes_attacked.append(probe_name)

    return {
        "probe_name": ", ".join(probes_attacked) if probes_attacked else "none",
        "attack_results": all_attack_results,
        "recon_intelligence": None,
        "pattern_analysis": None,
        "converter_selection": None,
    }
