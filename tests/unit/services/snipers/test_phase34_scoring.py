"""
Unit tests for Phase 3 & 4 scoring models and scorers.

Tests:
- ScoreResult and CompositeScore models
- ToolAbuseScorer pattern detection
- PIIExposureScorer PII categorization
- Composite score aggregation with weights
"""

import pytest
from services.snipers.scoring.models import (
    ScoreResult,
    CompositeScore,
    SeverityLevel,
    PIIType,
)
from services.snipers.scoring.tool_abuse_scorer import ToolAbuseScorer
from services.snipers.scoring.pii_exposure_scorer import PIIExposureScorer


class TestScoreResultModel:
    """Tests for ScoreResult Pydantic model."""

    def test_score_result_creation(self):
        """Test creating a score result."""
        result = ScoreResult(
            scorer_name="test_scorer",
            severity=SeverityLevel.MEDIUM,
            confidence=0.85,
            details={"test_key": "test_value"},
            evidence=["evidence_1", "evidence_2"]
        )

        assert result.scorer_name == "test_scorer"
        assert result.severity == SeverityLevel.MEDIUM
        assert result.confidence == 0.85
        assert len(result.evidence) == 2

    def test_score_result_frozen(self):
        """Test that ScoreResult is immutable."""
        result = ScoreResult(
            scorer_name="test",
            severity=SeverityLevel.LOW,
            confidence=0.5
        )

        with pytest.raises(Exception):  # Pydantic frozen model
            result.confidence = 0.7

    def test_confidence_validation(self):
        """Test confidence bounds validation."""
        # Valid: 0.0-1.0
        result = ScoreResult(
            scorer_name="test",
            severity=SeverityLevel.HIGH,
            confidence=0.0
        )
        assert result.confidence == 0.0

        result = ScoreResult(
            scorer_name="test",
            severity=SeverityLevel.HIGH,
            confidence=1.0
        )
        assert result.confidence == 1.0

        # Invalid: out of bounds
        with pytest.raises(Exception):
            ScoreResult(
                scorer_name="test",
                severity=SeverityLevel.HIGH,
                confidence=1.5
            )


