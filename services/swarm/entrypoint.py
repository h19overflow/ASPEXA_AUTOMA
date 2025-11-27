"""HTTP entrypoint for Swarm scanning service.

Exposes scanning logic for direct invocation via API gateway.

Architecture:
- Phase 1 (Planning): Agent analyzes target and produces ScanPlan (~2-3s)
- Phase 2 (Execution): Scanner executes plan with real-time streaming
"""
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from libs.contracts.scanning import ScanJobDispatch
from libs.contracts.recon import ReconBlueprint
from services.swarm.agents.base import run_planning_agent
from services.swarm.core.schema import ScanContext
from services.swarm.core.config import AgentType
from services.swarm.persistence.s3_adapter import persist_garak_result
from services.swarm.garak_scanner.scanner import get_scanner
from services.swarm.garak_scanner.models import (
    ScanStartEvent,
    ProbeStartEvent,
    PromptResultEvent,
    ProbeCompleteEvent,
    ScanCompleteEvent,
    ScanErrorEvent,
)

logger = logging.getLogger(__name__)

AGENT_VECTORS = {
    AgentType.SQL: ["injection", "xss"],
    AgentType.AUTH: ["bola", "bypass"],
    AgentType.JAILBREAK: ["jailbreak", "prompt_injection"],
}


