"""
Purpose: FastStream consumer for Swarm scanning service (Trinity fan-out)
Role: Event handler for cmd_scan_start, orchestrates agents
Dependencies: libs.events, libs.contracts, services.swarm.agents
"""
import logging

from libs.events.publisher import broker, CMD_SCAN_START
from libs.contracts.scanning import ScanJobDispatch
from libs.contracts.recon import ReconBlueprint

from services.swarm.agents.base import run_scanning_agent
from services.swarm.core.schema import ScanContext
from services.swarm.core.config import AgentType
from services.swarm.persistence.s3_adapter import (
    load_recon_for_campaign,
    persist_garak_result,
)

logger = logging.getLogger(__name__)


async def handle_scan_request(message: dict, agent_type: str):
    """
    Base handler for scan requests. Used by all three Trinity agents.

    Args:
        message: ScanJobDispatch message
        agent_type: Type of agent (agent_sql, agent_auth, agent_jailbreak)
    """
    try:
        request = ScanJobDispatch(**message)
        logger.info(f"[{agent_type}] Starting scan for audit: {request.job_id}")

        # Parse recon blueprint
        blueprint = ReconBlueprint(**request.blueprint_context)

        # Check safety policy compliance
        if request.safety_policy and request.safety_policy.blocked_attack_vectors:
            blocked = request.safety_policy.blocked_attack_vectors
            agent_vectors = {
                AgentType.SQL: ["injection", "xss"],
                AgentType.AUTH: ["bola", "bypass"],
                AgentType.JAILBREAK: ["jailbreak", "prompt_injection"],
            }

            agent_enum = AgentType(agent_type)
            if any(v in blocked for v in agent_vectors.get(agent_enum, [])):
                logger.warning(f"[{agent_type}] Blocked by safety policy. Skipping.")
                return

        # Build unified scan context (replaces all manual extraction)
        scan_context = ScanContext.from_scan_job(
            request=request,
            blueprint=blueprint,
            agent_type=agent_type,
            default_target_url="https://api.target.local/v1/chat"
        )

        # Run scanning agent
        logger.info(f"[{agent_type}] Invoking agent with config: {scan_context.config.approach}")
        result = await run_scanning_agent(agent_type, scan_context.to_scan_input())

        if not result.get("success"):
            logger.error(f"[{agent_type}] Agent failed: {result.get('error', 'Unknown')}")
            return

        logger.info(f"[{agent_type}] Scan completed for audit: {blueprint.audit_id}")

        # Extract structured vulnerabilities from result
        vulnerabilities = result.get("vulnerabilities", [])

        if vulnerabilities:
            logger.info(f"[{agent_type}] Found {len(vulnerabilities)} vulnerabilities")

        # Persist garak results to S3 (no local file I/O)
        try:
            garak_report = {
                "summary": result.get("metadata", {}),
                "vulnerabilities": vulnerabilities,
                "probes_executed": result.get("probes_executed", []),
                "metadata": {
                    "audit_id": blueprint.audit_id,
                    "agent_type": agent_type,
                }
            }

            scan_id = f"garak-{blueprint.audit_id}-{agent_type}"
            await persist_garak_result(
                campaign_id=blueprint.audit_id,
                scan_id=scan_id,
                garak_report=garak_report,
                target_url=scan_context.target_url,
            )
            logger.info(f"[{agent_type}] Persisted garak results to S3: {scan_id}")
        except Exception as e:
            logger.warning(f"[{agent_type}] Persistence failed (continuing): {e}")

    except Exception as e:
        logger.error(f"[{agent_type}] Error: {e}")
        import traceback
        traceback.print_exc()


# Trinity fan-out: Three subscribers with DIFFERENT groups
# Each agent receives and processes the SAME message independently
# Note: FastStream RedisBroker may not support 'group' parameter directly
# Using manual registration as fallback

async def handle_scan_sql(message: dict):
    """SQL injection scanning agent."""
    await handle_scan_request(message, AgentType.SQL.value)


async def handle_scan_auth(message: dict):
    """Authorization scanning agent."""
    await handle_scan_request(message, AgentType.AUTH.value)


async def handle_scan_jailbreak(message: dict):
    """Prompt injection/jailbreak scanning agent."""
    await handle_scan_request(message, AgentType.JAILBREAK.value)


# Register subscribers - try with group parameter, fallback to without
try:
    # Try FastStream's standard subscriber with group
    broker.subscriber(CMD_SCAN_START, group="agent_sql")(handle_scan_sql)
    broker.subscriber(CMD_SCAN_START, group="agent_auth")(handle_scan_auth)
    broker.subscriber(CMD_SCAN_START, group="agent_jailbreak")(handle_scan_jailbreak)
except TypeError:
    # Fallback: register without groups (will need manual group setup)
    broker.subscriber(CMD_SCAN_START)(handle_scan_sql)
    broker.subscriber(CMD_SCAN_START)(handle_scan_auth)
    broker.subscriber(CMD_SCAN_START)(handle_scan_jailbreak)
    logger.warning("FastStream broker doesn't support 'group' parameter. Using default subscriber.")

