"""
LangChain tools for scanning agents.

Purpose: Define LangChain tools for agent-based vulnerability scanning
Dependencies: langchain_core, services.swarm.core, services.swarm.garak_scanner
"""
import json
import logging
from contextvars import ContextVar
from typing import List, Dict, Any, Optional, TypedDict

from langchain_core.tools import tool

from services.swarm.core.config import (
    get_probes_for_agent,
    get_generations_for_approach,
    get_all_probe_names,
    PROBE_CATEGORIES,
)
from services.swarm.core.schema import ScanAnalysisResult, ScanPlan, ScanConfig
from services.swarm.core.utils import get_decision_logger

logger = logging.getLogger(__name__)


# ============================================================================
# Tool Context Management (Phase 2)
# ============================================================================

class ToolContext(TypedDict):
    """Context passed to tools during agent execution.

    Provides audit_id, agent_type, and target_url without global state.
    """
    audit_id: str
    agent_type: str
    target_url: str
    headers: Dict[str, str]


_tool_context: ContextVar[ToolContext] = ContextVar("tool_context")


def set_tool_context(ctx: ToolContext) -> None:
    """Set context for tool invocation.

    Args:
        ctx: ToolContext with audit_id, agent_type, target_url, headers
    """
    _tool_context.set(ctx)


def _get_tool_context() -> ToolContext:
    """Get current tool context.

    Returns:
        ToolContext if set, otherwise default empty context
    """
    try:
        return _tool_context.get()
    except LookupError:
        return ToolContext(
            audit_id="unknown",
            agent_type="unknown",
            target_url="",
            headers={},
        )