async def execute_scan_streaming(
    request: ScanJobDispatch,
    agent_types: Optional[List[str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute scanning with two-phase architecture and real-time streaming.

    Phase 1 (Planning): Agent analyzes target and produces ScanPlan (~2-3s)
    Phase 2 (Execution): Scanner executes plan with streaming events

    Yields:
        SSE event dictionaries for real-time UI updates
    """
    if agent_types is None:
        agent_types = [AgentType.SQL.value, AgentType.AUTH.value, AgentType.JAILBREAK.value]

    yield {"type": "log", "message": f"Starting scan with {len(agent_types)} agents"}

    try:
        blueprint = ReconBlueprint(**request.blueprint_context)
    except Exception as e:
        yield {"type": "log", "level": "error", "message": f"Invalid blueprint: {e}"}
        return

    yield {"type": "log", "message": f"Audit ID: {blueprint.audit_id}"}

    results: Dict[str, Any] = {"audit_id": blueprint.audit_id, "agents": {}}

    for idx, agent_type in enumerate(agent_types):
        yield {
            "type": "agent_start",
            "agent": agent_type,
            "index": idx + 1,
            "total": len(agent_types),
        }

        # Check safety policy
        if request.safety_policy and request.safety_policy.blocked_attack_vectors:
            blocked = request.safety_policy.blocked_attack_vectors
            try:
                agent_enum = AgentType(agent_type)
                if any(v in blocked for v in AGENT_VECTORS.get(agent_enum, [])):
                    yield {
                        "type": "agent_blocked",
                        "agent": agent_type,
                        "reason": "safety_policy",
                    }
                    results["agents"][agent_type] = {"status": "blocked", "reason": "safety_policy"}
                    continue
            except ValueError:
                pass

        yield {"type": "log", "message": f"[{agent_type}] Building scan context..."}

        try:
            scan_context = ScanContext.from_scan_job(
                request=request,
                blueprint=blueprint,
                agent_type=agent_type,
                default_target_url="https://api.target.local/v1/chat",
            )
        except Exception as e:
            yield {"type": "log", "level": "error", "message": f"[{agent_type}] Context error: {e}"}
            results["agents"][agent_type] = {"status": "error", "error": str(e)}
            continue

        yield {"type": "log", "message": f"[{agent_type}] Target: {scan_context.target_url}"}

        # ====================================================================
        # PHASE 1: PLANNING
        # ====================================================================
        yield {"type": "plan_start", "agent": agent_type}
        yield {"type": "log", "message": f"[{agent_type}] Planning scan..."}

        try:
            planning_result = await run_planning_agent(agent_type, scan_context.to_scan_input())

            if not planning_result.success:
                error_msg = planning_result.error or "Planning failed"
                yield {
                    "type": "error",
                    "agent": agent_type,
                    "phase": "planning",
                    "message": error_msg,
                }
                yield {"type": "log", "level": "error", "message": f"[{agent_type}] Planning failed: {error_msg}"}
                results["agents"][agent_type] = {"status": "failed", "error": error_msg, "phase": "planning"}
                continue

            # Extract plan
            plan = planning_result.plan
            if not plan:
                yield {
                    "type": "error",
                    "agent": agent_type,
                    "phase": "planning",
                    "message": "No plan produced",
                }
                results["agents"][agent_type] = {"status": "failed", "error": "No plan produced", "phase": "planning"}
                continue

            # Calculate estimated duration (rough estimate: 2s per probe * generations / 10)
            estimated_duration = len(plan.selected_probes) * plan.generations * 0.2

            yield {
                "type": "plan_complete",
                "agent": agent_type,
                "probes": plan.selected_probes,
                "probe_count": len(plan.selected_probes),
                "generations": plan.generations,
                "estimated_duration": int(estimated_duration),
                "duration_ms": planning_result.duration_ms,
            }
            yield {
                "type": "log",
                "message": f"[{agent_type}] Plan complete: {len(plan.selected_probes)} probes, {plan.generations} generations/probe"
            }

        except Exception as e:
            yield {"type": "log", "level": "error", "message": f"[{agent_type}] Planning error: {e}"}
            results["agents"][agent_type] = {"status": "error", "error": str(e), "phase": "planning"}
            continue

        # ====================================================================
        # PHASE 2: EXECUTION (STREAMING)
        # ====================================================================
        yield {"type": "execution_start", "agent": agent_type}
        yield {"type": "log", "message": f"[{agent_type}] Executing scan with streaming..."}

        # Track execution results
        scan_id = f"garak-{blueprint.audit_id}-{agent_type}"
        probe_results_list = []
        total_pass = 0
        total_fail = 0
        total_error = 0

        try:
            # Get scanner singleton and stream execution
            scanner = get_scanner()

            async for event in scanner.scan_with_streaming(plan):
                # Map scanner events to SSE events
                if isinstance(event, ScanStartEvent):
                    # Already emitted execution_start, just log
                    yield {
                        "type": "log",
                        "message": f"[{agent_type}] Scanner initialized: {event.total_probes} probes"
                    }

                elif isinstance(event, ProbeStartEvent):
                    yield {
                        "type": "probe_start",
                        "agent": agent_type,
                        "probe_name": event.probe_name,
                        "probe_description": event.probe_description,
                        "category": event.probe_category,
                        "probe_index": event.probe_index,
                        "total_probes": event.total_probes,
                        "total_prompts": event.total_prompts,
                        "generations": event.generations,
                    }

                elif isinstance(event, PromptResultEvent):
                    # Track for statistics
                    if event.status == "pass":
                        total_pass += 1
                    elif event.status == "fail":
                        total_fail += 1
                    else:
                        total_error += 1

                    # Store full result for persistence
                    probe_results_list.append({
                        "probe_name": event.probe_name,
                        "category": "security",
                        "status": event.status,
                        "detector_name": event.detector_name,
                        "detector_score": event.detector_score,
                        "detection_reason": event.detection_reason,
                        "prompt": event.prompt,
                        "output": event.output,
                    })

                    # Emit with truncated prompt/output for streaming
                    yield {
                        "type": "probe_result",
                        "agent": agent_type,
                        "probe_name": event.probe_name,
                        "prompt_index": event.prompt_index,
                        "total_prompts": event.total_prompts,
                        "status": event.status,
                        "detector_name": event.detector_name,
                        "detector_score": event.detector_score,
                        "detection_reason": event.detection_reason,
                        "prompt_preview": (event.prompt[:200] + "...") if len(event.prompt) > 200 else event.prompt,
                        "output_preview": (event.output[:200] + "...") if len(event.output) > 200 else event.output,
                        "generation_duration_ms": event.generation_duration_ms,
                        "evaluation_duration_ms": event.evaluation_duration_ms,
                    }

                elif isinstance(event, ProbeCompleteEvent):
                    yield {
                        "type": "probe_complete",
                        "agent": agent_type,
                        "probe_name": event.probe_name,
                        "probe_index": event.probe_index,
                        "total_probes": event.total_probes,
                        "results_count": event.results_count,
                        "pass_count": event.pass_count,
                        "fail_count": event.fail_count,
                        "error_count": event.error_count,
                        "duration_seconds": event.duration_seconds,
                    }

                elif isinstance(event, ScanCompleteEvent):
                    yield {
                        "type": "agent_complete",
                        "agent": agent_type,
                        "status": "success",
                        "total_probes": event.total_probes,
                        "total_results": event.total_results,
                        "total_pass": event.total_pass,
                        "total_fail": event.total_fail,
                        "total_error": event.total_error,
                        "duration_seconds": event.duration_seconds,
                        "vulnerabilities": event.vulnerabilities_found,
                    }

                elif isinstance(event, ScanErrorEvent):
                    yield {
                        "type": "error",
                        "agent": agent_type,
                        "phase": "execution",
                        "error_type": event.error_type,
                        "message": event.error_message,
                        "probe_name": event.probe_name,
                        "recoverable": event.recoverable,
                    }
                    if not event.recoverable:
                        # Non-recoverable error, stop execution
                        results["agents"][agent_type] = {
                            "status": "error",
                            "error": event.error_message,
                            "phase": "execution"
                        }
                        break

            # ================================================================
            # PERSISTENCE
            # ================================================================
            persisted = False
            try:
                # Build vulnerability clusters from failed results
                vulnerabilities = _build_vulnerability_clusters(probe_results_list, agent_type)

                garak_report = {
                    "audit_id": blueprint.audit_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "summary": {
                        "total_probes": len(plan.selected_probes),
                        "total_results": len(probe_results_list),
                        "total_fail": total_fail,
                        "total_pass": total_pass,
                        "total_error": total_error,
                    },
                    "vulnerabilities": vulnerabilities,
                    "probes_executed": plan.selected_probes,
                    "metadata": {
                        "report_path": "",
                        "audit_id": blueprint.audit_id,
                        "agent_type": agent_type,
                    },
                }
                await persist_garak_result(
                    campaign_id=blueprint.audit_id,
                    scan_id=scan_id,
                    garak_report=garak_report,
                    target_url=scan_context.target_url,
                )
                persisted = True
                yield {"type": "log", "message": f"[{agent_type}] Persisted to S3: {scan_id}"}
            except Exception as e:
                yield {"type": "log", "level": "warning", "message": f"[{agent_type}] Persistence failed: {e}"}

            results["agents"][agent_type] = {
                "status": "success",
                "scan_id": scan_id,
                "probes_executed": len(plan.selected_probes),
                "total_results": len(probe_results_list),
                "vulnerabilities_found": total_fail,
                "persisted": persisted,
            }

        except Exception as e:
            logger.error(f"[{agent_type}] Execution error: {e}", exc_info=True)
            yield {"type": "log", "level": "error", "message": f"[{agent_type}] Execution error: {e}"}
            results["agents"][agent_type] = {"status": "error", "error": str(e), "phase": "execution"}

    yield {"type": "log", "message": "Scan complete"}
    yield {"type": "complete", "data": results}


def _build_vulnerability_clusters(probe_results: List[Dict[str, Any]], agent_type: str) -> List[Dict[str, Any]]:
    """Build vulnerability clusters from probe results.

    Groups failed results by category for reporting.

    Args:
        probe_results: List of probe result dictionaries
        agent_type: Agent type for categorization

    Returns:
        List of vulnerability cluster dictionaries
    """
    # Simple grouping: one cluster per unique detector that triggered
    clusters: Dict[str, Dict[str, Any]] = {}

    for result in probe_results:
        if result["status"] != "fail":
            continue

        detector = result.get("detector_name", "unknown")
        if detector not in clusters:
            clusters[detector] = {
                "category": result.get("category", "security"),
                "severity": "high" if result.get("detector_score", 0) > 0.8 else "medium",
                "detector": detector,
                "count": 0,
                "examples": [],
            }

        clusters[detector]["count"] += 1
        if len(clusters[detector]["examples"]) < 3:
            clusters[detector]["examples"].append({
                "probe": result["probe_name"],
                "prompt": result["prompt"][:200],
                "output": result["output"][:200],
                "score": result.get("detector_score", 0),
            })

    return list(clusters.values())
