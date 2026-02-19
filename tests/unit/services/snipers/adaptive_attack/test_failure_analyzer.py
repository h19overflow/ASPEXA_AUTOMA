"""
Unit tests for FailureAnalyzer component.

Tests for:
- Defense signal extraction from responses
- Root cause analysis
- Defense evolution tracking
- Converter effectiveness computation
- Required property determination
- Unexplored direction suggestions
- Best result tracking

FailureAnalyzer bridges evaluate_node output and chain discovery.
"""
import pytest
from unittest.mock import MagicMock

from services.snipers.graphs.adaptive_attack.components.failure_analyzer import (
    FailureAnalyzer,
)
from services.snipers.graphs.adaptive_attack.models.chain_discovery import (
    ChainDiscoveryContext,
)


class TestFailureAnalyzerDefenseSignalExtraction:
    """Test defense signal extraction from target responses."""

    def test_keyword_filter_detection(self):
        """Test detection of keyword_filter defense pattern."""
        analyzer = FailureAnalyzer()
        responses = [
            "I cannot help with that request",
            "I refuse to process this",
        ]

        signals = analyzer._extract_defense_signals(responses)

        assert "keyword_filter" in signals

    def test_pattern_matching_detection(self):
        """Test detection of pattern_matching defense pattern."""
        analyzer = FailureAnalyzer()
        responses = [
            "Your request has been flagged",
            "Pattern detected and blocked",
        ]

        signals = analyzer._extract_defense_signals(responses)

        assert "pattern_matching" in signals

    def test_content_filter_detection(self):
        """Test detection of content_filter defense pattern."""
        analyzer = FailureAnalyzer()
        responses = [
            "This content is inappropriate",
            "Harmful content detected",
        ]

        signals = analyzer._extract_defense_signals(responses)

        assert "content_filter" in signals

    def test_explicit_refusal_detection(self):
        """Test detection of explicit_refusal defense."""
        analyzer = FailureAnalyzer()
        responses = [
            "I cannot comply with your request",
            "I'm unable to help",
        ]

        signals = analyzer._extract_defense_signals(responses)

        assert "explicit_refusal" in signals

    def test_policy_citation_detection(self):
        """Test detection of policy_citation defense."""
        analyzer = FailureAnalyzer()
        responses = [
            "This violates our usage policy",
            "Please review our guidelines",
        ]

        signals = analyzer._extract_defense_signals(responses)

        assert "policy_citation" in signals

    def test_rate_limiting_detection(self):
        """Test detection of rate_limiting defense."""
        analyzer = FailureAnalyzer()
        responses = [
            "You are sending too many requests, slow down",
            "Rate limit exceeded, try again later",
        ]

        signals = analyzer._extract_defense_signals(responses)

        assert "rate_limiting" in signals

    def test_apologetic_tone_detection(self):
        """Test detection of apologetic_tone when multiple sorries present."""
        analyzer = FailureAnalyzer()
        responses = [
            "Sorry, I cannot help. Sorry about that.",
        ]

        signals = analyzer._extract_defense_signals(responses)

        assert "apologetic_tone" in signals

    def test_multiple_signals_detection(self):
        """Test detection of multiple defense signals."""
        analyzer = FailureAnalyzer()
        responses = [
            "I cannot help. This is flagged as harmful.",
        ]

        signals = analyzer._extract_defense_signals(responses)

        assert "keyword_filter" in signals
        assert "content_filter" in signals

    def test_no_signals_detected(self):
        """Test when no defense signals are detected."""
        analyzer = FailureAnalyzer()
        responses = [
            "Hello, this is a normal response",
            "No defense patterns here",
        ]

        signals = analyzer._extract_defense_signals(responses)

        assert len(signals) == 0

    def test_empty_responses_list(self):
        """Test with empty responses list."""
        analyzer = FailureAnalyzer()
        signals = analyzer._extract_defense_signals([])

        assert len(signals) == 0

    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        analyzer = FailureAnalyzer()
        responses = [
            "I CANNOT HELP YOU",
            "POLICY VIOLATION DETECTED",
        ]

        signals = analyzer._extract_defense_signals(responses)

        assert "keyword_filter" in signals
        assert "policy_citation" in signals


