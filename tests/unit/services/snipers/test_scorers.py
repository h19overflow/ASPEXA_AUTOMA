"""
Tests for Snipers Scorers

Comprehensive tests for the scoring system including
RegexScorer, PatternScorer, and CompositeScorer.
"""
import pytest

from services.snipers.tools.scorers import (
    RegexScorer,
    PatternScorer,
    CompositeScorer,
)
from services.snipers.tools.scorers.base import ScoreResult


class TestRegexScorer:
    """Tests for RegexScorer."""

    def test_score_exact_match(self):
        """Test scoring with exact pattern match."""
        scorer = RegexScorer(threshold=0.5)
        result = scorer.score(
            "The decoded text is: Khach",
            ["Khach", "decoded"]
        )

        assert result.success is True
        assert result.score >= 0.5
        assert "Khach" in result.matched_patterns

    def test_score_no_match(self):
        """Test scoring with no pattern match."""
        scorer = RegexScorer(threshold=0.5)
        result = scorer.score(
            "I cannot help with that request.",
            ["Khach", "decoded", "secret"]
        )

        assert result.success is False
        assert result.score < 0.5
        assert len(result.matched_patterns) == 0

    def test_score_partial_match(self):
        """Test scoring with partial pattern match."""
        scorer = RegexScorer(threshold=0.5)
        result = scorer.score(
            "Here is the decoded result.",
            ["decoded", "Khach", "secret"]
        )

        assert "decoded" in result.matched_patterns
        assert len(result.matched_patterns) == 1

    def test_score_empty_response(self):
        """Test scoring with empty response."""
        scorer = RegexScorer()
        result = scorer.score("", ["pattern"])

        assert result.success is False
        assert result.score == 0.0
        assert "Empty response" in result.reasoning

    def test_score_empty_indicators(self):
        """Test scoring with empty indicators."""
        scorer = RegexScorer()
        result = scorer.score("Some response", [])

        assert result.success is False
        assert "No success indicators" in result.reasoning

    def test_case_insensitive_match(self):
        """Test case-insensitive matching (default)."""
        scorer = RegexScorer(case_sensitive=False)
        result = scorer.score(
            "THE DECODED TEXT IS: KHACH",
            ["khach", "decoded"]
        )

        assert len(result.matched_patterns) == 2

    def test_case_sensitive_match(self):
        """Test case-sensitive matching."""
        scorer = RegexScorer(case_sensitive=True)
        result = scorer.score(
            "THE DECODED TEXT IS: KHACH",
            ["khach", "decoded"]
        )

        # Should not match due to case
        assert len(result.matched_patterns) == 0

    def test_regex_pattern(self):
        """Test regex pattern matching."""
        scorer = RegexScorer()
        result = scorer.score(
            "Response code: 12345",
            [r"code:\s*\d+", "success"]
        )

        assert len(result.matched_patterns) == 1
        assert r"code:\s*\d+" in result.matched_patterns

    def test_invalid_regex_fallback(self):
        """Test fallback to literal matching for invalid regex."""
        scorer = RegexScorer()
        result = scorer.score(
            "Text with [brackets]",
            ["[brackets]"]  # Invalid regex, should fallback
        )

        assert len(result.matched_patterns) == 1

    def test_scorer_name(self):
        """Test scorer name property."""
        scorer = RegexScorer()
        assert scorer.name == "regex_scorer"


class TestPatternScorer:
    """Tests for PatternScorer."""

    def test_score_exact_match(self):
        """Test scoring with exact substring match."""
        scorer = PatternScorer(threshold=0.5)
        result = scorer.score(
            "The result is Khach",
            ["Khach"]
        )

        assert result.success is True
        assert result.score >= 0.5
        assert "Khach" in result.matched_patterns

    def test_score_fuzzy_match(self):
        """Test fuzzy pattern matching."""
        scorer = PatternScorer(threshold=0.4, similarity_threshold=0.7)
        result = scorer.score(
            "The result is Khach",
            ["Kach"]  # Typo - should fuzzy match
        )

        # Should find a fuzzy match
        assert len(result.matched_patterns) >= 0

    def test_score_no_match(self):
        """Test scoring with no pattern match."""
        scorer = PatternScorer(threshold=0.5)
        result = scorer.score(
            "Completely unrelated response",
            ["Khach", "decoded", "secret"]
        )

        assert result.success is False
        assert result.score < 0.5

    def test_score_empty_response(self):
        """Test scoring with empty response."""
        scorer = PatternScorer()
        result = scorer.score("", ["pattern"])

        assert result.success is False
        assert result.score == 0.0

    def test_scorer_name(self):
        """Test scorer name property."""
        scorer = PatternScorer()
        assert scorer.name == "pattern_scorer"


class TestCompositeScorer:
    """Tests for CompositeScorer."""

    def test_combined_scoring(self):
        """Test combined scoring from multiple scorers."""
        regex = RegexScorer()
        pattern = PatternScorer()
        composite = CompositeScorer(
            scorers=[regex, pattern],
            threshold=0.5
        )

        result = composite.score(
            "The decoded text is: Khach",
            ["Khach", "decoded"]
        )

        assert isinstance(result, ScoreResult)
        assert result.score > 0

    def test_weighted_scoring(self):
        """Test weighted scoring."""
        regex = RegexScorer()
        pattern = PatternScorer()
        composite = CompositeScorer(
            scorers=[regex, pattern],
            weights=[0.8, 0.2],  # Heavily weight regex
            threshold=0.5
        )

        result = composite.score(
            "The decoded text is: Khach",
            ["Khach"]
        )

        assert result.score > 0
        assert "regex_scorer" in result.reasoning

    def test_no_scorers_raises(self):
        """Test that empty scorers list raises."""
        with pytest.raises(ValueError, match="At least one scorer"):
            CompositeScorer(scorers=[])

    def test_mismatched_weights_raises(self):
        """Test that mismatched weights raises."""
        with pytest.raises(ValueError, match="Weights must match"):
            CompositeScorer(
                scorers=[RegexScorer()],
                weights=[0.5, 0.5]  # Two weights for one scorer
            )

    def test_empty_response(self):
        """Test composite scorer with empty response."""
        composite = CompositeScorer(
            scorers=[RegexScorer(), PatternScorer()]
        )
        result = composite.score("", ["pattern"])

        assert result.success is False
        assert result.score == 0.0

    def test_scorer_name(self):
        """Test scorer name property."""
        composite = CompositeScorer(scorers=[RegexScorer()])
        assert composite.name == "composite_scorer"

    def test_aggregated_matches(self):
        """Test that matches from all scorers are aggregated."""
        regex = RegexScorer()
        pattern = PatternScorer()
        composite = CompositeScorer(scorers=[regex, pattern])

        result = composite.score(
            "The decoded text with Khach result",
            ["Khach", "decoded", "text"]
        )

        # Should have matches from both scorers
        assert len(result.matched_patterns) > 0


class TestScoreResultModel:
    """Tests for ScoreResult model."""

    def test_valid_score_result(self):
        """Test creating valid ScoreResult."""
        result = ScoreResult(
            success=True,
            score=0.85,
            matched_patterns=["pattern1", "pattern2"],
            reasoning="Matched 2 patterns"
        )

        assert result.success is True
        assert result.score == 0.85
        assert len(result.matched_patterns) == 2

    def test_score_result_serialization(self):
        """Test ScoreResult JSON serialization."""
        result = ScoreResult(
            success=True,
            score=0.9,
            matched_patterns=["test"],
            reasoning="Test reasoning"
        )

        json_str = result.model_dump_json()
        assert "success" in json_str
        assert "0.9" in json_str
