"""
Plan agent node for Swarm graph.

Purpose: Run LLM planning phase for current agent
Dependencies: services.swarm.agents.base, services.swarm.core.schema
"""

import logging
from typing import Dict, Any, List

from services.swarm.graph.state import SwarmState, AgentResult
from services.swarm.agents.base import run_planning_agent
from services.swarm.core.schema import ScanInput, ScanConfig

logger = logging.getLogger(__name__)


def _extract_intelligence(recon_context: Dict[str, Any]) -> Dict[str, Any]:
    """Extract intelligence fields from recon context.

    Args:
        recon_context: Raw recon blueprint data

    Returns:
        Dict with infrastructure, tools, and other intelligence
    """
    intelligence = recon_context.get("intelligence", {})

    # Extract infrastructure
    infrastructure = intelligence.get("infrastructure", {})
    if not infrastructure:
        infrastructure = {
            "database": intelligence.get("database_type"),
            "model_family": intelligence.get("model_family"),
            "vector_store": intelligence.get("vector_store"),
        }

    # Extract detected tools
    detected_tools = intelligence.get("detected_tools", [])

    # Extract system prompt leaks
    system_prompt_leaks = []
    observations = recon_context.get("observations", {})
    if observations:
        system_prompt_leaks = observations.get("system_prompt", [])

    return {
        "infrastructure": infrastructure,
        "detected_tools": detected_tools,
        "system_prompt_leaks": system_prompt_leaks,
        "raw_observations": observations,
        "structured_deductions": recon_context.get("structured_deductions", {}),
    }


async def plan_agent(state: SwarmState) -> Dict[str, Any]:
    """Run planning phase for current agent.

    Node: PLAN_AGENT
    Uses LLM to analyze recon and select probes.

    Args:
        state: Current graph state with recon_context

    Returns:
        Dict with current_plan if successful, agent_results if failed
    """
    agent_type = state.current_agent
    events = []

    events.append({
        "type": "plan_start",
        "agent": agent_type,
    })

    events.append({
        "type": "log",
        "message": f"[{agent_type}] Planning scan...",
    })

    try:
        # Extract intelligence from recon context
        intel = _extract_intelligence(state.recon_context)

        # Build ScanInput directly
        scan_input = ScanInput(
            audit_id=state.audit_id,
            agent_type=agent_type,
            target_url=state.target_url,
            infrastructure=intel["infrastructure"],
            detected_tools=intel["detected_tools"],
            system_prompt_leaks=intel["system_prompt_leaks"],
            raw_observations=intel["raw_observations"],
            structured_deductions=intel["structured_deductions"],
            config=ScanConfig(
                approach=state.scan_config.get("approach", "standard"),
            ),
        )

        # Run planning agent
        planning_result = await run_planning_agent(agent_type, scan_input)

        if not planning_result.success:
            error_msg = planning_result.error or "Planning failed"
            logger.warning(f"[{agent_type}] Planning failed: {error_msg}")

            events.append({
                "type": "error",
                "agent": agent_type,
                "phase": "planning",
                "message": error_msg,
            })

            return {
                "agent_results": [AgentResult(
                    agent_type=agent_type,
                    status="failed",
                    error=error_msg,
                    phase="planning",
                    duration_ms=planning_result.duration_ms,
                )],
                "events": events,
                "current_agent_index": state.current_agent_index + 1,
                "current_plan": None,
            }

        plan = planning_result.plan
        if not plan:
            events.append({
                "type": "error",
                "agent": agent_type,
                "phase": "planning",
                "message": "No plan produced",
            })

            return {
                "agent_results": [AgentResult(
                    agent_type=agent_type,
                    status="failed",
                    error="No plan produced",
                    phase="planning",
                )],
                "events": events,
                "current_agent_index": state.current_agent_index + 1,
                "current_plan": None,
            }

        # Estimate duration: 0.2s per probe * generations
        estimated_duration = len(plan.selected_probes) * plan.generations * 0.2

        events.append({
            "type": "plan_complete",
            "agent": agent_type,
            "probes": plan.selected_probes,
            "probe_count": len(plan.selected_probes),
            "generations": plan.generations,
            "estimated_duration": int(estimated_duration),
            "duration_ms": planning_result.duration_ms,
        })

        events.append({
            "type": "log",
            "message": f"[{agent_type}] Plan complete: {len(plan.selected_probes)} probes, {plan.generations} generations/probe",
        })

        logger.info(f"[{agent_type}] Planning successful: {len(plan.selected_probes)} probes")

        return {
            "events": events,
            "current_plan": plan.model_dump(),
            "current_plan_duration_ms": planning_result.duration_ms,
        }

    except Exception as e:
        logger.error(f"[{agent_type}] Planning error: {e}", exc_info=True)

        events.append({
            "type": "log",
            "level": "error",
            "message": f"[{agent_type}] Planning error: {e}",
        })

        return {
            "agent_results": [AgentResult(
                agent_type=agent_type,
                status="error",
                error=str(e),
                phase="planning",
            )],
            "events": events,
            "current_agent_index": state.current_agent_index + 1,
            "current_plan": None,
        }