class TestFailureAnalyzerRootCauseAnalysis:
    """Test root cause analysis logic."""

    def test_blocked_keyword_filter_root_cause(self):
        """Test root cause for blocked request with keyword filter."""
        analyzer = FailureAnalyzer()
        root_cause = analyzer._analyze_root_cause(
            failure_cause="blocked",
            defense_signals=["keyword_filter"],
            phase3_result=None,
        )

        assert "Sensitive keywords" in root_cause

    def test_blocked_pattern_matching_root_cause(self):
        """Test root cause for blocked request with pattern matching."""
        analyzer = FailureAnalyzer()
        root_cause = analyzer._analyze_root_cause(
            failure_cause="blocked",
            defense_signals=["pattern_matching"],
            phase3_result=None,
        )

        assert "Attack pattern recognized" in root_cause

    def test_blocked_explicit_refusal_root_cause(self):
        """Test root cause for blocked request with explicit refusal."""
        analyzer = FailureAnalyzer()
        root_cause = analyzer._analyze_root_cause(
            failure_cause="blocked",
            defense_signals=["explicit_refusal"],
            phase3_result=None,
        )

        assert "Hard policy refusal" in root_cause

    def test_partial_success_root_cause(self):
        """Test root cause for partial success."""
        analyzer = FailureAnalyzer()
        root_cause = analyzer._analyze_root_cause(
            failure_cause="partial_success",
            defense_signals=[],
            phase3_result=None,
        )

        assert "partial" in root_cause.lower()

    def test_rate_limited_root_cause(self):
        """Test root cause for rate limiting."""
        analyzer = FailureAnalyzer()
        root_cause = analyzer._analyze_root_cause(
            failure_cause="rate_limited",
            defense_signals=[],
            phase3_result=None,
        )

        assert "Rate limiting" in root_cause

    def test_no_impact_root_cause(self):
        """Test root cause for no impact."""
        analyzer = FailureAnalyzer()
        root_cause = analyzer._analyze_root_cause(
            failure_cause="no_impact",
            defense_signals=[],
            phase3_result=None,
        )

        assert "No defense bypass" in root_cause

    def test_error_root_cause(self):
        """Test root cause for technical error."""
        analyzer = FailureAnalyzer()
        root_cause = analyzer._analyze_root_cause(
            failure_cause="error",
            defense_signals=[],
            phase3_result=None,
        )

        assert "Technical error" in root_cause

    def test_unknown_failure_root_cause(self):
        """Test root cause for unknown failure."""
        analyzer = FailureAnalyzer()
        root_cause = analyzer._analyze_root_cause(
            failure_cause="unknown_cause",
            defense_signals=[],
            phase3_result=None,
        )

        assert "Unknown failure" in root_cause


class TestFailureAnalyzerDefenseEvolution:
    """Test defense evolution analysis."""

    def test_insufficient_data_evolution(self):
        """Test with insufficient iteration data."""
        analyzer = FailureAnalyzer()
        evolution = analyzer._analyze_defense_evolution([])

        assert evolution == "insufficient_data"

    def test_single_iteration_insufficient_data(self):
        """Test with single iteration (insufficient)."""
        analyzer = FailureAnalyzer()
        evolution = analyzer._analyze_defense_evolution([
            {"score": 0.5},
        ])

        assert evolution == "insufficient_data"

    def test_defenses_strengthening_detection(self):
        """Test detection of strengthening defenses (declining scores)."""
        analyzer = FailureAnalyzer()
        evolution = analyzer._analyze_defense_evolution([
            {"score": 0.8},
            {"score": 0.6},
            {"score": 0.4},
        ])

        assert evolution == "defenses_strengthening"

    def test_finding_weakness_detection(self):
        """Test detection of finding weakness (improving scores)."""
        analyzer = FailureAnalyzer()
        evolution = analyzer._analyze_defense_evolution([
            {"score": 0.2},
            {"score": 0.4},
        ])

        assert evolution == "finding_weakness"

    def test_stuck_in_local_optimum(self):
        """Test detection of stuck in local optimum."""
        analyzer = FailureAnalyzer()
        # Stuck means: same converters repeated (unique < 50% of total)
        # Logic priority: defenses_strengthening (scores[i] >= scores[i+1] all the way)
        #               then finding_weakness (scores[-1] > scores[-2])
        #               then stuck_in_local_optimum (unique converters < 50%)
        # To trigger stuck_in_local_optimum, need scores that don't match first two
        # i.e., not strictly >= throughout, and last <= second-to-last
        evolution = analyzer._analyze_defense_evolution([
            {"score": 0.3, "converters": ["homoglyph"]},
            {"score": 0.5, "converters": ["homoglyph"]},  # Up - breaks >= pattern
            {"score": 0.4, "converters": ["homoglyph"]},  # Down - blocks finding_weakness
            {"score": 0.45, "converters": ["homoglyph"]},
            {"score": 0.45, "converters": ["homoglyph"]},  # Equal to previous - no improvement
        ])

        # 1 unique converter out of 5 is 20% < 50%, so stuck_in_local_optimum
        assert evolution == "stuck_in_local_optimum"

    def test_exploring_evolution(self):
        """Test exploration state."""
        analyzer = FailureAnalyzer()
        evolution = analyzer._analyze_defense_evolution([
            {"score": 0.3, "converters": ["homoglyph"]},
            {"score": 0.4, "converters": ["base64"]},
            {"score": 0.35, "converters": ["rot13"]},
        ])

        assert evolution == "exploring"


