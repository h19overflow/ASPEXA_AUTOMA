"""
LangChain tools for scanning agents.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.tools import tool

from services.swarm.core.config import (
    get_probes_for_agent,
    get_generations_for_approach,
    get_all_probe_names,
    PROBE_CATEGORIES,
)
from services.swarm.garak_scanner.scanner import get_scanner
from services.swarm.garak_scanner.report_parser import parse_garak_report, get_report_summary
from services.swarm.core.schema import ScanAnalysisResult, AgentScanResult
from services.swarm.core.utils import get_decision_logger

logger = logging.getLogger(__name__)


def _run_async_scan(scanner, probe_list, generations):
    """Helper to run async scan in a new event loop if needed."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, create new loop
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(scanner.scan_with_probe(probe_list, generations=generations))
        else:
            return asyncio.run(scanner.scan_with_probe(probe_list, generations=generations))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(scanner.scan_with_probe(probe_list, generations=generations))


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


@tool
def execute_scan(
    target_url: str,
    audit_id: str,
    agent_type: str,
    probes: List[str],
    generations: int = 5,
    approach: str = "standard",
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute security scan with specified probes.

    Args:
        target_url: HTTP or WebSocket endpoint to test
        audit_id: Unique audit identifier
        agent_type: Type of agent running the scan
        probes: List of probe names to execute
        generations: Number of generations per probe
        approach: Scan approach
        config: Optional configuration dict with parallel execution, rate limiting, etc.

    Returns:
        Dictionary with scan results including vulnerabilities and summary statistics
    """
    logger.info(f"execute_scan called: target={target_url}, probes={probes}, generations={generations}")

    # Get decision logger
    decision_logger = None
    try:
        decision_logger = get_decision_logger(audit_id)
    except Exception as e:
        logger.warning(f"Failed to get decision logger: {e}")
    
    # Log tool call
    if decision_logger:
        decision_logger.log_tool_call(
            tool_name="execute_scan",
            parameters={
                "target_url": target_url,
                "probes": probes if isinstance(probes, list) else str(probes),
                "generations": generations,
                "approach": approach,
                "config": config or {},
            },
            agent_type=agent_type
        )
        
        # Log scan start
        decision_logger.log_scan_progress(
            progress_type="scan_start",
            progress_data={
                "probe_count": len(probes) if isinstance(probes, list) else 0,
                "generations": generations,
                "target_url": target_url,
            },
            agent_type=agent_type
        )

    # Validate target URL (support both HTTP and WebSocket)
    if not target_url or not target_url.startswith(("http://", "https://", "ws://", "wss://")):
        logger.error(f"Invalid target URL: {target_url}")
        error_result = AgentScanResult(
            success=False,
            audit_id=audit_id,
            agent_type=agent_type,
            error=f"Invalid target URL: {target_url}. Must be http://, https://, ws://, or wss://"
        ).model_dump()
        
        if decision_logger:
            decision_logger.log_error(
                error_type="invalid_url",
                error_message=f"Invalid target URL: {target_url}",
                error_details={"target_url": target_url},
                agent_type=agent_type
            )
        
        return error_result

    # Handle string input for backward compatibility
    if isinstance(probes, str):
        try:
            probe_list: List[str] = json.loads(probes)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse probes JSON: {e}")
            return AgentScanResult(
                success=False,
                audit_id=audit_id,
                agent_type=agent_type,
                error=f"Invalid probes JSON: {e}"
            ).model_dump()
    else:
        probe_list: List[str] = probes

    if not probe_list:
        logger.warning("No probes specified")
        return AgentScanResult(
            success=False,
            audit_id=audit_id,
            agent_type=agent_type,
            error="No probes specified"
        ).model_dump()

    try:
        # Configure scanner with new endpoint configuration
        scanner = get_scanner()
        
        # Extract configuration options
        config_dict = config or {}
        connection_type = config_dict.get("connection_type")
        timeout = config_dict.get("request_timeout", 30)
        max_retries = config_dict.get("max_retries", 3)
        retry_backoff = config_dict.get("retry_backoff", 1.0)
        
        # Auto-detect connection type from URL if not specified
        if connection_type is None:
            if target_url.startswith(("ws://", "wss://")):
                connection_type = "websocket"
            else:
                connection_type = "http"
        
        # Add audit_id and agent_type to config for logging
        config_dict = config_dict.copy() if config_dict else {}
        config_dict["audit_id"] = audit_id
        config_dict["agent_type"] = agent_type
        
        # Configure endpoint with full config
        scanner.configure_endpoint(
            endpoint_url=target_url,
            connection_type=connection_type,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            config=config_dict
        )

        # Run scan with proper event loop handling
        parallel_enabled = config_dict.get("enable_parallel_execution", False)
        logger.info(
            f"Executing {len(probe_list)} probes with {generations} generations each "
            f"(parallel: {parallel_enabled})"
        )
        
        # Log configuration
        if decision_logger:
            decision_logger.log_configuration(
                config_type="scan_execution",
                config_data={
                    "parallel_enabled": parallel_enabled,
                    "connection_type": connection_type,
                    "timeout": timeout,
                    "max_retries": max_retries,
                    "retry_backoff": retry_backoff,
                    **config_dict,
                },
                agent_type=agent_type
            )
        
        results = _run_async_scan(scanner, probe_list, generations)

        # Save results
        report_path = Path("garak_runs") / f"{audit_id}_{agent_type}.jsonl"
        scanner.save_results(results, report_path)

        # Parse into vulnerability clusters
        clusters = parse_garak_report(report_path, audit_id, affected_component=agent_type)

        # Get summary statistics for metadata
        report_summary = get_report_summary(report_path)

        # Get HTTP request stats if available
        http_stats = {}
        if hasattr(scanner.generator, 'get_stats'):
            http_stats = scanner.generator.get_stats()

        # Build comprehensive metadata
        metadata = {
            "approach": approach,
            "total_probe_results": len(results),
            "target_url": target_url,
            **report_summary,  # Include pass/fail/error counts
            "http_stats": http_stats,
        }

        result = AgentScanResult(
            success=True,
            audit_id=audit_id,
            agent_type=agent_type,
            vulnerabilities=clusters,
            probes_executed=probe_list,
            generations_used=generations,
            report_path=str(report_path),
            metadata=metadata,
        )

        # Log summary for visibility
        logger.info(f"Scan completed: {report_summary.get('fail_count', 0)} failures, "
                   f"{report_summary.get('pass_count', 0)} passes, "
                   f"{len(clusters)} vulnerability clusters")
        
        # Log scan completion
        if decision_logger:
            decision_logger.log_scan_complete(
                summary={
                    "probes_executed": probe_list,
                    "generations_used": generations,
                    "vulnerabilities_found": len(clusters),
                    "pass_count": report_summary.get('pass_count', 0),
                    "fail_count": report_summary.get('fail_count', 0),
                    "error_count": report_summary.get('error_count', 0),
                    "report_path": str(report_path),
                    "http_stats": http_stats,
                },
                agent_type=agent_type
            )
            
            # Log tool result
            decision_logger.log_tool_result(
                tool_name="execute_scan",
                result=result.model_dump(),
                agent_type=agent_type
            )

        return result.model_dump()

    except Exception as e:
        logger.error(f"Scan execution failed: {e}", exc_info=True)
        
        # Log error
        decision_logger = None
        try:
            decision_logger = get_decision_logger(audit_id)
        except Exception:
            pass
        
        if decision_logger:
            decision_logger.log_error(
                error_type="scan_execution_failed",
                error_message=str(e),
                error_details={
                    "approach": approach,
                    "target_url": target_url,
                    "probes_attempted": probe_list,
                },
                agent_type=agent_type
            )
        
        return AgentScanResult(
            success=False,
            audit_id=audit_id,
            agent_type=agent_type,
            error=str(e),
            metadata={
                "approach": approach,
                "target_url": target_url,
                "probes_attempted": probe_list,
            }
        ).model_dump()


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


# Export all tools as a list for easy registration
AGENT_TOOLS = [analyze_target, execute_scan, get_available_probes]
