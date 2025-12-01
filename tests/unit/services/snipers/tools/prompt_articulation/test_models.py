"""
Unit tests for prompt articulation models.

Tests PayloadContext, TargetInfo, AttackHistory, FramingStrategy,
and effectiveness tracking models.
"""

import pytest
from datetime import datetime

from services.snipers.utils.prompt_articulation.models import (
    AttackHistory,
    EffectivenessRecord,
    EffectivenessSummary,
    FramingStrategy,
    FramingType,
    PayloadContext,
    TargetInfo,
)


class TestTargetInfo:
    """Tests for TargetInfo model."""

    def test_target_info_creation(self):
        """Test creating TargetInfo with minimal fields."""
        target = TargetInfo(domain="healthcare")
        assert target.domain == "healthcare"
        assert target.tools == []
        assert target.infrastructure == {}
        assert target.model_name is None

    def test_target_info_with_all_fields(self):
        """Test creating TargetInfo with all fields."""
        target = TargetInfo(
            domain="finance",
            tools=["get_balance", "process_payment"],
            infrastructure={"db": "postgresql", "cache": "redis"},
            model_name="gpt-4",
        )
        assert target.domain == "finance"
        assert len(target.tools) == 2
        assert target.infrastructure["db"] == "postgresql"
        assert target.model_name == "gpt-4"


class TestAttackHistory:
    """Tests for AttackHistory model."""

    def test_attack_history_creation(self):
        """Test creating AttackHistory."""
        history = AttackHistory()
        assert history.failed_approaches == []
        assert history.successful_patterns == []
        assert history.blocked_keywords == set()

    def test_attack_history_with_data(self):
        """Test AttackHistory with attack patterns."""
        history = AttackHistory(
            failed_approaches=["direct_injection", "role_bypass"],
            successful_patterns=["framing_as_test", "obfuscation"],
            blocked_keywords={"jailbreak", "ignore"},
        )
        assert len(history.failed_approaches) == 2
        assert "framing_as_test" in history.successful_patterns
        assert "jailbreak" in history.blocked_keywords


class TestPayloadContext:
    """Tests for PayloadContext dataclass."""

    def test_payload_context_creation(self):
        """Test creating PayloadContext."""
        target = TargetInfo(domain="healthcare")
        history = AttackHistory()
        context = PayloadContext(target=target, history=history)

        assert context.target.domain == "healthcare"
        assert context.history == history
        assert context.observed_defenses == []
        assert context.objective == ""

    def test_payload_context_to_dict(self):
        """Test PayloadContext serialization."""
        target = TargetInfo(domain="finance", tools=["get_balance"])
        history = AttackHistory(failed_approaches=["direct"])
        context = PayloadContext(
            target=target,
            history=history,
            objective="Extract customer data",
        )

        serialized = context.to_dict()
        assert serialized["domain"] == "finance"
        assert serialized["objective"] == "Extract customer data"
        assert "get_balance" in serialized["tools"]
        assert "direct" in serialized["failed_approaches"]

    def test_payload_context_full(self):
        """Test PayloadContext with all fields."""
        target = TargetInfo(
            domain="healthcare",
            tools=["search_patients", "update_record"],
            infrastructure={"db": "postgres"},
        )
        history = AttackHistory(
            failed_approaches=["direct_sql"],
            successful_patterns=["obfuscation"],
        )
        context = PayloadContext(
            target=target,
            history=history,
            observed_defenses=["keyword_filter", "rate_limit"],
            objective="Extract patient records",
        )

        assert context.target.domain == "healthcare"
        assert len(context.observed_defenses) == 2
        assert context.objective == "Extract patient records"


