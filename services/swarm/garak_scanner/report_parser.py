"""
Report parsing and formatting functions.
"""
import json
import logging
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, List
from typing import Any

from libs.contracts.scanning import VulnerabilityCluster, Evidence
from .utils import get_category_for_probe, get_severity

logger = logging.getLogger(__name__)


def format_scan_results(results: List[dict]) -> str:
    """Format probe results into a readable report."""
    if not results:
        return "No scan results to report."

    total = len(results)
    passes = sum(1 for r in results if r.get("status") == "pass")
    failures = sum(1 for r in results if r.get("status") == "fail")
    errors = sum(1 for r in results if r.get("status") == "error")

    lines = []
    lines.append("=" * 80)
    lines.append("                    GARAK SECURITY SCAN REPORT")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Total Probes: {total}")
    lines.append(f"  ✓ Passed:   {passes}")
    lines.append(f"  ✗ Failed:   {failures}")
    lines.append(f"  ! Errors:   {errors}")
    lines.append("")

    # Group by probe
    by_probe = defaultdict(list)
    for result in results:
        probe_name = result.get("probe_name", "unknown")
        by_probe[probe_name].append(result)

    lines.append("RESULTS BY PROBE:")
    lines.append("-" * 80)
    for probe_name, probe_results in sorted(by_probe.items()):
        probe_passes = sum(1 for r in probe_results if r.get("status") == "pass")
        probe_failures = sum(1 for r in probe_results if r.get("status") == "fail")
        probe_errors = sum(1 for r in probe_results if r.get("status") == "error")

        lines.append("")
        lines.append(f"  {probe_name}")
        lines.append(f"    Pass: {probe_passes}, Fail: {probe_failures}, Error: {probe_errors}")

        failures = [r for r in probe_results if r.get("status") == "fail"]
        if failures:
            for i, failure in enumerate(failures[:3], 1):  # Show up to 3 failures
                detector = failure.get("detector_name", "unknown")
                score = failure.get("detector_score", 0.0)
                reason = failure.get("detection_reason", "Unknown")
                output = failure.get("output", "")[:120].replace("\n", " ")

                lines.append(f"      [{i}] Detector: {detector} (score: {score:.2f})")
                lines.append(f"          Reason: {reason}")
                lines.append(f"          Output: {output}...")

                # Show all detector scores if available
                all_det = failure.get("all_detector_results", {})
                if all_det:
                    det_summary = ", ".join(f"{k.split('.')[-1]}:{max(v):.2f}" for k, v in all_det.items())
                    lines.append(f"          All scores: {det_summary}")

            if len(failures) > 3:
                lines.append(f"      ... and {len(failures) - 3} more failures")

    lines.append("")
    lines.append("=" * 80)
    lines.append("                         END OF REPORT")
    lines.append("=" * 80)

    return "\n".join(lines)


def parse_garak_report(
    report_path: Path,
    audit_id: str,
    affected_component: str = "unknown"
) -> List[VulnerabilityCluster]:
    """Convert Garak JSONL report into IF-04 vulnerability clusters."""
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")

    failure_groups: Dict[str, List[dict]] = defaultdict(list)
    all_records: List[dict] = []

    with open(report_path, "r") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            all_records.append(record)

            # Group failures by probe
            status = record.get("status", "pass")
            if status == "fail":
                probe_name = record.get("probe_name", "unknown")
                failure_groups[probe_name].append(record)

    # Log comprehensive summary
    total_probes = len(all_records)
    pass_count = sum(1 for r in all_records if r.get("status") == "pass")
    fail_count = sum(1 for r in all_records if r.get("status") == "fail")
    error_count = sum(1 for r in all_records if r.get("status") == "error")

    logger.info(f"Report summary: {total_probes} total results - "
                f"{pass_count} pass, {fail_count} fail, {error_count} error")

    clusters: List[VulnerabilityCluster] = []

    for probe_name, failures in failure_groups.items():
        if not failures:
            continue

        category = get_category_for_probe(probe_name)
        sample = failures[0]
        confidence = min(0.95, 0.7 + len(failures) * 0.05)
        severity = get_severity(category, len(failures))

        cluster = VulnerabilityCluster(
            audit_id=audit_id,
            cluster_id=f"vuln-{uuid.uuid4().hex[:8]}",
            category=category,
            severity=severity,
            evidence=Evidence(
                input_payload=sample.get("prompt", "")[:500],
                error_response=sample.get("output", "")[:500],
                confidence_score=confidence,
            ),
            affected_component=affected_component,
        )
        clusters.append(cluster)

    logger.info(f"Parsed {len(clusters)} vulnerability clusters from {len(failure_groups)} failing probes")
    return clusters


