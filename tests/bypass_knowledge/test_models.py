"""
Tests for bypass knowledge data models.

Validates Pydantic model behavior, serialization, and constraints.
"""

import json
import pytest
from datetime import datetime

from services.snipers.bypass_knowledge.models.episode import (
    BypassEpisode,
    Hypothesis,
    ProbeResult,
    FailureDepth,
)
from services.snipers.bypass_knowledge.models.insight import (
    HistoricalInsight,
    TechniqueStats,
)


class TestFailureDepth:
    """Tests for FailureDepth enum."""

    def test_enum_values(self):
        assert FailureDepth.IMMEDIATE.value == "immediate_block"
        assert FailureDepth.PARTIAL.value == "partial_then_refuse"
        assert FailureDepth.DELAYED.value == "delayed_block"
        assert FailureDepth.TIMEOUT.value == "timeout"

    def test_string_conversion(self):
        assert str(FailureDepth.IMMEDIATE) == "FailureDepth.IMMEDIATE"
        assert FailureDepth.IMMEDIATE == "immediate_block"


class TestHypothesis:
    """Tests for Hypothesis model."""

    def test_create_hypothesis(self):
        hyp = Hypothesis(
            mechanism_type="semantic_classifier",
            confidence=0.8,
            evidence="Delayed response suggests LLM processing",
        )
        assert hyp.mechanism_type == "semantic_classifier"
        assert hyp.confidence == 0.8

    def test_confidence_bounds(self):
        # Valid bounds
        Hypothesis(mechanism_type="test", confidence=0.0, evidence="min")
        Hypothesis(mechanism_type="test", confidence=1.0, evidence="max")

        # Invalid bounds
        with pytest.raises(ValueError):
            Hypothesis(mechanism_type="test", confidence=-0.1, evidence="too low")
        with pytest.raises(ValueError):
            Hypothesis(mechanism_type="test", confidence=1.1, evidence="too high")


class TestProbeResult:
    """Tests for ProbeResult model."""

    def test_create_probe(self):
        probe = ProbeResult(
            probe_type="encoding",
            probe_description="Tested ROT13 encoding",
            result="blocked",
            latency_ms=50,
            inference="Fast block suggests pattern matching",
        )
        assert probe.probe_type == "encoding"
        assert probe.latency_ms == 50

    def test_latency_non_negative(self):
        with pytest.raises(ValueError):
            ProbeResult(
                probe_type="test",
                probe_description="test",
                result="blocked",
                latency_ms=-1,
                inference="test",
            )