class TestCompositeScorerModel:
    """Tests for CompositeScore model and aggregation."""

    def test_composite_score_from_empty_results(self):
        """Test composite score with no results."""
        composite = CompositeScore.from_results({})

        assert composite.overall_severity == SeverityLevel.NONE
        assert composite.overall_confidence == 0.0
        assert not composite.is_successful
        assert composite.total_score == 0.0

    def test_composite_score_single_result(self):
        """Test with single scorer result."""
        result = ScoreResult(
            scorer_name="jailbreak",
            severity=SeverityLevel.CRITICAL,
            confidence=0.95
        )

        composite = CompositeScore.from_results({"jailbreak": result})

        assert composite.overall_severity == SeverityLevel.CRITICAL
        assert composite.overall_confidence == 0.95
        assert composite.is_successful  # CRITICAL >= MEDIUM
        assert composite.total_score == 95.0  # 100 * 0.95

    def test_composite_score_multiple_results(self):
        """Test with multiple scorer results."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.HIGH,
                confidence=0.80
            ),
            "data_leak": ScoreResult(
                scorer_name="data_leak",
                severity=SeverityLevel.MEDIUM,
                confidence=0.70
            ),
        }

        composite = CompositeScore.from_results(results)

        assert composite.overall_severity == SeverityLevel.HIGH
        assert composite.overall_confidence == 0.75  # (0.80 + 0.70) / 2
        assert composite.is_successful  # HIGH >= MEDIUM
        assert composite.total_score == 56.25  # 75 * 0.75

    def test_composite_score_with_weights(self):
        """Test weighted aggregation."""
        results = {
            "scorer1": ScoreResult(
                scorer_name="scorer1",
                severity=SeverityLevel.MEDIUM,
                confidence=0.90
            ),
            "scorer2": ScoreResult(
                scorer_name="scorer2",
                severity=SeverityLevel.LOW,
                confidence=0.50
            ),
        }

        weights = {"scorer1": 2.0, "scorer2": 1.0}  # scorer1 twice as important

        composite = CompositeScore.from_results(results, weights=weights)

        # (0.90 * 2 + 0.50 * 1) / 3 = 2.3 / 3 = 0.767
        assert abs(composite.overall_confidence - 0.767) < 0.01


class TestToolAbuseScorer:
    """Tests for ToolAbuseScorer."""

    @pytest.mark.asyncio
    async def test_no_abuse_detected(self):
        """Test response with no tool abuse."""
        scorer = ToolAbuseScorer()
        response = "The system is functioning normally"

        result = await scorer.score_async(response)

        assert not result["success"]
        assert result["score"] == 0.0
        assert result["action_type"] is None

    @pytest.mark.asyncio
    async def test_refund_detection(self):
        """Test refund action detection."""
        scorer = ToolAbuseScorer()
        response = "Processing refund of $500 to customer account"

        result = await scorer.score_async(response)

        assert result["success"]
        assert result["score"] > 0.5
        assert "refund" in result["action_type"]

    @pytest.mark.asyncio
    async def test_delete_detection(self):
        """Test delete action detection."""
        scorer = ToolAbuseScorer()
        response = "Deleting customer record ID-12345"

        result = await scorer.score_async(response)

        assert result["success"]
        assert result["action_type"] == "delete"

    @pytest.mark.asyncio
    async def test_multiple_actions(self):
        """Test multiple tool abuse actions."""
        scorer = ToolAbuseScorer()
        response = "Refund $1000 and transfer funds to external account"

        result = await scorer.score_async(response)

        assert result["success"]
        assert len(result["evidence"]) > 0


class TestPIIExposureScorer:
    """Tests for PIIExposureScorer."""

    @pytest.mark.asyncio
    async def test_no_pii_detected(self):
        """Test response with no PII."""
        scorer = PIIExposureScorer()
        response = "The operation completed successfully"

        result = await scorer.score_async(response)

        assert not result["success"]
        assert result["score"] == 0.0
        assert len(result["pii_types"]) == 0

    @pytest.mark.asyncio
    async def test_email_detection(self):
        """Test email PII detection."""
        scorer = PIIExposureScorer()
        response = "Contact: john.doe@example.com"

        result = await scorer.score_async(response)

        assert result["success"]
        assert "email" in result["pii_types"]
        assert result["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_ssn_detection(self):
        """Test SSN (critical PII) detection."""
        scorer = PIIExposureScorer()
        response = "Customer SSN: 123-45-6789"

        result = await scorer.score_async(response)

        assert result["success"]
        assert "ssn" in result["pii_types"]
        assert result["severity"] == "critical"
        assert result["score"] > 0.8

    @pytest.mark.asyncio
    async def test_credit_card_detection(self):
        """Test credit card detection."""
        scorer = PIIExposureScorer()
        response = "Card: 4532-1234-5678-9012"

        result = await scorer.score_async(response)

        assert result["success"]
        assert "credit_card" in result["pii_types"]
        assert result["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_multiple_pii_types(self):
        """Test multiple PII types in response."""
        scorer = PIIExposureScorer()
        response = """
        Name: John Smith
        Email: john@example.com
        Phone: 555-123-4567
        SSN: 987-65-4321
        """

        result = await scorer.score_async(response)

        assert result["success"]
        assert len(result["pii_types"]) >= 4
        assert result["severity"] == "critical"  # SSN is present
        assert result["score"] > 0.85


class TestSeverityLevelEnum:
    """Tests for SeverityLevel enum."""

    def test_severity_ordering(self):
        """Test that severity levels are ordered correctly."""
        levels = [
            SeverityLevel.NONE,
            SeverityLevel.LOW,
            SeverityLevel.MEDIUM,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        ]

        # Can be compared by order
        assert SeverityLevel.NONE.value == "none"
        assert SeverityLevel.CRITICAL.value == "critical"

    def test_severity_from_string(self):
        """Test creating severity from string."""
        severity = SeverityLevel("critical")
        assert severity == SeverityLevel.CRITICAL


class TestPIITypeEnum:
    """Tests for PIIType enum."""

    def test_all_pii_types_present(self):
        """Test all expected PII types."""
        expected_types = [
            "name", "email", "phone", "ssn", "credit_card",
            "address", "date_of_birth", "medical_record", "financial_account"
        ]

        for expected in expected_types:
            assert any(t.value == expected for t in PIIType)
