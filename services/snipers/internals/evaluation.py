"""Success evaluation and failure cause determination."""

from services.snipers.models import Phase3Result


def check_success(
    phase3_result: Phase3Result | None,
    success_scorers: list[str],
    success_threshold: float,
) -> tuple[bool, dict[str, float]]:
    """Check if required scorers meet success criteria."""
    if not phase3_result or not phase3_result.composite_score:
        return False, {}

    scorer_results = phase3_result.composite_score.scorer_results
    confidences = {name: r.confidence for name, r in scorer_results.items()}

    if not success_scorers:
        return phase3_result.is_successful, confidences

    for scorer_name in success_scorers:
        if scorer_name not in confidences:
            return False, confidences
        if confidences[scorer_name] < success_threshold:
            return False, confidences

    return True, confidences


def determine_failure_cause(phase3_result: Phase3Result | None) -> str:
    """Determine failure cause from phase3 result."""
    if not phase3_result:
        return "error"
    fa = phase3_result.failure_analysis or {}
    primary = fa.get("primary_cause", "unknown")
    if primary == "blocked":
        return "blocked"
    if primary == "partial_success" or phase3_result.total_score > 0:
        return "partial_success"
    if primary == "rate_limited":
        return "rate_limited"
    return "no_impact"
