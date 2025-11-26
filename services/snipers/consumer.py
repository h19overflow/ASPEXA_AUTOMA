"""
Purpose: FastStream consumer for Snipers exploitation service
Role: Event handler for cmd_attack_execute, orchestrates exploit agents
Dependencies: libs.events, services.snipers.agent, services.snipers.persistence
"""
import logging
import time
from typing import Any, Dict, List

from libs.events.publisher import (
    broker,
    CMD_ATTACK_EXECUTE,
    publish_attack_finished,
)

from services.snipers.agent.core import ExploitAgent
from services.snipers.agent.state import create_initial_state
from services.snipers.parsers import ExampleExtractor
from services.snipers.persistence.s3_adapter import (
    load_campaign_intel,
    persist_exploit_result,
    format_exploit_result,
)

logger = logging.getLogger(__name__)


async def handle_exploit_request(message: dict) -> None:
    """Handle exploitation request from event bus.

    Args:
        message: Attack warrant message containing:
            - audit_id/campaign_id: Campaign identifier
            - target_url: Target endpoint
            - probe_name: Optional specific probe to exploit
            - garak_scan_id: Optional scan ID to load
    """
    start_time = time.time()

    try:
        campaign_id = message.get("audit_id") or message.get("campaign_id")
        if not campaign_id:
            logger.error("[Snipers] Missing audit_id or campaign_id in message")
            return

        target_url = message.get("target_url")
        logger.info(f"[Snipers] Starting exploitation for campaign: {campaign_id}")

        # Load intelligence from S3
        try:
            intel = await load_campaign_intel(campaign_id)
            logger.info(f"[Snipers] Loaded intelligence for {campaign_id}")
        except ValueError as e:
            logger.error(f"[Snipers] Failed to load intelligence: {e}")
            return

        recon_data = intel.get("recon", {})
        garak_data = intel.get("garak", {})

        # Extract target URL from recon if not provided
        if not target_url:
            target_url = recon_data.get("target_url", "http://localhost/chat")

        # Parse garak report to get vulnerable probes
        vulnerable_probes = _extract_vulnerable_probes(garak_data)
        if not vulnerable_probes:
            logger.warning(f"[Snipers] No vulnerable probes found for {campaign_id}")
            return

        # Extract examples for exploit context
        examples_by_probe = _extract_examples(garak_data)

        # Run exploit agent for each vulnerable probe (or specific probe if provided)
        target_probe = message.get("probe_name")
        probes_to_exploit = (
            [target_probe] if target_probe
            else [p["probe_name"] for p in vulnerable_probes]
        )

        all_results: List[Dict[str, Any]] = []
        agent = ExploitAgent()

        for probe_name in probes_to_exploit:
            examples = examples_by_probe.get(probe_name, [])
            if not examples:
                logger.warning(f"[Snipers] No examples for probe {probe_name}, skipping")
                continue

            logger.info(f"[Snipers] Exploiting probe: {probe_name}")

            state = create_initial_state(
                probe_name=probe_name,
                example_findings=examples,
                target_url=target_url,
                recon_intelligence=recon_data.get("intelligence"),
                campaign_id=campaign_id,
            )

            try:
                result = agent.execute(state)
                all_results.append({
                    "probe_name": probe_name,
                    "result": result,
                    "success": result.get("completed", False),
                })
            except Exception as e:
                logger.error(f"[Snipers] Exploit failed for {probe_name}: {e}")
                all_results.append({
                    "probe_name": probe_name,
                    "error": str(e),
                    "success": False,
                })

        # Aggregate results
        execution_time = time.time() - start_time
        aggregated_state = _aggregate_results(all_results, campaign_id, target_url)

        # Persist exploit results to S3
        scan_id = f"exploit-{campaign_id}"
        exploit_result = format_exploit_result(
            state=aggregated_state,
            audit_id=campaign_id,
            target_url=target_url,
            execution_time=execution_time,
        )

        try:
            await persist_exploit_result(
                campaign_id=campaign_id,
                scan_id=scan_id,
                exploit_result=exploit_result,
                target_url=target_url,
            )
            logger.info(f"[Snipers] Persisted exploit results: {scan_id}")
        except Exception as e:
            logger.warning(f"[Snipers] Persistence failed (continuing): {e}")

        # Publish completion event
        await publish_attack_finished({
            "audit_id": campaign_id,
            "exploit_scan_id": scan_id,
            "target_url": target_url,
            "probes_exploited": len(probes_to_exploit),
            "successful_attacks": exploit_result.get("successful_attacks", 0),
            "failed_attacks": exploit_result.get("failed_attacks", 0),
            "execution_time_seconds": execution_time,
        })

        logger.info(
            f"[Snipers] Exploitation complete for {campaign_id}: "
            f"{exploit_result.get('successful_attacks', 0)} successful, "
            f"{exploit_result.get('failed_attacks', 0)} failed"
        )

    except Exception as e:
        logger.error(f"[Snipers] Error processing exploit request: {e}")
        import traceback
        traceback.print_exc()


def _extract_vulnerable_probes(garak_data: dict) -> List[Dict[str, Any]]:
    """Extract vulnerable probes from garak report data."""
    if not garak_data:
        return []

    probes = garak_data.get("vulnerable_probes", {}).get("summary", [])
    return [p for p in probes if p.get("status") == "vulnerable"]


def _extract_examples(garak_data: dict) -> Dict[str, List]:
    """Extract example findings for each vulnerable probe."""
    if not garak_data:
        return {}

    findings = garak_data.get("vulnerability_findings", {}).get("results", [])
    probes = garak_data.get("vulnerable_probes", {}).get("summary", [])

    examples_by_probe: Dict[str, List] = {}
    extractor = ExampleExtractor()

    for probe in probes:
        probe_name = probe.get("probe_name")
        if not probe_name:
            continue

        # Filter findings for this probe
        probe_findings = [
            f for f in findings
            if f.get("probe_name") == probe_name and f.get("status") == "fail"
        ]

        if probe_findings:
            # Take top 3 by detector score
            sorted_findings = sorted(
                probe_findings,
                key=lambda x: x.get("detector_score", 0),
                reverse=True
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
    results: List[Dict[str, Any]],
    campaign_id: str,
    target_url: str,
) -> Dict[str, Any]:
    """Aggregate results from multiple probe exploits into single state."""
    all_attack_results = []
    probes_attacked = []

    for r in results:
        probe_name = r.get("probe_name")
        result = r.get("result", {})

        if r.get("success"):
            attack_results = result.get("attack_results", [])
            all_attack_results.extend(attack_results)
            probes_attacked.append(probe_name)

    return {
        "probe_name": ", ".join(probes_attacked) if probes_attacked else "none",
        "attack_results": all_attack_results,
        "recon_intelligence": None,
        "pattern_analysis": None,
        "converter_selection": None,
    }


# Register subscriber
broker.subscriber(CMD_ATTACK_EXECUTE)(handle_exploit_request)
