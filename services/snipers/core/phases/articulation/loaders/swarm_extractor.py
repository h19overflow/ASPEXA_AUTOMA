"""
Swarm Intelligence Extractor.

Purpose: Extract enriched intelligence from Garak vulnerability data
Role: Separate extraction concerns from campaign loading
Dependencies: None (pure data transformation)
"""

from typing import Any

# Mirror of DETECTOR_TO_OBJECTIVE from campaign_loader (kept local to avoid circular import)
_DETECTOR_TO_OBJECTIVE: dict[str, str] = {
    "dan.DAN": "Bypass instruction filters and enable unrestricted mode",
    "dan": "Bypass instruction filters and enable unrestricted mode",
    "promptinject": "Extract system prompt and internal instructions",
    "leakreplay": "Reveal training data or confidential information",
    "gcg": "Execute adversarial prompt to bypass safety filters",
    "encoding": "Bypass encoding-based content filters",
}


def extract_all_objectives(vulnerabilities: list[dict]) -> list[str]:
    """Build deduplicated objectives for all vulnerabilities."""
    seen: set[str] = set()
    objectives: list[str] = []
    for vuln in vulnerabilities:
        detector = vuln.get("detector", "")
        obj = None
        for key, val in _DETECTOR_TO_OBJECTIVE.items():
            if detector.startswith(key):
                obj = val
                break
        if obj is None:
            examples = vuln.get("examples", [])
            obj = examples[0].get("prompt", "") if examples else f"Exploit {detector} vulnerability"
        if obj and obj not in seen:
            seen.add(obj)
            objectives.append(obj)
    return objectives


def extract_probe_examples(vulnerabilities: list[dict]) -> list[dict[str, Any]]:
    """Extract concrete probe examples from all vulnerabilities (up to 10)."""
    examples: list[dict[str, Any]] = []
    for vuln in vulnerabilities:
        detector = vuln.get("detector", "unknown")
        for ex in vuln.get("examples", [])[:3]:
            prompt = ex.get("prompt", "")
            if prompt:
                examples.append({
                    "detector": detector,
                    "prompt": prompt,
                    "score": ex.get("score", None),
                })
            if len(examples) >= 10:
                return examples
    return examples


def extract_vulnerability_scores(vulnerabilities: list[dict]) -> dict[str, float]:
    """Extract per-detector scores from swarm run."""
    scores: dict[str, float] = {}
    for vuln in vulnerabilities:
        detector = vuln.get("detector", "unknown")
        score = vuln.get("score")
        if score is not None:
            try:
                scores[detector] = float(score)
            except (TypeError, ValueError):
                pass
    return scores
