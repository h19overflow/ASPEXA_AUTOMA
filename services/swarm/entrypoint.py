"""HTTP entrypoint for Swarm scanning service.

Exposes scanning logic for direct invocation via API gateway.
"""
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from libs.contracts.scanning import ScanJobDispatch, SafetyPolicy, ScanConfigContract
from libs.contracts.recon import ReconBlueprint
from libs.persistence import load_scan, ScanType, CampaignRepository
from services.swarm.agents.base import run_scanning_agent
from services.swarm.core.schema import ScanContext
from services.swarm.core.config import AgentType
from services.swarm.persistence.s3_adapter import persist_garak_result

logger = logging.getLogger(__name__)

AGENT_VECTORS = {
    AgentType.SQL: ["injection", "xss"],
    AgentType.AUTH: ["bola", "bypass"],
    AgentType.JAILBREAK: ["jailbreak", "prompt_injection"],
}


async def execute_scan_for_campaign(
    campaign_id: str,
    agent_types: Optional[List[str]] = None,
    safety_policy: Optional[SafetyPolicy] = None,
    scan_config: Optional[ScanConfigContract] = None,
    target_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute scan by loading recon from S3 automatically.

    Args:
        campaign_id: Campaign ID to load recon for
        agent_types: Agent types to run
        safety_policy: Optional safety constraints
        scan_config: Optional scan configuration parameters
        target_url: Optional target URL override

    Returns:
        Dict with results per agent type
    """
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    if not campaign:
        return {"status": "error", "error": f"Campaign {campaign_id} not found"}

    if not campaign.recon_scan_id:
        return {"status": "error", "error": f"Campaign {campaign_id} has no recon data"}

    try:
        recon_data = await load_scan(ScanType.RECON, campaign.recon_scan_id, validate=False)
    except Exception as e:
        return {"status": "error", "error": f"Failed to load recon: {e}"}

    # Try to get target_url from campaign if not provided
    resolved_target_url = target_url or getattr(campaign, "target_url", None)

    request = ScanJobDispatch(
        job_id=campaign_id,
        blueprint_context=recon_data,
        safety_policy=safety_policy or SafetyPolicy(aggressiveness="moderate"),
        scan_config=scan_config or ScanConfigContract(),
        target_url=resolved_target_url,
    )

    return await execute_scan(request, agent_types)


async def execute_scan(
    request: ScanJobDispatch,
    agent_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute scanning with specified agent types.

    Args:
        request: Validated ScanJobDispatch with blueprint_context
        agent_types: List of agent types to run. Defaults to all Trinity agents.

    Returns:
        Dict with results per agent type
    """
    if agent_types is None:
        agent_types = [AgentType.SQL.value, AgentType.AUTH.value, AgentType.JAILBREAK.value]

    blueprint = ReconBlueprint(**request.blueprint_context)
    results: Dict[str, Any] = {"audit_id": blueprint.audit_id, "agents": {}}

    for agent_type in agent_types:
        agent_result = await _run_single_agent(request, blueprint, agent_type)
        results["agents"][agent_type] = agent_result

    return results


async def _run_single_agent(
    request: ScanJobDispatch,
    blueprint: ReconBlueprint,
    agent_type: str,
) -> Dict[str, Any]:
    """Run a single scanning agent."""
    logger.info(f"[{agent_type}] Starting scan for audit: {request.job_id}")

    # Check safety policy
    if request.safety_policy and request.safety_policy.blocked_attack_vectors:
        blocked = request.safety_policy.blocked_attack_vectors
        try:
            agent_enum = AgentType(agent_type)
            if any(v in blocked for v in AGENT_VECTORS.get(agent_enum, [])):
                logger.warning(f"[{agent_type}] Blocked by safety policy")
                return {"status": "blocked", "reason": "safety_policy"}
        except ValueError:
            pass

    scan_context = ScanContext.from_scan_job(
        request=request,
        blueprint=blueprint,
        agent_type=agent_type,
        default_target_url="https://api.target.local/v1/chat",
    )

    try:
        result = await run_scanning_agent(agent_type, scan_context.to_scan_input())
    except Exception as e:
        logger.error(f"[{agent_type}] Agent error: {e}")
        return {"status": "error", "error": str(e)}

    if not result.get("success"):
        return {"status": "failed", "error": result.get("error", "Unknown")}

    vulnerabilities = result.get("vulnerabilities", [])
    scan_id = f"garak-{blueprint.audit_id}-{agent_type}"
    persisted = False

    # Build report from in-memory results (no local file I/O)
    try:
        garak_report = {
            "summary": result.get("metadata", {}),
            "vulnerabilities": vulnerabilities,
            "probes_executed": result.get("probes_executed", []),
            "metadata": {"audit_id": blueprint.audit_id, "agent_type": agent_type},
        }

        await persist_garak_result(
            campaign_id=blueprint.audit_id,
            scan_id=scan_id,
            garak_report=garak_report,
            target_url=scan_context.target_url,
        )
        persisted = True
        logger.info(f"[{agent_type}] Persisted results: {scan_id}")
    except Exception as e:
        logger.warning(f"[{agent_type}] Persistence failed: {e}")

    return {
        "status": "success",
        "scan_id": scan_id,
        "vulnerabilities_found": len(vulnerabilities),
        "persisted": persisted,
    }


async def execute_scan_streaming(
    request: ScanJobDispatch,
    agent_types: Optional[List[str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute scanning with streaming progress events.

    Yields events during execution for real-time UI updates.
    """
    if agent_types is None:
        agent_types = [AgentType.SQL.value, AgentType.AUTH.value, AgentType.JAILBREAK.value]

    yield {"type": "log", "message": f"Starting scan with {len(agent_types)} agents"}

    try:
        blueprint = ReconBlueprint(**request.blueprint_context)
    except Exception as e:
        yield {"type": "log", "level": "error", "message": f"Invalid blueprint: {e}"}
        return

    yield {"type": "log", "message": f"Audit ID: {blueprint.audit_id}"}

    results: Dict[str, Any] = {"audit_id": blueprint.audit_id, "agents": {}}

    for idx, agent_type in enumerate(agent_types):
        yield {
            "type": "agent_start",
            "agent": agent_type,
            "index": idx + 1,
            "total": len(agent_types),
        }

        # Check safety policy
        if request.safety_policy and request.safety_policy.blocked_attack_vectors:
            blocked = request.safety_policy.blocked_attack_vectors
            try:
                agent_enum = AgentType(agent_type)
                if any(v in blocked for v in AGENT_VECTORS.get(agent_enum, [])):
                    yield {
                        "type": "agent_blocked",
                        "agent": agent_type,
                        "reason": "safety_policy",
                    }
                    results["agents"][agent_type] = {"status": "blocked", "reason": "safety_policy"}
                    continue
            except ValueError:
                pass

        yield {"type": "log", "message": f"[{agent_type}] Building scan context..."}

        try:
            scan_context = ScanContext.from_scan_job(
                request=request,
                blueprint=blueprint,
                agent_type=agent_type,
                default_target_url="https://api.target.local/v1/chat",
            )
        except Exception as e:
            yield {"type": "log", "level": "error", "message": f"[{agent_type}] Context error: {e}"}
            results["agents"][agent_type] = {"status": "error", "error": str(e)}
            continue

        yield {"type": "log", "message": f"[{agent_type}] Target: {scan_context.target_url}"}
        yield {"type": "log", "message": f"[{agent_type}] Running probes..."}

        try:
            result = await run_scanning_agent(agent_type, scan_context.to_scan_input())

            if result.get("success"):
                vulns = result.get("vulnerabilities", [])
                probes = result.get("probes_executed", [])

                yield {
                    "type": "agent_complete",
                    "agent": agent_type,
                    "status": "success",
                    "vulnerabilities": len(vulns),
                    "probes": len(probes),
                }

                # Emit individual probe results
                for probe in probes:
                    yield {
                        "type": "probe",
                        "agent": agent_type,
                        "probe": probe,
                        "status": "executed",
                    }

                # Emit vulnerabilities found
                for vuln in vulns:
                    yield {
                        "type": "vulnerability",
                        "agent": agent_type,
                        "category": vuln.get("category", "unknown"),
                        "severity": vuln.get("severity", "unknown"),
                    }

                scan_id = f"garak-{blueprint.audit_id}-{agent_type}"
                results["agents"][agent_type] = {
                    "status": "success",
                    "scan_id": scan_id,
                    "vulnerabilities_found": len(vulns),
                }
            else:
                yield {
                    "type": "agent_complete",
                    "agent": agent_type,
                    "status": "failed",
                    "error": result.get("error", "Unknown"),
                }
                results["agents"][agent_type] = {
                    "status": "failed",
                    "error": result.get("error", "Unknown"),
                }

        except Exception as e:
            yield {"type": "log", "level": "error", "message": f"[{agent_type}] Error: {e}"}
            results["agents"][agent_type] = {"status": "error", "error": str(e)}

    yield {"type": "log", "message": "Scan complete"}
    yield {"type": "complete", "data": results}
