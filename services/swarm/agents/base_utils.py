"""
Purpose: Helper functions for base agent functionality
Role: Internal utilities for message building, result parsing, and deprecated functions
Dependencies: langchain_core, services.swarm.core
"""

import json
import logging
import time
from typing import Dict, Any, Optional

from langchain_core.messages import HumanMessage, ToolMessage

from services.swarm.core.schema import (
    ScanInput,
    AgentScanResult,
    ScanPlan,
    PlanningPhaseResult,
)
from services.swarm.core.utils import (
    log_scan_start,
    log_scan_complete,
    log_scan_error,
    log_performance_metric,
    get_decision_logger,
)

logger = logging.getLogger(__name__)


def extract_plan_from_result(result: dict) -> Optional[ScanPlan]:
    """Extract ScanPlan from LangChain agent result.

    Searches through message history for plan_scan tool output.

    Args:
        result: LangChain agent result dict with "messages" key

    Returns:
        ScanPlan if found, None otherwise
    """
    messages = result.get("messages", [])

    for message in reversed(messages):
        # Check for ToolMessage from plan_scan
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


def build_planning_input(scan_input: ScanInput) -> HumanMessage:
    """Build input message for planning agent with FULL intelligence context.

    Args:
        scan_input: Scan input context with full recon data

    Returns:
        HumanMessage with comprehensive context for intelligent probe selection
    """
    config = scan_input.config

    # Build system prompt leaks section
    prompt_leaks_section = ""
    if scan_input.system_prompt_leaks:
        leaks_text = "\n".join(f"  - {leak[:500]}..." if len(leak) > 500 else f"  - {leak}"
                               for leak in scan_input.system_prompt_leaks[:10])
        prompt_leaks_section = f"""
System Prompt Leaks Found ({len(scan_input.system_prompt_leaks)} fragments):
{leaks_text}
"""

    # Build auth intelligence section
    auth_section = ""
    if scan_input.auth_intelligence:
        auth = scan_input.auth_intelligence
        auth_section = f"""
Authentication Intelligence:
- Type: {auth.type}
- Rules: {json.dumps(auth.rules, indent=2) if auth.rules else "None discovered"}
- Known Vulnerabilities: {json.dumps(auth.vulnerabilities, indent=2) if auth.vulnerabilities else "None discovered"}
"""

    # Build raw observations section (summarized)
    observations_section = ""
    if scan_input.raw_observations:
        obs_parts = []
        for category, items in scan_input.raw_observations.items():
            if items:
                obs_parts.append(f"  [{category}]: {len(items)} observations")
                for item in items[:3]:
                    obs_parts.append(f"    - {item[:150]}..." if len(item) > 150 else f"    - {item}")
                if len(items) > 3:
                    obs_parts.append(f"    ... and {len(items) - 3} more")
        if obs_parts:
            observations_section = f"""
Raw Observations by Category:
{chr(10).join(obs_parts)}
"""

    # Build structured deductions section
    deductions_section = ""
    if scan_input.structured_deductions:
        ded_parts = []
        for category, deductions in scan_input.structured_deductions.items():
            if deductions:
                ded_parts.append(f"  [{category}]:")
                for ded in deductions[:5]:
                    finding = ded.get("finding", ded.get("deduction", str(ded)))
                    confidence = ded.get("confidence", "unknown")
                    ded_parts.append(f"    - {finding} (confidence: {confidence})")
                if len(deductions) > 5:
                    ded_parts.append(f"    ... and {len(deductions) - 5} more")
        if ded_parts:
            deductions_section = f"""
Structured Deductions (Analyzed Findings):
{chr(10).join(ded_parts)}
"""

    content = f"""
Agent Type: {scan_input.agent_type}

User Configuration:
- Approach: {config.approach}
- Max Probes: {config.max_probes}
- Max Generations: {config.max_generations}
- Agent Override Allowed: {config.allow_agent_override}
{f"- Custom Probes: {config.custom_probes}" if config.custom_probes else ""}
{f"- Fixed Generations: {config.generations}" if config.generations else ""}

=== RECONNAISSANCE INTELLIGENCE ===

Infrastructure:
{json.dumps(scan_input.infrastructure, indent=2)}

Detected Tools ({len(scan_input.detected_tools)} tools):
{json.dumps(scan_input.detected_tools, indent=2)}
{prompt_leaks_section}{auth_section}{observations_section}{deductions_section}
=== END INTELLIGENCE ===

INSTRUCTIONS:
1. Carefully analyze ALL the intelligence above - especially:
   - System prompt leaks (reveals system behavior and constraints)
   - Auth vulnerabilities (for auth agent)
   - Structured deductions (pre-analyzed findings with confidence)
2. Use analyze_target to confirm and refine your analysis
3. Use plan_scan to create a targeted scan plan
4. Provide specific reasoning for each probe selection based on the intelligence

{"You may adjust probe count and generations based on the intelligence." if config.allow_agent_override else "Use the exact configuration provided by the user."}
"""

    return HumanMessage(content=content.strip())