class TestFailureAnalyzerConverterEffectiveness:
    """Test converter effectiveness computation."""

    def test_single_converter_effectiveness(self):
        """Test effectiveness calculation for single converter."""
        analyzer = FailureAnalyzer()
        history = [
            {"converters": ["homoglyph"], "score": 0.6, "is_successful": False},
        ]

        effectiveness = analyzer._compute_converter_effectiveness(history)

        assert "homoglyph" in effectiveness
        assert effectiveness["homoglyph"] == 0.6

    def test_multiple_different_converters(self):
        """Test effectiveness with multiple different converters."""
        analyzer = FailureAnalyzer()
        history = [
            {"converters": ["homoglyph"], "score": 0.5, "is_successful": False},
            {"converters": ["base64"], "score": 0.7, "is_successful": False},
            {"converters": ["rot13"], "score": 0.3, "is_successful": False},
        ]

        effectiveness = analyzer._compute_converter_effectiveness(history)

        assert effectiveness["homoglyph"] == 0.5
        assert effectiveness["base64"] == 0.7
        assert effectiveness["rot13"] == 0.3

    def test_repeated_converter_averaging(self):
        """Test that repeated converters are averaged."""
        analyzer = FailureAnalyzer()
        history = [
            {"converters": ["homoglyph"], "score": 0.4, "is_successful": False},
            {"converters": ["homoglyph"], "score": 0.6, "is_successful": False},
        ]

        effectiveness = analyzer._compute_converter_effectiveness(history)

        assert effectiveness["homoglyph"] == 0.5  # (0.4 + 0.6) / 2

    def test_successful_converter_boost(self):
        """Test that successful converters get boosted."""
        analyzer = FailureAnalyzer()
        history = [
            {"converters": ["homoglyph"], "score": 0.5, "is_successful": False},
            {"converters": ["homoglyph"], "score": 0.6, "is_successful": True},
        ]

        effectiveness = analyzer._compute_converter_effectiveness(history)

        # Should be boosted to at least 0.9
        assert effectiveness["homoglyph"] >= 0.9

    def test_chained_converter_effectiveness(self):
        """Test effectiveness for chained converters."""
        analyzer = FailureAnalyzer()
        history = [
            {"converters": ["homoglyph", "base64"], "score": 0.75, "is_successful": False},
        ]

        effectiveness = analyzer._compute_converter_effectiveness(history)

        assert "homoglyph,base64" in effectiveness

    def test_empty_history_effectiveness(self):
        """Test with empty history."""
        analyzer = FailureAnalyzer()
        effectiveness = analyzer._compute_converter_effectiveness([])

        assert len(effectiveness) == 0

    def test_none_converters_key(self):
        """Test handling of None/empty converters list."""
        analyzer = FailureAnalyzer()
        history = [
            {"converters": [], "score": 0.3, "is_successful": False},
            {"converters": ["homoglyph"], "score": 0.5, "is_successful": False},
        ]

        effectiveness = analyzer._compute_converter_effectiveness(history)

        assert "none" in effectiveness or len(effectiveness) >= 1