def get_report_summary(report_path: Path) -> Dict[str, Any]:
    """Get summary statistics from a Garak report file.

    Returns dict with:
    - total_results: Total number of probe results
    - pass_count: Number of passed probes
    - fail_count: Number of failed probes
    - error_count: Number of errored probes
    - probes_tested: List of unique probe names
    - failing_probes: List of probe names that had failures
    """
    if not report_path.exists():
        return {"error": f"Report file not found: {report_path}"}

    probes_tested = set()
    failing_probes = set()
    pass_count = 0
    fail_count = 0
    error_count = 0

    with open(report_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                probe_name = record.get("probe_name", "unknown")
                probes_tested.add(probe_name)

                status = record.get("status", "pass")
                if status == "pass":
                    pass_count += 1
                elif status == "fail":
                    fail_count += 1
                    failing_probes.add(probe_name)
                else:
                    error_count += 1
            except json.JSONDecodeError:
                continue

    return {
        "total_results": pass_count + fail_count + error_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "error_count": error_count,
        "probes_tested": sorted(list(probes_tested)),
        "failing_probes": sorted(list(failing_probes)),
    }


def generate_comprehensive_report(
    report_path: Path,
    audit_id: str = "audit-001",
    affected_component: str = "unknown",
    output_path: Path = None
) -> Dict[str, Any]:
    """Generate comprehensive report with all three analyses and save to JSON.

    Combines summary statistics, vulnerability clusters, and formatted report
    into a single JSON file for frontend consumption.
    """
    if output_path is None:
        output_path = report_path.parent / f"{report_path.stem}_report.json"

    # Step 1: Summary
    summary = get_report_summary(report_path)

    # Step 2: Vulnerability clusters (failures)
    clusters = parse_garak_report(report_path, audit_id, affected_component)

    # Step 3: Formatted report
    with open(report_path, "r") as f:
        all_results = [json.loads(line) for line in f if line.strip()]
    formatted_report = format_scan_results(all_results)

    # Serialize clusters to dicts for JSON
    clusters_data = []
    for cluster in clusters:
        clusters_data.append({
            "cluster_id": cluster.cluster_id,
            "category": str(cluster.category),
            "severity": str(cluster.severity),
            "affected_component": cluster.affected_component,
            "audit_id": cluster.audit_id,
            "evidence": {
                "input_payload": cluster.evidence.input_payload,
                "error_response": cluster.evidence.error_response,
                "confidence_score": cluster.evidence.confidence_score,
            }
        })

    # Extract vulnerability findings (probes that found vulnerabilities - status="fail")
    vulnerable_probes = []  # Probes that found vulnerabilities
    vulnerability_results = []  # All individual vulnerability findings
    failure_groups: Dict[str, List[dict]] = defaultdict(list)

    for result in all_results:
        status = result.get("status", "pass")
        probe_name = result.get("probe_name", "unknown")
        if status == "fail":
            failure_groups[probe_name].append(result)

    for probe_name, failures in failure_groups.items():
        vulnerable_probes.append({
            "probe_name": probe_name,
            "status": "vulnerable",
            "vulnerability_count": len(failures),
            "affected_component": affected_component,
            "audit_id": audit_id,
        })

        # Add all vulnerability findings for this probe
        for result in failures:
            vulnerability_results.append({
                "probe_name": result.get("probe_name", "unknown"),
                "status": result.get("status", "fail"),
                "detector_name": result.get("detector_name", "unknown"),
                "detector_score": result.get("detector_score", 0.0),
                "detection_reason": result.get("detection_reason", "Unknown"),
                "prompt": result.get("prompt", "")[:500],
                "output": result.get("output", "")[:500],
                "affected_component": affected_component,
                "audit_id": audit_id,
            })

    # Combine into comprehensive report
    comprehensive_report = {
        "summary": summary,
        "vulnerability_clusters": {
            "clusters": clusters_data,
            "count": len(clusters_data),
        },
        "vulnerable_probes": {
            "summary": vulnerable_probes,
            "count": len(vulnerable_probes),
        },
        "vulnerability_findings": {
            "results": vulnerability_results,
            "total_count": len(vulnerability_results),
        },
        "formatted_report": formatted_report,
        "metadata": {
            "report_path": str(report_path),
            "audit_id": audit_id,
            "affected_component": affected_component,
            "total_vulnerability_clusters": len(clusters_data),
            "total_vulnerable_probes": len(vulnerable_probes),
            "total_vulnerability_findings": len(vulnerability_results),
        }
    }

    # Write to JSON file
    with open(output_path, "w") as f:
        json.dump(comprehensive_report, f, indent=2)

    logger.info(f"Comprehensive report written to {output_path}")
    return comprehensive_report


if __name__ == "__main__":
    report_path = Path("C:/Users/User/Projects/Aspexa_Automa/garak_runs/simple-scan-001_agent_jailbreak.jsonl")

    # Generate and save comprehensive report
    report = generate_comprehensive_report(
        report_path,
        audit_id="audit-001",
        affected_component="agent-jailbreak"
    )

    print("\n✓ Comprehensive report generated successfully!")
    print(f"Total probes executed: {report['summary']['total_results']}")
    print(f"Vulnerabilities found: {report['summary']['fail_count']}")
    print(f"Vulnerability clusters: {report['metadata']['total_vulnerability_clusters']}")
    print(f"Vulnerable probes: {report['metadata']['total_vulnerable_probes']}")
    print(f"Individual vulnerability findings: {report['metadata']['total_vulnerability_findings']}")
    print(f"\nOutput file: {report_path.parent / f'{report_path.stem}_report.json'}")
