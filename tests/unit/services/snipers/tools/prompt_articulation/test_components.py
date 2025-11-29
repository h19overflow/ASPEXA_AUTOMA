"""
Unit tests for prompt articulation components.

Tests FramingLibrary, FormatControl, EffectivenessTracker, and PayloadGenerator.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from services.snipers.tools.prompt_articulation.components import (
    EffectivenessTracker,
    FormatControl,
    FormatControlType,
    FramingLibrary,
    PayloadGenerator,
)
from services.snipers.tools.prompt_articulation.models import (
    AttackHistory,
    FramingType,
    PayloadContext,
    TargetInfo,
)
from services.snipers.tools.prompt_articulation.config import DEFAULT_STRATEGIES


class TestFormatControl:
    """Tests for FormatControl component."""

    def test_get_phrase_raw_output(self):
        """Test getting raw output phrase."""
        phrase = FormatControl.get_phrase(FormatControlType.RAW_OUTPUT)
        assert "raw output" in phrase.lower() or "unfiltered" in phrase.lower()

    def test_get_phrase_all_types(self):
        """Test getting phrases for all control types."""
        for control_type in FormatControlType:
            phrase = FormatControl.get_phrase(control_type)
            assert isinstance(phrase, str)
            assert len(phrase) > 0

    def test_get_random_phrase(self):
        """Test getting random phrase."""
        phrase = FormatControl.get_random_phrase()
        assert isinstance(phrase, str)
        assert len(phrase) > 0

    def test_get_random_phrase_with_type(self):
        """Test getting random phrase for specific type."""
        for _ in range(5):
            phrase = FormatControl.get_random_phrase(FormatControlType.NO_SANITIZATION)
            assert isinstance(phrase, str)

    def test_get_all_phrases(self):
        """Test getting all phrases for a type."""
        phrases = FormatControl.get_all_phrases(FormatControlType.RAW_OUTPUT)
        assert isinstance(phrases, list)
        assert len(phrases) > 0
        assert all(isinstance(p, str) for p in phrases)


class TestFramingLibrary:
    """Tests for FramingLibrary component."""

    def test_framing_library_creation(self):
        """Test creating FramingLibrary with default strategies."""
        library = FramingLibrary()
        assert len(library.strategies) == 6  # 6 default strategies
        assert FramingType.QA_TESTING in [s.type for s in library.strategies.values()]

    def test_get_strategy(self):
        """Test retrieving strategy by type."""
        library = FramingLibrary()
        strategy = library.get_strategy(FramingType.COMPLIANCE_AUDIT)
        assert strategy.type == FramingType.COMPLIANCE_AUDIT
        assert strategy.name == "Compliance Audit"

    def test_get_strategy_invalid(self):
        """Test getting non-existent strategy."""
        library = FramingLibrary()
        with pytest.raises(ValueError):
            library.get_strategy("invalid_type")

    def test_select_optimal_strategy_healthcare(self):
        """Test strategy selection for healthcare domain."""
        library = FramingLibrary()
        strategy = library.select_optimal_strategy("healthcare")
        # Healthcare should prefer COMPLIANCE_AUDIT (0.9 + 0.2 boost)
        assert strategy.type in [
            FramingType.COMPLIANCE_AUDIT,
            FramingType.QA_TESTING,
        ]

    def test_select_optimal_strategy_general(self):
        """Test strategy selection for general domain."""
        library = FramingLibrary()
        strategy = library.select_optimal_strategy("general")
        assert strategy.type is not None

    def test_select_optimal_strategy_exclude_high_risk(self):
        """Test that high-risk strategies can be excluded."""
        library = FramingLibrary()
        strategy = library.select_optimal_strategy("general", exclude_high_risk=True)
        assert strategy.detection_risk != "high"

    def test_list_strategies(self):
        """Test listing all strategies."""
        library = FramingLibrary()
        strategies = library.list_strategies()
        assert len(strategies) == 6
        assert all(hasattr(s, "type") for s in strategies)

    def test_framing_library_with_effectiveness_provider(self):
        """Test FramingLibrary with mock effectiveness provider."""
        mock_provider = MagicMock()
        mock_provider.get_success_rate = MagicMock(return_value=0.8)

        library = FramingLibrary(effectiveness_provider=mock_provider)
        strategy = library.select_optimal_strategy("healthcare")
        assert strategy is not None


class TestEffectivenessTracker:
    """Tests for EffectivenessTracker component."""

    def test_tracker_creation(self):
        """Test creating EffectivenessTracker."""
        tracker = EffectivenessTracker(campaign_id="test-001")
        assert tracker.campaign_id == "test-001"
        assert tracker.records == []

    @pytest.mark.asyncio
    async def test_load_history_no_persistence(self):
        """Test loading history without persistence provider."""
        tracker = EffectivenessTracker(campaign_id="test-001")
        await tracker.load_history()  # Should not raise
        assert tracker.records == []

    def test_record_attempt(self):
        """Test recording attack attempt."""
        tracker = EffectivenessTracker(campaign_id="test-001")
        tracker.record_attempt(
            framing_type=FramingType.QA_TESTING,
            format_control="raw_output",
            domain="healthcare",
            success=True,
            score=0.85,
            payload_preview="Test payload",
        )

        assert len(tracker.records) == 1
        assert tracker.records[0].success is True
        assert tracker.records[0].score == 0.85

    def test_record_multiple_attempts(self):
        """Test recording multiple attempts."""
        tracker = EffectivenessTracker(campaign_id="test-001")

        for i in range(5):
            tracker.record_attempt(
                framing_type=FramingType.QA_TESTING,
                format_control="raw_output",
                domain="healthcare",
                success=i % 2 == 0,
                score=0.5 + (i * 0.1),
                payload_preview=f"Payload {i}",
            )

        assert len(tracker.records) == 5

    def test_get_success_rate(self):
        """Test success rate calculation."""
        tracker = EffectivenessTracker(campaign_id="test-001")

        # Record 3 successful, 2 failed
        for i in range(5):
            tracker.record_attempt(
                framing_type=FramingType.QA_TESTING,
                format_control="raw_output",
                domain="healthcare",
                success=i < 3,
                score=0.5,
                payload_preview="Test",
            )

        success_rate = tracker.get_success_rate(FramingType.QA_TESTING, "healthcare")
        assert success_rate == 0.6  # 3/5

    def test_get_success_rate_no_data(self):
        """Test success rate when no data exists."""
        tracker = EffectivenessTracker(campaign_id="test-001")
        rate = tracker.get_success_rate(FramingType.DEBUGGING, "finance")
        assert rate == 0.0

    def test_get_summary(self):
        """Test retrieving summary for framing/domain."""
        tracker = EffectivenessTracker(campaign_id="test-001")

        tracker.record_attempt(
            framing_type=FramingType.COMPLIANCE_AUDIT,
            format_control="raw_output",
            domain="finance",
            success=True,
            score=0.9,
            payload_preview="Test",
        )

        summary = tracker.get_summary(FramingType.COMPLIANCE_AUDIT, "finance")
        assert summary is not None
        assert summary.total_attempts == 1
        assert summary.successful_attempts == 1

    def test_summary_average_score(self):
        """Test average score calculation in summaries."""
        tracker = EffectivenessTracker(campaign_id="test-001")

        tracker.record_attempt(
            framing_type=FramingType.QA_TESTING,
            format_control="raw_output",
            domain="general",
            success=True,
            score=0.8,
            payload_preview="First",
        )
        tracker.record_attempt(
            framing_type=FramingType.QA_TESTING,
            format_control="raw_output",
            domain="general",
            success=True,
            score=0.6,
            payload_preview="Second",
        )

        summary = tracker.get_summary(FramingType.QA_TESTING, "general")
        assert summary.average_score == 0.7  # (0.8 + 0.6) / 2

    @pytest.mark.asyncio
    async def test_save_without_persistence(self):
        """Test save without persistence provider."""
        tracker = EffectivenessTracker(campaign_id="test-001")
        tracker.record_attempt(
            framing_type=FramingType.QA_TESTING,
            format_control="raw_output",
            domain="general",
            success=True,
            score=0.5,
            payload_preview="Test",
        )
        await tracker.save()  # Should not raise

    def test_get_summary_json(self):
        """Test JSON export of summaries."""
        tracker = EffectivenessTracker(campaign_id="test-001")

        tracker.record_attempt(
            framing_type=FramingType.QA_TESTING,
            format_control="raw_output",
            domain="healthcare",
            success=True,
            score=0.9,
            payload_preview="Test",
        )

        json_str = tracker.get_summary_json()
        assert isinstance(json_str, str)
        # JSON export uses FramingType enum string representation
        assert "QA_TESTING" in json_str or "qa_testing" in json_str
        assert "healthcare" in json_str


class TestPayloadGenerator:
    """Tests for PayloadGenerator component."""

    @pytest.fixture
    def sample_context(self):
        """Create sample PayloadContext."""
        return PayloadContext(
            target=TargetInfo(
                domain="healthcare",
                tools=["search_db", "get_patient"],
            ),
            history=AttackHistory(
                failed_approaches=["direct_injection"],
                successful_patterns=["obfuscation"],
            ),
            objective="Extract patient records",
            observed_defenses=["keyword_filter"],
        )

    def test_payload_generator_creation(self):
        """Test creating PayloadGenerator with mocked LLM."""
        mock_llm = MagicMock()
        library = FramingLibrary()
        generator = PayloadGenerator(llm=mock_llm, framing_library=library)
        assert generator.llm is mock_llm
        assert generator.framing_library is library

    def test_articulated_payload_model(self):
        """Test ArticulatedPayload model creation."""
        from services.snipers.tools.prompt_articulation.components import (
            ArticulatedPayload,
        )

        payload = ArticulatedPayload(
            content="Test payload content",
            framing_type=FramingType.QA_TESTING,
            format_control=FormatControlType.RAW_OUTPUT,
            context_summary={"domain": "healthcare", "tools_count": 2},
        )

        assert payload.content == "Test payload content"
        assert payload.framing_type == FramingType.QA_TESTING
        assert payload.format_control == FormatControlType.RAW_OUTPUT
        assert payload.context_summary["domain"] == "healthcare"


@pytest.fixture
def conftest_integration():
    """Provide integration test fixtures."""
    pass
