"""
LangChain tools for scanning agents.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

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

    Returns:
        Dictionary with recommended probes, generations, and reasoning
    """
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

    result = ScanAnalysisResult(
        recommended_probes=selected_probes,
        recommended_generations=generations,
        risk_level=risk_level,
        reasoning=" | ".join(reasoning_parts) if reasoning_parts else "Standard intelligence-driven scan",
        infrastructure_summary={
            "model_family": infrastructure.get("model_family", "unknown"),
            "database": infrastructure.get("database") or infrastructure.get("database_type", "unknown"),
            "tool_count": len(detected_tools),
        }
    )

    return result.model_dump()


@tool
def execute_scan(
    target_url: str,
    audit_id: str,
    agent_type: str,
    probes: List[str],
    generations: int = 5,
    approach: str = "standard",
) -> Dict[str, Any]:
    """
    Execute security scan with specified probes.

    Args:
        target_url: HTTP endpoint to test
        audit_id: Unique audit identifier
        agent_type: Type of agent running the scan
        probes: List of probe names to execute
        generations: Number of generations per probe
        approach: Scan approach

    Returns:
        Dictionary with scan results including vulnerabilities and summary statistics
    """
    logger.info(f"execute_scan called: target={target_url}, probes={probes}, generations={generations}")

    # Validate target URL
    if not target_url or not target_url.startswith(("http://", "https://")):
        logger.error(f"Invalid target URL: {target_url}")
        return AgentScanResult(
            success=False,
            audit_id=audit_id,
            agent_type=agent_type,
            error=f"Invalid target URL: {target_url}. Must be http:// or https://"
        ).model_dump()

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
        # Configure scanner
        scanner = get_scanner()
        scanner.configure_http_endpoint(target_url)

        # Run scan with proper event loop handling
        logger.info(f"Executing {len(probe_list)} probes with {generations} generations each")
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

        return result.model_dump()

    except Exception as e:
        logger.error(f"Scan execution failed: {e}", exc_info=True)
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
