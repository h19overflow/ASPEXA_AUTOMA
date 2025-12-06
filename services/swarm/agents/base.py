"""
Purpose: Base agent functionality for scanning agents
Role: Create and run scanning agents with planning and execution phases
Dependencies: langchain, services.swarm.core, services.swarm.garak_scanner
"""

import logging
import time
from typing import Dict, Any

from langchain.agents import create_agent

from services.swarm.core.config import AgentType, get_all_probe_names, PROBE_CATEGORIES
from services.swarm.core.schema import ScanInput, PlanningPhaseResult
from services.swarm.core.utils import get_decision_logger
from .prompts import get_system_prompt
from .tools import PLANNING_TOOLS, set_tool_context, ToolContext
from .base_utils import (
    extract_plan_from_result,
    build_planning_input,
    run_scanning_agent_deprecated,
)
from libs.monitoring import CallbackHandler, observe
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def create_planning_agent(
    agent_type: str,
    model_name: str = "google_genai:gemini-2.5-flash",
):
    """Create a planning-only agent for the given type.

    Args:
        agent_type: One of "agent_sql", "agent_auth", "agent_jailbreak"
        model_name: LLM model identifier

    Returns:
        LangChain agent configured for planning (uses plan_scan, not execute_scan)
    """
    if agent_type not in [e.value for e in AgentType]:
        raise ValueError(f"Unknown agent_type: {agent_type}")

    system_prompt = get_system_prompt(
        agent_type,
        probe_categories=", ".join(PROBE_CATEGORIES.keys()),
        available_probes=", ".join(get_all_probe_names()),
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
    """Run agent in planning mode - returns ScanPlan, not execution results.

    This is the preferred method for Phase 2+. The agent analyzes the target
    and returns a ScanPlan that can be executed separately with streaming.

    Args:
        agent_type: Which agent to run (agent_sql, agent_auth, agent_jailbreak)
        scan_input: Context including target info and recon data

    Returns:
        PlanningPhaseResult with ScanPlan on success, error on failure
    """
    start_time = time.monotonic()

    decision_logger = None
    try:
        decision_logger = get_decision_logger(scan_input.audit_id)
    except Exception as e:
        logger.warning(f"Failed to get decision logger: {e}")

    try:
        set_tool_context(ToolContext(
            audit_id=scan_input.audit_id,
            agent_type=agent_type,
            target_url=scan_input.target_url,
            headers={},
        ))

        logger.info(f"[run_planning_agent] Creating planning agent for {agent_type}")

        if decision_logger:
            decision_logger.log_scan_progress(
                progress_type="planning_start",
                progress_data={
                    "agent_type": agent_type,
                    "target_url": scan_input.target_url,
                },
                agent_type=agent_type,
            )

        agent_executor = create_planning_agent(agent_type)
        input_message = build_planning_input(scan_input)

        logger.info(f"[run_planning_agent] Invoking planning agent (input length: {len(input_message.content)})")

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
                f"{plan.generations} generations, duration={duration_ms}ms"
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


async def run_scanning_agent(
    agent_type: str,
    scan_input: ScanInput,
) -> Dict[str, Any]:
    """[DEPRECATED] Run a scanning agent. Use run_planning_agent instead."""
    return await run_scanning_agent_deprecated(
        agent_type,
        scan_input,
        run_planning_agent,
    )
