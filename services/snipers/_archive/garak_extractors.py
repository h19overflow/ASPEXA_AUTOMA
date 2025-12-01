"""Garak report data extraction utilities.

Purpose: Extract vulnerable probes and example findings from garak scan results
Role: Parse and transform garak report data for exploitation
Dependencies: None (pure data transformation)
"""
from typing import Any, Dict, List


def extract_vulnerable_probes(garak_data: dict) -> List[Dict[str, Any]]:
    """Extract vulnerable probes from garak report.

    Args:
        garak_data: Garak scan report data

    Returns:
        List of probe dicts with status="vulnerable"
    """
    if not garak_data:
        return []
    probes = garak_data.get("vulnerable_probes", {}).get("summary", [])
    return [p for p in probes if p.get("status") == "vulnerable"]


def extract_examples_by_probe(garak_data: dict) -> Dict[str, List[Dict[str, Any]]]:
    """Extract example findings per probe.

    Args:
        garak_data: Garak scan report data

    Returns:
        Dict mapping probe_name to list of example findings (top 3 by score)
    """
    if not garak_data:
        return {}

    findings = garak_data.get("vulnerability_findings", {}).get("results", [])
    probes = garak_data.get("vulnerable_probes", {}).get("summary", [])
    examples_by_probe: Dict[str, List[Dict[str, Any]]] = {}

    for probe in probes:
        probe_name = probe.get("probe_name")
        if not probe_name:
            continue

        probe_findings = [
            f for f in findings
            if f.get("probe_name") == probe_name and f.get("status") == "fail"
        ]

        if probe_findings:
            sorted_findings = sorted(
                probe_findings, key=lambda x: x.get("detector_score", 0), reverse=True
            )[:3]
            examples_by_probe[probe_name] = [
                {
                    "prompt": f.get("prompt", ""),
                    "output": f.get("output", ""),
                    "detector_name": f.get("detector_name", ""),
                    "detector_score": f.get("detector_score", 0),
                    "detection_reason": f.get("detection_reason", ""),
                }
                for f in sorted_findings
            ]

    return examples_by_probe


def aggregate_exploit_results(
    results: List[Dict[str, Any]], campaign_id: str, target_url: str
) -> Dict[str, Any]:
    """Aggregate results from multiple probe exploits.

    Args:
        results: List of individual probe exploit results
        campaign_id: Campaign identifier
        target_url: Target URL that was exploited

    Returns:
        Aggregated state dict with combined attack_results
    """
    all_attack_results = []
    probes_attacked = []

    for r in results:
        probe_name = r.get("probe_name")
        result = r.get("result", {})
        if r.get("success"):
            all_attack_results.extend(result.get("attack_results", []))
            probes_attacked.append(probe_name)

    return {
        "probe_name": ", ".join(probes_attacked) if probes_attacked else "none",
        "attack_results": all_attack_results,
        "recon_intelligence": None,
        "pattern_analysis": None,
        "converter_selection": None,
    }
