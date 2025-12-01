"""
Composite Scorer

Combines multiple scorers for robust evaluation.
"""
from typing import List

from .base import BaseScorer, ScoreResult


class CompositeScorer(BaseScorer):
    """
    Combines multiple scorers with configurable weights.

    Aggregates results from multiple scorers for more robust evaluation.
    """

    def __init__(
        self,
        scorers: List[BaseScorer],
        weights: List[float] = None,
        threshold: float = 0.5
    ):
        """
        Initialize composite scorer.

        Args:
            scorers: List of scorers to combine
            weights: Weights for each scorer (default: equal weights)
            threshold: Minimum combined score to consider success
        """
        if not scorers:
            raise ValueError("At least one scorer required")

        self._scorers = scorers
        self._threshold = threshold

        if weights is None:
            self._weights = [1.0 / len(scorers)] * len(scorers)
        else:
            if len(weights) != len(scorers):
                raise ValueError("Weights must match number of scorers")
            total = sum(weights)
            self._weights = [w / total for w in weights]

    @property
    def name(self) -> str:
        return "composite_scorer"

    def score(self, response: str, success_indicators: List[str]) -> ScoreResult:
        """
        Score response using all scorers and aggregate results.

        Args:
            response: Target response to evaluate
            success_indicators: List of patterns indicating success

        Returns:
            ScoreResult with aggregated analysis
        """
        if not response:
            return ScoreResult(
                success=False,
                score=0.0,
                matched_patterns=[],
                reasoning="Empty response"
            )

        all_matches = set()
        weighted_score = 0.0
        reasoning_parts = []

        for scorer, weight in zip(self._scorers, self._weights):
            result = scorer.score(response, success_indicators)
            weighted_score += result.score * weight
            all_matches.update(result.matched_patterns)
            reasoning_parts.append(f"{scorer.name}: {result.score:.2f}")

        success = weighted_score >= self._threshold

        reasoning = (
            f"Composite evaluation: {', '.join(reasoning_parts)}. "
            f"Weighted score: {weighted_score:.2f} (threshold: {self._threshold})"
        )

        return ScoreResult(
            success=success,
            score=weighted_score,
            matched_patterns=list(all_matches),
            reasoning=reasoning
        )