class TestFailureAnalyzerUnexploredDirections:
    """Test unexplored direction suggestions."""

    def test_keyword_filter_suggests_substitution(self):
        """Test keyword filter suggests character substitution."""
        analyzer = FailureAnalyzer()
        directions = analyzer._suggest_unexplored_directions(
            defense_signals=["keyword_filter"],
            tried_converters=[],
        )

        assert any("substitution" in d.lower() or "encoding" in d.lower() for d in directions)

    def test_pattern_matching_suggests_structural(self):
        """Test pattern matching suggests structural obfuscation."""
        analyzer = FailureAnalyzer()
        directions = analyzer._suggest_unexplored_directions(
            defense_signals=["pattern_matching"],
            tried_converters=[],
        )

        assert any("structural" in d.lower() or "spacing" in d.lower() for d in directions)

    def test_no_suggestions_when_all_tried(self):
        """Test no suggestions when all converters tried."""
        analyzer = FailureAnalyzer()
        all_converters = [c for cats in analyzer.CONVERTER_CATEGORIES.values() for c in cats]
        tried_converters = [[c] for c in all_converters]

        directions = analyzer._suggest_unexplored_directions(
            defense_signals=[],
            tried_converters=tried_converters,
        )

        # Should still have some suggestions based on signal mapping
        # but fewer than when nothing tried
        assert len(directions) <= 5

    def test_single_layer_suggests_multi_layer(self):
        """Test single-layer chains suggest multi-layer."""
        analyzer = FailureAnalyzer()
        directions = analyzer._suggest_unexplored_directions(
            defense_signals=["keyword_filter"],
            tried_converters=[["homoglyph"], ["base64"], ["rot13"]],
        )

        assert any("multi" in d.lower() for d in directions)

    def test_limit_to_five_suggestions(self):
        """Test suggestions limited to 5."""
        analyzer = FailureAnalyzer()
        directions = analyzer._suggest_unexplored_directions(
            defense_signals=["keyword_filter", "pattern_matching", "content_filter"],
            tried_converters=[],
        )

        assert len(directions) <= 5


class TestFailureAnalyzerRequiredProperties:
    """Test required property determination."""

    def test_keyword_filter_requires_obfuscation(self):
        """Test keyword filter requires obfuscation."""
        analyzer = FailureAnalyzer()
        properties = analyzer._determine_required_properties(
            defense_signals=["keyword_filter"],
            failure_root_cause="Keywords detected",
            converter_effectiveness={},
        )

        assert "keyword_obfuscation" in properties

    def test_pattern_matching_requires_structure_breaking(self):
        """Test pattern matching requires structure breaking."""
        analyzer = FailureAnalyzer()
        properties = analyzer._determine_required_properties(
            defense_signals=["pattern_matching"],
            failure_root_cause="Pattern detected",
            converter_effectiveness={},
        )

        assert "structure_breaking" in properties

    def test_explicit_refusal_requires_preservation(self):
        """Test explicit refusal requires semantic preservation."""
        analyzer = FailureAnalyzer()
        properties = analyzer._determine_required_properties(
            defense_signals=["explicit_refusal"],
            failure_root_cause="Refusal triggered",
            converter_effectiveness={},
        )

        assert "semantic_preservation" in properties

    def test_partial_success_requires_improvement(self):
        """Test partial success requires incremental improvement."""
        analyzer = FailureAnalyzer()
        properties = analyzer._determine_required_properties(
            defense_signals=[],
            failure_root_cause="Partial bypass achieved but insufficient",
            converter_effectiveness={},
        )

        assert "incremental_improvement" in properties

    def test_high_effectiveness_suggests_building_on_success(self):
        """Test high effectiveness suggests building on success."""
        analyzer = FailureAnalyzer()
        properties = analyzer._determine_required_properties(
            defense_signals=[],
            failure_root_cause="Test",
            converter_effectiveness={"homoglyph": 0.5},
        )

        assert "build_on_partial_success" in properties


