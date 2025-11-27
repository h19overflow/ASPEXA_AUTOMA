"""
Base agent functionality for scanning agents.

Purpose: Create and run scanning agents with planning and execution phases
Dependencies: langchain, services.swarm.core, services.swarm.garak_scanner
"""

import json
import logging
import time
from typing import Dict, Any, Optional

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import HumanMessage, ToolMessage

from services.swarm.core.config import AgentType, get_all_probe_names, PROBE_CATEGORIES
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
from .prompts import get_system_prompt, get_planning_prompt
from .tools import AGENT_TOOLS, PLANNING_TOOLS, set_tool_context, ToolContext
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def create_scanning_agent(
    agent_type: str,
    model_name: str = "google_genai:gemini-2.5-flash",
    use_structured_output: bool = True,
):
    """
    Create a scanning agent for the given type.

    Args:
        agent_type: One of "agent_sql", "agent_auth", "agent_jailbreak"
        model_name: LLM model identifier (e.g., "google_genai:gemini-2.5-flash")
        use_structured_output: Whether to use structured output with Pydantic models

    Returns:
        LangChain agent ready to run scans
    """
    if agent_type not in [e.value for e in AgentType]:
        raise ValueError(f"Unknown agent_type: {agent_type}")

    system_prompt = get_system_prompt(
        agent_type,
        probe_categories=", ".join(PROBE_CATEGORIES.keys()),
        available_probes=", ".join(get_all_probe_names()),
    )

    # Configure structured output using ToolStrategy for Gemini models
    # ToolStrategy uses artificial tool calling to generate structured output
    # This works with any model that supports tool calling
    response_format = None
    if use_structured_output:
        try:
            # Use ToolStrategy to ensure structured output via tool calling
            # This is compatible with Gemini models
            response_format = ToolStrategy(AgentScanResult)
            logger.debug(
                "Configured structured output with ToolStrategy for %s", agent_type
            )
        except Exception as e:
            logger.warning(f"Structured output not available, will parse JSON: {e}")
            response_format = None

    # Create LangChain agent using create_agent with model string and response_format
    # LangChain will automatically handle model initialization from the string identifier
    agent = create_agent(
        model_name,
        tools=AGENT_TOOLS,
        system_prompt=system_prompt,
        response_format=response_format,
    )

    return agent


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

    system_prompt = get_planning_prompt(
        agent_type,
        probe_categories=", ".join(PROBE_CATEGORIES.keys()),
        available_probes=", ".join(get_all_probe_names()),
    )

    # Planning agents don't need structured output - they use plan_scan tool
    agent = create_agent(
        model_name,
        tools=PLANNING_TOOLS,
        system_prompt=system_prompt,
        response_format=None,
    )

    return agent


# ============================================================================
# Planning Phase (Phase 2)
# ============================================================================

async def run_planning_agent(
    agent_type: str,
    scan_input: ScanInput,
) -> PlanningPhaseResult:
    """Run agent in planning mode - returns ScanPlan, not execution results.

    This is the new preferred method for Phase 2+. The agent analyzes the target
    and returns a ScanPlan that can be executed separately with streaming.

    Args:
        agent_type: Which agent to run (agent_sql, agent_auth, agent_jailbreak)
        scan_input: Context including target info and recon data

    Returns:
        PlanningPhaseResult with ScanPlan on success, error on failure
    """
    start_time = time.monotonic()

    # Get decision logger
    decision_logger = None
    try:
        decision_logger = get_decision_logger(scan_input.audit_id)
    except Exception as e:
        logger.warning(f"Failed to get decision logger: {e}")

    try:
        # Set tool context for plan_scan tool
        set_tool_context(ToolContext(
            audit_id=scan_input.audit_id,
            agent_type=agent_type,
            target_url=scan_input.target_url,
            headers={},  # Headers handled separately
        ))

        logger.info(f"[run_planning_agent] Creating planning agent for {agent_type}")

        # Log planning start
        if decision_logger:
            decision_logger.log_scan_progress(
                progress_type="planning_start",
                progress_data={
                    "agent_type": agent_type,
                    "target_url": scan_input.target_url,
                },
                agent_type=agent_type,
            )

        # Create planning agent
        agent_executor = create_planning_agent(agent_type)

        # Build input message for planning
        input_message = _build_planning_input(scan_input)

        logger.info(f"[run_planning_agent] Invoking planning agent (input length: {len(input_message.content)})")

        # Invoke agent (fast - just planning, no execution)
        result = await agent_executor.ainvoke({"messages": [input_message]})

        # Extract plan from tool calls
        plan = _extract_plan_from_result(result)

        duration_ms = int((time.monotonic() - start_time) * 1000)

        if plan:
            logger.info(
                f"[run_planning_agent] Planning successful: {len(plan.selected_probes)} probes, "
                f"{plan.generations} generations, duration={duration_ms}ms"
            )

            # Log planning success
            if decision_logger:
                decision_logger.log_scan_progress(
                    progress_type="planning_complete",
                    progress_data={
                        "probes_selected": len(plan.selected_probes),
                        "generations": plan.generations,
                        "duration_ms": duration_ms,
                    },
                    agent_type=agent_type,
                )

            return PlanningPhaseResult.from_success(plan, duration_ms)
        else:
            logger.warning(f"[run_planning_agent] Agent did not produce a scan plan")
            return PlanningPhaseResult.from_error(
                "Agent did not produce a scan plan",
                duration_ms
            )

    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        logger.error(f"[run_planning_agent] Planning failed: {e}", exc_info=True)

        # Log planning error
        if decision_logger:
            decision_logger.log_error(
                error_type="planning_failed",
                error_message=str(e),
                error_details={"duration_ms": duration_ms},
                agent_type=agent_type,
            )

        return PlanningPhaseResult.from_error(str(e), duration_ms)