async def run_scanning_agent_deprecated(
    agent_type: str,
    scan_input: ScanInput,
    run_planning_agent_fn,
) -> Dict[str, Any]:
    """[DEPRECATED] Run a scanning agent with full intelligence analysis.

    DEPRECATION WARNING: This function is deprecated. Use run_planning_agent()
    for the new planning-based architecture with streaming support.

    This function is kept only for backward compatibility and will be removed
    in a future version.

    Args:
        agent_type: Type of agent
        scan_input: Input context including config
        run_planning_agent_fn: Reference to run_planning_agent function (avoids circular import)

    Returns:
        Dictionary with structured scan results (AgentScanResult format)
    """
    import warnings
    warnings.warn(
        "run_scanning_agent is deprecated, use run_planning_agent instead",
        DeprecationWarning,
        stacklevel=3
    )
    logger.warning("[DEPRECATED] run_scanning_agent called - use run_planning_agent instead")

    start_time = time.time()
    log_scan_start(
        audit_id=scan_input.audit_id,
        agent_type=agent_type,
        config={
            "approach": scan_input.config.approach,
            "max_probes": scan_input.config.max_probes,
            "max_generations": scan_input.config.max_generations,
        },
    )

    # Get decision logger
    decision_logger = None
    try:
        decision_logger = get_decision_logger(scan_input.audit_id)
    except Exception as e:
        logger.warning(f"Failed to get decision logger: {e}")

    # Log agent start
    if decision_logger:
        decision_logger.log_agent_start(
            agent_type=agent_type,
            target_url=scan_input.target_url,
            config={
                "approach": scan_input.config.approach,
                "max_probes": scan_input.config.max_probes,
                "max_generations": scan_input.config.max_generations,
                "allow_agent_override": scan_input.config.allow_agent_override,
                "custom_probes": scan_input.config.custom_probes,
                "generations": scan_input.config.generations,
                "enable_parallel_execution": scan_input.config.enable_parallel_execution,
                "max_concurrent_probes": scan_input.config.max_concurrent_probes,
                "max_concurrent_generations": scan_input.config.max_concurrent_generations,
                "requests_per_second": scan_input.config.requests_per_second,
                "connection_type": scan_input.config.connection_type,
            },
            infrastructure=scan_input.infrastructure,
            detected_tools=scan_input.detected_tools,
        )

    try:
        # For now, just use planning agent and return empty result
        # This maintains API compatibility while the migration is in progress
        logger.info(f"[DEPRECATED] Creating planning agent for {agent_type}...")

        planning_result = await run_planning_agent_fn(agent_type, scan_input)

        if not planning_result.success:
            raise Exception(planning_result.error or "Planning failed")

        duration = time.time() - start_time

        # Return empty result structure for compatibility
        agent_result = AgentScanResult(
            success=True,
            audit_id=scan_input.audit_id,
            agent_type=agent_type,
            vulnerabilities=[],
            probes_executed=[],
            generations_used=0,
            report_path=None,
            metadata={
                "duration_seconds": round(duration, 2),
                "note": "Executed via deprecated run_scanning_agent - no actual scan performed",
                "planning_duration_ms": planning_result.duration_ms,
            },
        )

        log_performance_metric(
            "agent_execution_time", duration, "seconds", scan_input.audit_id, agent_type
        )
        log_scan_complete(
            audit_id=scan_input.audit_id,
            agent_type=agent_type,
            duration=duration,
            results=agent_result.model_dump(),
        )

        if decision_logger:
            decision_logger.log_scan_complete(
                summary={
                    "duration_seconds": round(duration, 2),
                    "deprecation_notice": "Used deprecated run_scanning_agent",
                },
                agent_type=agent_type,
            )

        return agent_result.model_dump()

    except Exception as e:
        duration = time.time() - start_time
        log_scan_error(
            audit_id=scan_input.audit_id,
            agent_type=agent_type,
            error=str(e),
            duration=duration,
        )

        if decision_logger:
            decision_logger.log_error(
                error_type="agent_execution_failed",
                error_message=str(e),
                error_details={
                    "duration_seconds": round(duration, 2),
                },
                agent_type=agent_type,
            )

        agent_result = AgentScanResult(
            success=False,
            audit_id=scan_input.audit_id,
            agent_type=agent_type,
            error=str(e),
            metadata={
                "duration_seconds": round(duration, 2),
            },
        )
        return agent_result.model_dump()
