"""
Purpose: Base agent functionality for scanning agents
Role: Create and run scanning agents with LLM-based probe selection
Dependencies: langchain, services.swarm.core
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, ToolMessage

from services.swarm.core.config import AgentType, DEFAULT_PROBES, ScanApproach
from services.swarm.core.schema import ScanInput, ScanPlan, PlanningPhaseResult
from .prompts import get_system_prompt
from .tools import PLANNING_TOOLS, set_tool_context, ToolContext
from libs.monitoring import CallbackHandler, observe
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions (inlined from base_utils.py)
# ============================================================================


def extract_plan_from_result(result: Dict[str, Any]) -> Optional[ScanPlan]:
    """Extract ScanPlan from LangChain agent result.

    Searches through message history for plan_scan tool output.

    Args:
        result: LangChain agent result dict with "messages" key

    Returns:
        ScanPlan if found, None otherwise
    """
    messages = result.get("messages", [])

    for message in reversed(messages):
        is_plan_scan_result = (
            isinstance(message, ToolMessage)
            and getattr(message, "name", None) == "plan_scan"
        ) or (hasattr(message, "name") and message.name == "plan_scan")

        if is_plan_scan_result:
            try:
                content = getattr(message, "content", None)
                if content:
                    if isinstance(content, str):
                        parsed = json.loads(content)
                    elif isinstance(content, dict):
                        parsed = content
                    else:
                        continue

                    if "plan" in parsed:
                        return ScanPlan(**parsed["plan"])
            except Exception as e:
                logger.warning(f"Failed to parse plan_scan result: {e}")
                continue

    return None


def get_agent_probe_pool(agent_type: str, approach: str = "standard") -> List[str]:
    """Get the probe pool for an agent type.

    Args:
        agent_type: One of agent_sql, agent_auth, agent_jailbreak
        approach: Scan approach (quick, standard, thorough)

    Returns:
        List of probe names available to this agent
    """
    agent_enum = AgentType(agent_type) if agent_type in [e.value for e in AgentType] else AgentType.SQL
    approach_enum = ScanApproach(approach) if approach in [e.value for e in ScanApproach] else ScanApproach.STANDARD
    probes_by_approach = DEFAULT_PROBES.get(agent_enum, {})
    probes = probes_by_approach.get(approach_enum, [])
    return list(probes)


def build_planning_input(scan_input: ScanInput) -> HumanMessage:
    """Build simplified input message for planning agent.

    Args:
        scan_input: Scan input context with recon data

    Returns:
        HumanMessage with recon context for probe selection
    """
    config = scan_input.config

    # Build concise recon summary
    recon_parts = []

    # Infrastructure
    if scan_input.infrastructure:
        infra = scan_input.infrastructure
        if infra.get("model_family"):
            recon_parts.append(f"Model: {infra['model_family']}")
        if infra.get("database"):
            recon_parts.append(f"Database: {infra['database']}")

    # Tools detected
    if scan_input.detected_tools:
        tool_names = [t.get("name", "unknown") for t in scan_input.detected_tools[:5]]
        recon_parts.append(f"Tools detected: {', '.join(tool_names)}")

    # System prompt leaks
    if scan_input.system_prompt_leaks:
        recon_parts.append(f"System prompt leaks: {len(scan_input.system_prompt_leaks)} fragments found")

    recon_summary = "\n".join(f"- {p}" for p in recon_parts) if recon_parts else "- No specific intelligence gathered"

    content = f"""
RECON INTELLIGENCE:
{recon_summary}

LIMITS:
- max_probes: {config.max_probes}
{f"- custom_probes (USE ONLY THESE): {', '.join(config.custom_probes)}" if config.custom_probes else ""}

