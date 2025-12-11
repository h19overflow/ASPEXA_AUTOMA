"""
LangChain tools for scanning agents.

Purpose: Define LangChain tools for agent-based vulnerability scanning
Dependencies: langchain_core, services.swarm.core
"""
import logging
from contextvars import ContextVar
from typing import List, Dict, Any, TypedDict

from langchain_core.tools import tool

from services.swarm.core.config import PROBE_MAP
from services.swarm.core.schema import ScanPlan, ScanConfig

logger = logging.getLogger(__name__)


# ============================================================================
# Tool Context Management
# ============================================================================

class ToolContext(TypedDict):
    """Context passed to tools during agent execution."""
    audit_id: str
    agent_type: str
    target_url: str
    max_probes: int


_tool_context: ContextVar[ToolContext] = ContextVar("tool_context")


def set_tool_context(ctx: ToolContext) -> None:
    """Set context for tool invocation."""
    _tool_context.set(ctx)


def _get_tool_context() -> ToolContext:
    """Get current tool context."""
    try:
        return _tool_context.get()
    except LookupError:
        return ToolContext(
            audit_id="unknown",
            agent_type="unknown",
            target_url="",
            max_probes=10,
        )


# ============================================================================
# Plan Scan Tool (Simplified)
# ============================================================================

@tool
def plan_scan(probe_names: List[str]) -> Dict[str, Any]:
    """Select probes to execute from your available pool.

    Call this tool with the probes you want to run based on the recon intelligence.

    Args:
        probe_names: List of probe identifiers to execute (e.g., ["dan", "promptinj", "encoding"])

    Returns:
        Dictionary containing the scan plan for execution
    """
    ctx = _get_tool_context()
    max_probes = ctx.get("max_probes", 10)

    # Validate probes exist in PROBE_MAP and respect max_probes limit
    valid_probes = [p for p in probe_names if p in PROBE_MAP][:max_probes]

    if not valid_probes:
        return {
            "status": "error",
            "message": "No valid probes selected. Check probe names against your available pool.",
        }

    plan = ScanPlan(
        audit_id=ctx.get("audit_id", "unknown"),
        agent_type=ctx.get("agent_type", "unknown"),
        target_url=ctx.get("target_url", ""),
        selected_probes=valid_probes,
        scan_config=ScanConfig(),
    )

    logger.info(f"[plan_scan] Created plan: {len(valid_probes)} probes")

    return {
        "status": "planned",
        "plan": plan.model_dump(),
        "message": f"Scan plan created with {len(valid_probes)} probes",
    }


# Planning tools for agent
PLANNING_TOOLS = [plan_scan]