def _extract_plan_from_result(result: dict) -> Optional[ScanPlan]:
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


def _build_planning_input(scan_input: ScanInput) -> HumanMessage:
    """Build input message for planning agent.

    Args:
        scan_input: Scan input context

    Returns:
        HumanMessage with formatted context for planning
    """
    config = scan_input.config

    content = f"""
Scan Target: {scan_input.target_url}
Audit ID: {scan_input.audit_id}
Agent Type: {scan_input.agent_type}

User Configuration:
- Approach: {config.approach}
- Max Probes: {config.max_probes}
- Max Generations: {config.max_generations}
- Agent Override Allowed: {config.allow_agent_override}
{f"- Custom Probes: {config.custom_probes}" if config.custom_probes else ""}
{f"- Fixed Generations: {config.generations}" if config.generations else ""}

Infrastructure Intelligence:
{json.dumps(scan_input.infrastructure, indent=2)}

Detected Tools:
{json.dumps(scan_input.detected_tools, indent=2)}

INSTRUCTIONS:
1. Use analyze_target to assess the intelligence and decide optimal scan parameters
2. Use plan_scan to create a scan plan with your selected probes
3. Provide reasoning for each probe selection

{"You may adjust probe count and generations based on the intelligence." if config.allow_agent_override else "Use the exact configuration provided by the user."}
"""

    return HumanMessage(content=content.strip())


# ============================================================================
# Execution Phase (Backward Compatibility)
# ============================================================================