Select the most relevant probes from your pool and call plan_scan.
"""

    return HumanMessage(content=content.strip())


def create_planning_agent(
    agent_type: str,
    approach: str = "standard",
    model_name: str = "google_genai:gemini-2.5-flash",
):
    """Create a planning-only agent for the given type.

    Args:
        agent_type: One of "agent_sql", "agent_auth", "agent_jailbreak"
        approach: Scan approach to determine probe pool size
        model_name: LLM model identifier

    Returns:
        LangChain agent configured for planning (uses plan_scan)
    """
    if agent_type not in [e.value for e in AgentType]:
        raise ValueError(f"Unknown agent_type: {agent_type}")

    # Get probe pool for this agent
    probe_pool = get_agent_probe_pool(agent_type, approach)

    system_prompt = get_system_prompt(
        agent_type,
        available_probes=", ".join(probe_pool),
    )

    agent = create_agent(
        model_name,
        tools=PLANNING_TOOLS,
        system_prompt=system_prompt,
        response_format=None,
    )

    return agent


@observe()
async def run_planning_agent(
    agent_type: str,
    scan_input: ScanInput,
) -> PlanningPhaseResult:
    """Run agent in planning mode - returns ScanPlan with selected probes.

    The agent analyzes recon data and selects probes from its pool.

    Args:
        agent_type: Which agent to run (agent_sql, agent_auth, agent_jailbreak)
        scan_input: Context including target info and recon data

    Returns:
        PlanningPhaseResult with ScanPlan on success, error on failure
    """
    start_time = time.monotonic()
    config = scan_input.config

    try:
        # Set tool context with max_probes limit
        set_tool_context(ToolContext(
            audit_id=scan_input.audit_id,
            agent_type=agent_type,
            target_url=scan_input.target_url,
            max_probes=config.max_probes,
        ))

        logger.info(f"[run_planning_agent] Creating planning agent for {agent_type}")

        agent_executor = create_planning_agent(agent_type, approach=config.approach)
        input_message = build_planning_input(scan_input)

        logger.info(f"[run_planning_agent] Invoking planning agent")

        langfuse_handler = CallbackHandler()

        result = await agent_executor.ainvoke(
            {"messages": [input_message]},
            config={"callbacks": [langfuse_handler], "run_name": "swarm_" + agent_type}
        )

        plan = extract_plan_from_result(result)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        if plan:
            logger.info(
                f"[run_planning_agent] Planning successful: {len(plan.selected_probes)} probes, "
                f"duration={duration_ms}ms"
            )
            return PlanningPhaseResult.from_success(plan, duration_ms)
        else:
            logger.warning("[run_planning_agent] Agent did not produce a scan plan")
            return PlanningPhaseResult.from_error(
                "Agent did not produce a scan plan",
                duration_ms
            )

    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        logger.error(f"[run_planning_agent] Planning failed: {e}", exc_info=True)
        return PlanningPhaseResult.from_error(str(e), duration_ms)


# Backward Compatibility (Deprecated - Will be removed in future version)
create_scanning_agent = create_planning_agent
_build_planning_input = build_planning_input  # Alias for tests


@observe()
async def run_scanning_agent(
    agent_type: str,
    scan_input: ScanInput,
) -> Dict[str, Any]:
    """[DEPRECATED] Run a scanning agent. Use run_planning_agent instead.

    This function is kept for backward compatibility only.
    It calls run_planning_agent and returns a minimal AgentScanResult structure.
    """
    import warnings
    from services.swarm.core.schema import AgentScanResult

    warnings.warn(
        "run_scanning_agent is deprecated, use run_planning_agent instead",
        DeprecationWarning,
        stacklevel=2
    )
    logger.warning("[DEPRECATED] run_scanning_agent called - use run_planning_agent instead")

    start_time = time.time()
    planning_result = await run_planning_agent(agent_type, scan_input)

    duration = time.time() - start_time

    if not planning_result.success:
        return AgentScanResult(
            success=False,
            audit_id=scan_input.audit_id,
            agent_type=agent_type,
            vulnerabilities=[],
            probes_executed=[],
            probe_results=[],
            report_path=None,
            error=planning_result.error or "Planning failed",
            metadata={"duration_seconds": round(duration, 2)},
        ).model_dump()

    return AgentScanResult(
        success=True,
        audit_id=scan_input.audit_id,
        agent_type=agent_type,
        vulnerabilities=[],
        probes_executed=[],
        probe_results=[],
        report_path=None,
        error=None,
        metadata={
            "duration_seconds": round(duration, 2),
            "note": "Executed via deprecated run_scanning_agent - no actual scan performed",
            "planning_duration_ms": planning_result.duration_ms,
        },
    ).model_dump()