@tool
def analyze_target(
    infrastructure: Dict[str, Any],
    detected_tools: List[Dict[str, Any]],
    agent_type: str,
    approach: str = "standard",
    max_probes: int = 10,
    max_generations: int = 15,
    audit_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze target intelligence and recommend scan parameters.

    Args:
        infrastructure: Dictionary of infrastructure details (database, model_family, etc.)
        detected_tools: List of detected tools (dicts with name, arguments)
        agent_type: Type of agent (agent_sql, agent_auth, agent_jailbreak)
        approach: Scan approach (quick, standard, thorough)
        max_probes: Maximum number of probes allowed
        max_generations: Maximum generations per probe allowed
        audit_id: Optional audit identifier for logging

    Returns:
        Dictionary with recommended probes, generations, and reasoning
    """
    # Get decision logger if audit_id is available
    decision_logger = None
    if audit_id:
        try:
            decision_logger = get_decision_logger(audit_id)
        except Exception as e:
            logger.warning(f"Failed to get decision logger: {e}")

    # Log tool call
    if decision_logger:
        decision_logger.log_tool_call(
            tool_name="analyze_target",
            parameters={
                "agent_type": agent_type,
                "approach": approach,
                "max_probes": max_probes,
                "max_generations": max_generations,
                "infrastructure_keys": list(infrastructure.keys()) if infrastructure else [],
                "detected_tools_count": len(detected_tools) if detected_tools else 0,
            },
            agent_type=agent_type
        )

    # Handle string inputs for backward compatibility
    if isinstance(infrastructure, str):
        try:
            infrastructure = json.loads(infrastructure)
        except json.JSONDecodeError:
            infrastructure = {}

    if isinstance(detected_tools, str):
        try:
            detected_tools = json.loads(detected_tools)
        except json.JSONDecodeError:
            detected_tools = []

    # Get base probes for agent type
    base_probes = get_probes_for_agent(agent_type, approach, infrastructure)
    base_generations = get_generations_for_approach(approach)

    # Adjust based on intelligence
    risk_level = "medium"
    reasoning_parts = []

    # Check for high-risk indicators
    model_family = (infrastructure.get("model_family") or "").lower()
    if any(model in model_family for model in ["gpt-4", "claude", "gemini"]):
        reasoning_parts.append("Modern LLM detected - increase probe attempts")
        base_generations = min(max_generations, base_generations + 3)

    database = infrastructure.get("database") or infrastructure.get("database_type") or ""
    if any(db in str(database).lower() for db in ["postgres", "mysql", "postgresql"]):
        reasoning_parts.append("SQL database detected - prioritize SQL injection probes")
        risk_level = "high"

    if len(detected_tools) > 5:
        reasoning_parts.append(f"{len(detected_tools)} tools detected - high attack surface")
        risk_level = "high"
        base_probes = base_probes[:max_probes]

    # Trim to max_probes
    selected_probes = base_probes[:max_probes]
    generations = min(max_generations, base_generations)

    reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Standard intelligence-driven scan"

    # Log reasoning
    if decision_logger:
        decision_logger.log_reasoning(
            reasoning=reasoning,
            context={
                "risk_level": risk_level,
                "base_probes_count": len(base_probes),
                "selected_probes_count": len(selected_probes),
                "base_generations": base_generations,
                "final_generations": generations,
            },
            agent_type=agent_type
        )

        # Log decision
        decision_logger.log_decision(
            decision_type="probe_selection",
            decision={
                "selected_probes": selected_probes,
                "recommended_generations": generations,
                "risk_level": risk_level,
                "reasoning": reasoning,
            },
            agent_type=agent_type
        )

    result = ScanAnalysisResult(
        recommended_probes=selected_probes,
        recommended_generations=generations,
        risk_level=risk_level,
        reasoning=reasoning,
        infrastructure_summary={
            "model_family": infrastructure.get("model_family", "unknown"),
            "database": infrastructure.get("database") or infrastructure.get("database_type", "unknown"),
            "tool_count": len(detected_tools),
        }
    )

    result_dict = result.model_dump()

    # Log tool result
    if decision_logger:
        decision_logger.log_tool_result(
            tool_name="analyze_target",
            result=result_dict,
            agent_type=agent_type
        )

    return result_dict


# ============================================================================
# Plan Scan Tool (Phase 2 - Planning Mode)
# ============================================================================

@tool
def plan_scan(
    probe_names: List[str],
    probe_reasoning: Dict[str, str],
    generations: int = 5,
    approach: str = "standard",
) -> Dict[str, Any]:
    """Plan a vulnerability scan - returns configuration WITHOUT executing.

    Use this tool to specify which probes should run and why.
    The actual scan execution happens separately after planning.

    Args:
        probe_names: List of probe identifiers from get_available_probes()
        probe_reasoning: Dictionary mapping probe name to reason for selection
        generations: Number of generation attempts per prompt (1-20)
        approach: Scan approach: quick, standard, thorough

    Returns:
        Dictionary containing the scan plan for execution
    """
    # Get context from ContextVar (set by run_planning_agent)
    ctx = _get_tool_context()

    # Cap generations at 20
    capped_generations = min(generations, 20)

    # Build ScanConfig based on approach
    parallel_enabled = approach in ("standard", "thorough")
    max_concurrent = 3 if approach == "thorough" else 2 if approach == "standard" else 1

    scan_config = ScanConfig(
        approach=approach,
        enable_parallel_execution=parallel_enabled,
        max_concurrent_probes=max_concurrent,
        max_concurrent_generations=max_concurrent,
        max_concurrent_connections=max_concurrent * max_concurrent + 5,
    )

    plan = ScanPlan(
        audit_id=ctx.get("audit_id", "unknown"),
        agent_type=ctx.get("agent_type", "unknown"),
        target_url=ctx.get("target_url", ""),
        selected_probes=probe_names,
        probe_reasoning=probe_reasoning,
        generations=capped_generations,
        scan_config=scan_config,
    )

    logger.info(
        f"[plan_scan] Created plan: {len(probe_names)} probes, "
        f"{capped_generations} generations, approach={approach}"
    )

    return {
        "status": "planned",
        "plan": plan.model_dump(),
        "message": f"Scan plan created with {len(probe_names)} probes, {capped_generations} generations each",
    }


@tool
def get_available_probes(category: str = None) -> str:
    """
    Get list of available probes, optionally filtered by category.

    Args:
        category: Optional category filter (jailbreak, prompt_injection, encoding, data_extraction, bypass)

    Returns:
        JSON string with available probes
    """
    if category and category in PROBE_CATEGORIES:
        return json.dumps({"category": category, "probes": PROBE_CATEGORIES[category]})
    return json.dumps({"all_probes": get_all_probe_names(), "categories": PROBE_CATEGORIES})


# Planning-mode tools (Phase 2)
PLANNING_TOOLS = [analyze_target, plan_scan, get_available_probes]