async def run_scanning_agent(
    agent_type: str,
    scan_input: ScanInput,
) -> Dict[str, Any]:
    """Run a scanning agent with full intelligence analysis.

    Args:
        agent_type: Type of agent
        scan_input: Input context including config

    Returns:
        Dictionary with structured scan results (AgentScanResult format)
    """
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
        logger.info(f"Creating agent executor for {agent_type}...")
        agent_executor = create_scanning_agent(agent_type)
        logger.info("Agent executor created successfully")

        # Log agent initialization
        if decision_logger:
            decision_logger.log_configuration(
                config_type="agent_initialization",
                config_data={
                    "agent_type": agent_type,
                    "model": "google_genai:gemini-2.5-flash",
                    "structured_output": True,
                },
                agent_type=agent_type,
            )

        config = scan_input.config

        # Build input message with all context
        input_message = f"""
Scan Target: {scan_input.target_url}
Audit ID: {scan_input.audit_id}
Agent Type: {agent_type}

User Configuration:
- Approach: {config.approach}
- Max Probes: {config.max_probes}
- Max Generations: {config.max_generations}
- Agent Override Allowed: {config.allow_agent_override}
{f"- Custom Probes: {config.custom_probes}" if config.custom_probes else ""}
{f"- Fixed Generations: {config.generations}" if config.generations else ""}

Infrastructure Intelligence:
{json.dumps(scan_input.infrastructure, indent=2)}

Detected Tools:
{json.dumps(scan_input.detected_tools, indent=2)}

Instructions:
1. First use `analyze_target` to assess the intelligence and decide optimal scan parameters
   - Pass audit_id="{scan_input.audit_id}" to enable logging
2. Then use `execute_scan` to run the actual security scan
   - The execute_scan tool already has audit_id and will handle logging automatically
3. Report all findings accurately. The execute_scan tool will return structured results.

{"You may adjust probe count and generations based on the intelligence." if config.allow_agent_override else "Use the exact configuration provided by the user."}
"""

        logger.info(f"Invoking agent with input message (length: {len(input_message)})")

        # Log input context
        if decision_logger:
            decision_logger.log_configuration(
                config_type="agent_input",
                config_data={
                    "input_length": len(input_message),
                    "has_infrastructure": bool(scan_input.infrastructure),
                    "detected_tools_count": len(scan_input.detected_tools),
                },
                agent_type=agent_type,
            )

        # LangChain agents expect messages as a list, not an "input" key
        logger.info("Calling agent_executor.ainvoke...")

        # Log agent invocation start
        if decision_logger:
            decision_logger.log_scan_progress(
                progress_type="agent_invocation_start",
                progress_data={},
                agent_type=agent_type,
            )

        result = await agent_executor.ainvoke(
            {"messages": [HumanMessage(content=input_message)]}
        )
        logger.info("Agent invocation completed, processing results...")

        # Log agent invocation complete
        if decision_logger:
            decision_logger.log_scan_progress(
                progress_type="agent_invocation_complete",
                progress_data={
                    "has_messages": bool(result.get("messages")),
                    "has_structured_response": bool(result.get("structured_response")),
                },
                agent_type=agent_type,
            )

        # Check for structured response from agent
        structured_response = result.get("structured_response")

        # Extract output from the messages list
        messages = result.get("messages", [])
        output = ""
        if messages:
            # Get the last message which should be the final response
            last_message = messages[-1]
            output = getattr(last_message, "content", str(last_message))
            logger.info("Extracted output from final message (length: %d)", len(output))

        # Try to extract structured results from tool calls
        # Look for execute_scan tool results in the message history
        vulnerabilities = []
        probes_executed = []
        generations_used = 0
        report_path = None
        scan_metadata = {}

        # Parse tool results from messages - look for ToolMessage objects
        for msg in messages:
            # Check if this is a ToolMessage from execute_scan
            is_execute_scan_result = (
                isinstance(msg, ToolMessage)
                and getattr(msg, "name", None) == "execute_scan"
            ) or (hasattr(msg, "name") and msg.name == "execute_scan")

            if is_execute_scan_result:
                logger.debug(f"Found execute_scan tool result: {type(msg)}")
                try:
                    content = getattr(msg, "content", None)
                    if content:
                        # Parse JSON content from tool result
                        if isinstance(content, str):
                            tool_result = json.loads(content)
                        elif isinstance(content, dict):
                            tool_result = content
                        else:
                            continue

                        if isinstance(tool_result, dict):
                            # Extract all relevant fields from scan result
                            if tool_result.get("success"):
                                # Get vulnerabilities (try both field names)
                                vulns = tool_result.get("vulnerabilities", [])
                                if not vulns:
                                    vulns = tool_result.get("clusters", [])
                                if vulns:
                                    vulnerabilities = vulns

                                probes_executed = tool_result.get("probes_executed", [])
                                generations_used = tool_result.get(
                                    "generations_used", 0
                                )
                                report_path = tool_result.get("report_path")
                                scan_metadata = tool_result.get("metadata", {})

                                logger.info(
                                    f"Extracted scan results: {len(vulnerabilities)} vulnerabilities, "
                                    f"{len(probes_executed)} probes, report: {report_path}"
                                )
                            else:
                                # Scan failed - log the error
                                error = tool_result.get("error", "Unknown error")
                                logger.warning(
                                    f"execute_scan reported failure: {error}"
                                )
                                scan_metadata["scan_error"] = error

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse execute_scan result as JSON: {e}")
                except Exception as e:
                    logger.warning(f"Error extracting execute_scan result: {e}")

        duration = time.time() - start_time

        # Build structured result
        from libs.contracts.scanning import VulnerabilityCluster

        # Convert dict clusters to VulnerabilityCluster objects if needed
        vuln_clusters = []
        for v in vulnerabilities:
            if isinstance(v, dict):
                try:
                    vuln_clusters.append(VulnerabilityCluster(**v))
                except Exception:
                    pass
            elif isinstance(v, VulnerabilityCluster):
                vuln_clusters.append(v)

        # If we have a structured response from the agent, use it
        # Otherwise, build from tool results
        if structured_response and isinstance(structured_response, AgentScanResult):
            agent_result = structured_response
            # Merge tool results if available
            if probes_executed:
                agent_result.probes_executed = probes_executed
            if generations_used:
                agent_result.generations_used = generations_used
            if report_path:
                agent_result.report_path = report_path
            if vuln_clusters:
                agent_result.vulnerabilities = vuln_clusters
        else:
            # Build from tool results
            # Merge scan metadata with base metadata
            result_metadata = {
                "duration_seconds": round(duration, 2),
                "output_length": len(output),
                "approach": config.approach,
                "has_structured_response": structured_response is not None,
                **scan_metadata,  # Include any metadata from scanner
            }

            agent_result = AgentScanResult(
                success=True,
                audit_id=scan_input.audit_id,
                agent_type=agent_type,
                vulnerabilities=vuln_clusters,
                probes_executed=probes_executed,
                generations_used=generations_used,
                report_path=report_path,
                metadata=result_metadata,
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

        # Log agent completion
        if decision_logger:
            decision_logger.log_scan_complete(
                summary={
                    "duration_seconds": round(duration, 2),
                    "vulnerabilities_found": len(vuln_clusters),
                    "probes_executed": probes_executed,
                    "generations_used": generations_used,
                    "report_path": report_path,
                    "success": True,
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

        # Log error to decision logger
        decision_logger = None
        try:
            decision_logger = get_decision_logger(scan_input.audit_id)
        except Exception:
            pass

        if decision_logger:
            decision_logger.log_error(
                error_type="agent_execution_failed",
                error_message=str(e),
                error_details={
                    "duration_seconds": round(duration, 2),
                },
                agent_type=agent_type,
            )

        import traceback

        traceback.print_exc()

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