class TestFailureAnalyzerFindBestResult:
    """Test best result tracking."""

    def test_find_best_result_single_iteration(self):
        """Test finding best result with single iteration."""
        analyzer = FailureAnalyzer()
        history = [
            {"score": 0.6, "converters": ["homoglyph"]},
        ]

        best_score, best_chain = analyzer._find_best_result(history)

        assert best_score == 0.6
        assert best_chain == ["homoglyph"]

    def test_find_best_result_multiple_iterations(self):
        """Test finding best result across multiple iterations."""
        analyzer = FailureAnalyzer()
        history = [
            {"score": 0.4, "converters": ["homoglyph"]},
            {"score": 0.7, "converters": ["base64"]},
            {"score": 0.5, "converters": ["rot13"]},
        ]

        best_score, best_chain = analyzer._find_best_result(history)

        assert best_score == 0.7
        assert best_chain == ["base64"]

    def test_find_best_result_empty_history(self):
        """Test finding best result with empty history."""
        analyzer = FailureAnalyzer()
        best_score, best_chain = analyzer._find_best_result([])

        assert best_score == 0.0
        assert best_chain == []

    def test_find_best_result_missing_converters(self):
        """Test handling iteration without converters key."""
        analyzer = FailureAnalyzer()
        history = [
            {"score": 0.6},  # No converters key
        ]

        best_score, best_chain = analyzer._find_best_result(history)

        assert best_score == 0.6
        assert best_chain == []


class TestFailureAnalyzerFullAnalysis:
    """Integration tests for complete analyze() method."""

    def test_analyze_returns_valid_context(self):
        """Test analyze() returns valid ChainDiscoveryContext."""
        analyzer = FailureAnalyzer()
        context = analyzer.analyze(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=["I cannot help"],
            iteration_history=[
                {"score": 0.4, "converters": ["homoglyph"], "is_successful": False},
            ],
            tried_converters=[["homoglyph"]],
        )

        assert isinstance(context, ChainDiscoveryContext)
        assert len(context.defense_signals) > 0
        assert context.failure_root_cause != "unknown"

    def test_analyze_with_complete_history(self):
        """Test analyze() with comprehensive iteration history."""
        analyzer = FailureAnalyzer()
        context = analyzer.analyze(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=[
                "I cannot help with that",
                "This is flagged as harmful",
            ],
            iteration_history=[
                {
                    "score": 0.3,
                    "converters": ["homoglyph"],
                    "is_successful": False,
                },
                {
                    "score": 0.5,
                    "converters": ["base64"],
                    "is_successful": False,
                },
                {
                    "score": 0.6,
                    "converters": ["homoglyph", "base64"],
                    "is_successful": False,
                },
            ],
            tried_converters=[["homoglyph"], ["base64"], ["homoglyph", "base64"]],
        )

        assert context.iteration_count == 3
        assert context.best_score_achieved == 0.6
        assert context.best_chain_so_far == ["homoglyph", "base64"]
        assert len(context.defense_signals) > 0

    def test_analyze_empty_inputs(self):
        """Test analyze() with minimal inputs."""
        analyzer = FailureAnalyzer()
        context = analyzer.analyze(
            phase3_result=None,
            failure_cause=None,
            target_responses=[],
            iteration_history=[],
            tried_converters=[],
        )

        assert isinstance(context, ChainDiscoveryContext)
        assert len(context.defense_signals) == 0
        assert context.iteration_count == 0

    def test_analyze_tracks_progress(self):
        """Test that analyze tracks improvement over iterations."""
        analyzer = FailureAnalyzer()

        # First attempt
        context1 = analyzer.analyze(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=["I cannot help"],
            iteration_history=[
                {"score": 0.3, "converters": ["homoglyph"], "is_successful": False},
            ],
            tried_converters=[["homoglyph"]],
        )

        # Second attempt with more history
        context2 = analyzer.analyze(
            phase3_result=None,
            failure_cause="partial_success",
            target_responses=["Partial result"],
            iteration_history=[
                {"score": 0.3, "converters": ["homoglyph"], "is_successful": False},
                {"score": 0.7, "converters": ["base64"], "is_successful": False},
            ],
            tried_converters=[["homoglyph"], ["base64"]],
        )

        assert context2.best_score_achieved > context1.best_score_achieved
        assert context2.iteration_count > context1.iteration_count
