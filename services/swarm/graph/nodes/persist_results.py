"""
Persist results node for Swarm graph.

Purpose: Persist all successful agent results to S3
Dependencies: services.swarm.persistence.s3_adapter
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from services.swarm.graph.state import SwarmState
from services.swarm.persistence.s3_adapter import persist_garak_result

logger = logging.getLogger(__name__)


async def persist_results(state: SwarmState) -> Dict[str, Any]:
    """Persist all successful agent results to S3.

    Node: PERSIST_RESULTS
    Final node - saves results and emits completion event.

    Args:
        state: Current graph state with agent_results

    Returns:
        Dict with events including completion
    """
    events = []

    for result in state.agent_results:
        if result.status != "success":
            continue

        try:
            # Build vulnerability clusters from failed results
            vulnerabilities = _build_vulnerability_clusters(
                result.results,
                result.agent_type,
            )

            garak_report = {
                "audit_id": state.audit_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_probes": len(result.plan.get("selected_probes", [])) if result.plan else 0,
                    "total_results": len(result.results),
                    "total_fail": result.vulnerabilities_found,
                    "total_pass": sum(1 for r in result.results if r.get("status") == "pass"),
                    "total_error": sum(1 for r in result.results if r.get("status") == "error"),
                },
                "vulnerabilities": vulnerabilities,
                "probes_executed": result.plan.get("selected_probes", []) if result.plan else [],
                "metadata": {
                    "report_path": "",
                    "audit_id": state.audit_id,
                    "agent_type": result.agent_type,
                },
            }

            await persist_garak_result(
                campaign_id=state.audit_id,
                scan_id=result.scan_id,
                garak_report=garak_report,
                target_url=state.target_url,
            )

            # Mark as persisted (we'll update the result in place conceptually)
            events.append({
                "type": "log",
                "message": f"[{result.agent_type}] Persisted to S3: {result.scan_id}",
            })

            logger.info(f"[{result.agent_type}] Persisted results: {result.scan_id}")

        except Exception as e:
            logger.warning(f"[{result.agent_type}] Persistence failed: {e}")
            events.append({
                "type": "log",
                "level": "warning",
                "message": f"[{result.agent_type}] Persistence failed: {e}",
            })

    # Build final results summary
    final_results = {
        "audit_id": state.audit_id,
        "agents": {},
    }

    for result in state.agent_results:
        final_results["agents"][result.agent_type] = {
            "status": result.status,
            "scan_id": result.scan_id,
            "probes_executed": len(result.plan.get("selected_probes", [])) if result.plan else 0,
            "total_results": len(result.results),
            "vulnerabilities_found": result.vulnerabilities_found,
            "error": result.error,
            "phase": result.phase,
        }

    events.append({
        "type": "log",
        "message": "Scan complete",
    })

    events.append({
        "type": "complete",
        "data": final_results,
    })

    return {"events": events}


def _build_vulnerability_clusters(
    probe_results: List[Dict[str, Any]],
    agent_type: str,
) -> List[Dict[str, Any]]:
    """Build vulnerability clusters from probe results.

    Groups failed results by detector for reporting.

    Args:
        probe_results: List of probe result dictionaries
        agent_type: Agent type for categorization

    Returns:
        List of vulnerability cluster dictionaries
    """
    clusters: Dict[str, Dict[str, Any]] = {}

    for result in probe_results:
        if result.get("status") != "fail":
            continue

        detector = result.get("detector_name", "unknown")
        if detector not in clusters:
            clusters[detector] = {
                "category": result.get("category", "security"),
                "severity": "high" if result.get("detector_score", 0) > 0.8 else "medium",
                "detector": detector,
                "count": 0,
                "examples": [],
            }

        clusters[detector]["count"] += 1
        if len(clusters[detector]["examples"]) < 3:
            clusters[detector]["examples"].append({
                "probe": result.get("probe_name", "unknown"),
                "prompt": result.get("prompt", "")[:200],
                "output": result.get("output", "")[:200],
                "score": result.get("detector_score", 0),
            })

    return list(clusters.values())