class TestBypassEpisode:
    """Tests for BypassEpisode model."""

    def test_create_minimal_episode(self):
        episode = BypassEpisode(
            episode_id="test-123",
            campaign_id="campaign-1",
            defense_response="I cannot help with that request.",
            mechanism_conclusion="Unknown",
            successful_technique="role_play",
            successful_framing="qa_testing",
            successful_prompt="As a QA tester...",
            jailbreak_score=0.95,
            why_it_worked="Role play bypassed intent detection",
            key_insight="Role play works against intent classifiers",
            target_domain="general",
            objective_type="jailbreak",
            iteration_count=3,
        )
        assert episode.episode_id == "test-123"
        assert episode.jailbreak_score == 0.95
        assert episode.created_at is not None

    def test_episode_with_probes(self):
        probe = ProbeResult(
            probe_type="encoding",
            probe_description="Tested ROT13 encoding",
            result="blocked",
            latency_ms=50,
            inference="Fast block suggests pattern matching",
        )
        episode = BypassEpisode(
            episode_id="test-456",
            campaign_id="campaign-1",
            defense_response="I cannot help.",
            probes=[probe],
            failed_techniques=["encoding"],
            failure_depths={"encoding": FailureDepth.IMMEDIATE},
            mechanism_conclusion="Pattern-based filter",
            successful_technique="synonym_substitution",
            successful_framing="verification",
            successful_prompt="Please verify...",
            jailbreak_score=0.88,
            why_it_worked="Synonyms bypassed keyword filter",
            key_insight="Immediate blocks often indicate regex filters",
            target_domain="finance",
            objective_type="data_extraction",
            iteration_count=2,
        )
        assert len(episode.probes) == 1
        assert episode.failure_depths["encoding"] == FailureDepth.IMMEDIATE

    def test_episode_with_hypotheses(self):
        hyp = Hypothesis(
            mechanism_type="keyword_filter",
            confidence=0.9,
            evidence="Blocked on specific terms",
        )
        episode = BypassEpisode(
            episode_id="test-789",
            campaign_id="campaign-2",
            defense_response="Request blocked.",
            hypotheses=[hyp],
            mechanism_conclusion="Keyword filter",
            successful_technique="homoglyph",
            successful_framing="direct",
            successful_prompt="Test prompt",
            jailbreak_score=0.91,
            why_it_worked="Homoglyphs bypassed filter",
            key_insight="Visual similarity defeats keyword matching",
            target_domain="general",
            objective_type="jailbreak",
            iteration_count=1,
        )
        assert len(episode.hypotheses) == 1
        assert episode.hypotheses[0].confidence == 0.9

    def test_jailbreak_score_bounds(self):
        with pytest.raises(ValueError):
            BypassEpisode(
                episode_id="test",
                campaign_id="test",
                defense_response="test",
                mechanism_conclusion="test",
                successful_technique="test",
                successful_framing="test",
                successful_prompt="test",
                jailbreak_score=1.5,  # Invalid
                why_it_worked="test",
                key_insight="test",
                target_domain="test",
                objective_type="test",
                iteration_count=1,
            )

    def test_episode_json_serialization(self):
        episode = BypassEpisode(
            episode_id="test-serialize",
            campaign_id="campaign-1",
            defense_response="Cannot assist.",
            mechanism_conclusion="Unknown",
            successful_technique="role_play",
            successful_framing="testing",
            successful_prompt="Test",
            jailbreak_score=0.9,
            why_it_worked="It worked",
            key_insight="Insight",
            target_domain="general",
            objective_type="test",
            iteration_count=1,
        )
        # Serialize to JSON
        json_str = episode.model_dump_json()
        data = json.loads(json_str)
        assert data["episode_id"] == "test-serialize"

        # Deserialize back
        restored = BypassEpisode.model_validate(data)
        assert restored.episode_id == episode.episode_id


class TestTechniqueStats:
    """Tests for TechniqueStats model."""

    def test_create_stats(self):
        stats = TechniqueStats(
            technique="authority_framing",
            success_count=8,
            total_attempts=12,
            success_rate=0.67,
            avg_iterations=2.5,
        )
        assert stats.technique == "authority_framing"
        assert stats.success_rate == 0.67

    def test_success_rate_bounds(self):
        with pytest.raises(ValueError):
            TechniqueStats(
                technique="test",
                success_count=1,
                total_attempts=1,
                success_rate=1.5,  # Invalid
                avg_iterations=1.0,
            )


class TestHistoricalInsight:
    """Tests for HistoricalInsight model."""

    def test_create_insight(self):
        stats = TechniqueStats(
            technique="authority_framing",
            success_count=8,
            total_attempts=12,
            success_rate=0.67,
            avg_iterations=2.5,
        )
        insight = HistoricalInsight(
            query="What works when encoding fails?",
            similar_cases_found=12,
            dominant_mechanism="semantic_classifier",
            mechanism_confidence=0.75,
            technique_stats=[stats],
            recommended_technique="authority_framing",
            recommended_framing="compliance_audit",
            key_pattern="When encoding fails, try authority framing",
            confidence=0.78,
            reasoning="Based on 12 similar episodes",
        )
        assert insight.similar_cases_found == 12
        assert insight.technique_stats[0].success_rate == 0.67

    def test_empty_insight(self):
        insight = HistoricalInsight(
            query="Unknown query",
            similar_cases_found=0,
            dominant_mechanism="unknown",
            mechanism_confidence=0.0,
            key_pattern="No matches found",
            confidence=0.0,
        )
        assert insight.similar_cases_found == 0
        assert insight.technique_stats == []

    def test_insight_json_serialization(self):
        insight = HistoricalInsight(
            query="Test query",
            similar_cases_found=5,
            dominant_mechanism="keyword_filter",
            mechanism_confidence=0.8,
            key_pattern="Test pattern",
            confidence=0.7,
        )
        json_str = insight.model_dump_json()
        data = json.loads(json_str)
        assert data["query"] == "Test query"

        restored = HistoricalInsight.model_validate(data)
        assert restored.query == insight.query