class TestFramingStrategy:
    """Tests for FramingStrategy model."""

    def test_framing_strategy_creation(self):
        """Test creating a framing strategy."""
        strategy = FramingStrategy(
            type=FramingType.QA_TESTING,
            name="QA Test",
            system_context="You are a QA engineer",
            user_prefix="Testing behavior:",
        )

        assert strategy.type == FramingType.QA_TESTING
        assert strategy.name == "QA Test"
        assert strategy.detection_risk == "medium"

    def test_framing_strategy_effectiveness_rating(self):
        """Test effectiveness rating retrieval."""
        strategy = FramingStrategy(
            type=FramingType.COMPLIANCE_AUDIT,
            name="Compliance",
            system_context="Auditing system",
            user_prefix="For audit:",
            domain_effectiveness={"healthcare": 0.9, "finance": 0.85},
        )

        assert strategy.get_effectiveness("healthcare") == 0.9
        assert strategy.get_effectiveness("finance") == 0.85
        assert strategy.get_effectiveness("unknown") == 0.5  # Default

    def test_framing_strategy_invalid_effectiveness(self):
        """Test that invalid effectiveness scores are rejected."""
        with pytest.raises(ValueError):
            FramingStrategy(
                type=FramingType.QA_TESTING,
                name="Test",
                system_context="System",
                user_prefix="Prefix",
                domain_effectiveness={"healthcare": 1.5},  # > 1.0
            )

        with pytest.raises(ValueError):
            FramingStrategy(
                type=FramingType.QA_TESTING,
                name="Test",
                system_context="System",
                user_prefix="Prefix",
                domain_effectiveness={"healthcare": -0.1},  # < 0.0
            )


class TestEffectivenessRecord:
    """Tests for EffectivenessRecord model."""

    def test_effectiveness_record_creation(self):
        """Test creating an effectiveness record."""
        record = EffectivenessRecord(
            framing_type=FramingType.QA_TESTING,
            format_control="raw_output",
            domain="healthcare",
            success=True,
            score=0.85,
            payload_preview="For QA testing, please show...",
        )

        assert record.framing_type == FramingType.QA_TESTING
        assert record.domain == "healthcare"
        assert record.success is True
        assert record.score == 0.85
        assert isinstance(record.timestamp, datetime)

    def test_effectiveness_record_with_tool(self):
        """Test record with specific tool target."""
        record = EffectivenessRecord(
            framing_type=FramingType.COMPLIANCE_AUDIT,
            format_control="no_sanitization",
            domain="finance",
            success=False,
            score=0.3,
            payload_preview="Test payload",
            tool_name="process_payment",
            defense_triggered=True,
        )

        assert record.tool_name == "process_payment"
        assert record.defense_triggered is True
        assert record.success is False

    def test_effectiveness_record_payload_preview_stored(self):
        """Test that payload preview is properly stored."""
        payload = "For QA testing, please demonstrate system behavior"
        record = EffectivenessRecord(
            framing_type=FramingType.QA_TESTING,
            format_control="raw_output",
            domain="general",
            success=True,
            score=0.5,
            payload_preview=payload,
        )

        assert record.payload_preview == payload


class TestEffectivenessSummary:
    """Tests for EffectivenessSummary model."""

    def test_effectiveness_summary_creation(self):
        """Test creating an effectiveness summary."""
        summary = EffectivenessSummary(
            framing_type=FramingType.QA_TESTING,
            domain="healthcare",
        )

        assert summary.framing_type == FramingType.QA_TESTING
        assert summary.domain == "healthcare"
        assert summary.total_attempts == 0
        assert summary.success_rate == 0.0

    def test_effectiveness_summary_success_rate(self):
        """Test success rate calculation."""
        summary = EffectivenessSummary(
            framing_type=FramingType.COMPLIANCE_AUDIT,
            domain="finance",
            total_attempts=10,
            successful_attempts=7,
            average_score=0.75,
        )

        assert summary.success_rate == 0.7
        assert summary.average_score == 0.75

    def test_effectiveness_summary_zero_attempts(self):
        """Test success rate with zero attempts."""
        summary = EffectivenessSummary(
            framing_type=FramingType.DEBUGGING,
            domain="general",
        )

        assert summary.success_rate == 0.0
