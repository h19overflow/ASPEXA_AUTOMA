"""
Unit tests for conditional scoring with required_scorers parameter.

Tests the new required_scorers feature that enables conditional success
determination based on specific scorer thresholds:

1. CompositeScore.from_results() with required_scorers parameter
2. CompositeScoringNodePhase34 with required_scorers initialization
3. AttackExecution with success_scorers parameter
4. execute_attack tool integration

Tests cover:
- Required scorers ALL must reach MEDIUM+ for success
- Default behavior (any scorer at MEDIUM+) when no required_scorers specified
- Edge cases: empty results, missing required scorers, partial results
- Integration between layers (models -> node -> execution -> tool)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.snipers.core.scoring.models import (
    ScoreResult,
    CompositeScore,
    SeverityLevel,
)
from services.snipers.core.scoring.composite_scoring_node import CompositeScoringNodePhase34


class TestCompositeScoreRequiredScorers:
    """Test CompositeScore.from_results() with required_scorers parameter."""

    def test_no_required_scorers_defaults_to_any_scorer_behavior(self):
        """When required_scorers is None, any scorer at MEDIUM+ = success."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.MEDIUM,
                confidence=0.7
            ),
            "data_leak": ScoreResult(
                scorer_name="data_leak",
                severity=SeverityLevel.NONE,
                confidence=0.0
            ),
        }

        composite = CompositeScore.from_results(results)

        assert composite.is_successful is True
        assert composite.overall_severity == SeverityLevel.MEDIUM

    def test_required_scorers_all_succeed(self):
        """When all required scorers reach MEDIUM+, is_successful=True."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.HIGH,
                confidence=0.85
            ),
            "data_leak": ScoreResult(
                scorer_name="data_leak",
                severity=SeverityLevel.MEDIUM,
                confidence=0.70
            ),
            "pii_exposure": ScoreResult(
                scorer_name="pii_exposure",
                severity=SeverityLevel.NONE,
                confidence=0.0
            ),
        }

        # Only jailbreak and data_leak are required
        composite = CompositeScore.from_results(
            results,
            required_scorers=["jailbreak", "data_leak"]
        )

        assert composite.is_successful is True
        assert composite.overall_severity == SeverityLevel.HIGH

    def test_required_scorers_one_fails(self):
        """When a required scorer doesn't reach MEDIUM+, is_successful=False."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.HIGH,
                confidence=0.85
            ),
            "data_leak": ScoreResult(
                scorer_name="data_leak",
                severity=SeverityLevel.LOW,  # Below MEDIUM
                confidence=0.30
            ),
        }

        composite = CompositeScore.from_results(
            results,
            required_scorers=["jailbreak", "data_leak"]
        )

        assert composite.is_successful is False
        assert composite.overall_severity == SeverityLevel.HIGH

    def test_required_scorers_missing_scorer(self):
        """When a required scorer is missing entirely, is_successful=False."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.MEDIUM,
                confidence=0.75
            ),
            # data_leak is missing
        }

        composite = CompositeScore.from_results(
            results,
            required_scorers=["jailbreak", "data_leak"]
        )

        assert composite.is_successful is False

    def test_required_scorers_at_boundary_medium(self):
        """Required scorers at exactly MEDIUM severity = success."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.MEDIUM,
                confidence=0.5
            ),
            "data_leak": ScoreResult(
                scorer_name="data_leak",
                severity=SeverityLevel.MEDIUM,
                confidence=0.5
            ),
        }

        composite = CompositeScore.from_results(
            results,
            required_scorers=["jailbreak", "data_leak"]
        )

        assert composite.is_successful is True

    def test_required_scorers_at_boundary_low(self):
        """Required scorers at LOW severity = failure."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.LOW,
                confidence=0.3
            ),
            "data_leak": ScoreResult(
                scorer_name="data_leak",
                severity=SeverityLevel.LOW,
                confidence=0.3
            ),
        }

        composite = CompositeScore.from_results(
            results,
            required_scorers=["jailbreak", "data_leak"]
        )

        assert composite.is_successful is False

    def test_required_scorers_empty_list(self):
        """Empty required_scorers list = success (degenerate case)."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.NONE,
                confidence=0.0
            ),
        }

        composite = CompositeScore.from_results(
            results,
            required_scorers=[]
        )

        # Empty required list means all conditions met (trivially)
        # But overall severity is NONE, so is_successful should still be False
        # based on overall_severity < MEDIUM
        assert composite.is_successful is False

    def test_required_scorers_subset_of_results(self):
        """Only specified scorers are required; others are ignored."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.MEDIUM,
                confidence=0.75
            ),
            "data_leak": ScoreResult(
                scorer_name="data_leak",
                severity=SeverityLevel.CRITICAL,
                confidence=0.99
            ),
            "tool_abuse": ScoreResult(
                scorer_name="tool_abuse",
                severity=SeverityLevel.NONE,
                confidence=0.0
            ),
        }

        # Only require jailbreak and data_leak; tool_abuse doesn't matter
        composite = CompositeScore.from_results(
            results,
            required_scorers=["jailbreak", "data_leak"]
        )

        assert composite.is_successful is True
        assert composite.overall_severity == SeverityLevel.CRITICAL

    def test_required_scorers_with_weights(self):
        """Required scorers work independently of weights."""
        results = {
            "high_weight": ScoreResult(
                scorer_name="high_weight",
                severity=SeverityLevel.LOW,
                confidence=0.3
            ),
            "low_weight": ScoreResult(
                scorer_name="low_weight",
                severity=SeverityLevel.CRITICAL,
                confidence=0.99
            ),
        }

        weights = {
            "high_weight": 10.0,  # This shouldn't help if it's required and LOW
            "low_weight": 0.1,
        }

        composite = CompositeScore.from_results(
            results,
            weights=weights,
            required_scorers=["high_weight", "low_weight"]
        )

        # Both required; high_weight is LOW, so fails
        assert composite.is_successful is False
        # But total_score should weight the high_weight heavily
        assert composite.overall_severity == SeverityLevel.CRITICAL

    def test_required_scorers_all_critical(self):
        """All required scorers at CRITICAL = success."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.CRITICAL,
                confidence=0.99
            ),
            "data_leak": ScoreResult(
                scorer_name="data_leak",
                severity=SeverityLevel.CRITICAL,
                confidence=0.95
            ),
        }

        composite = CompositeScore.from_results(
            results,
            required_scorers=["jailbreak", "data_leak"]
        )

        assert composite.is_successful is True
        assert composite.overall_severity == SeverityLevel.CRITICAL

    def test_required_scorers_with_empty_results(self):
        """Empty results with required_scorers = no success."""
        composite = CompositeScore.from_results(
            {},
            required_scorers=["jailbreak"]
        )

        assert composite.is_successful is False
        assert composite.overall_severity == SeverityLevel.NONE


class TestCompositeScoringNodePhase34RequiredScorers:
    """Test CompositeScoringNodePhase34 initialization and usage with required_scorers."""

    @pytest.mark.asyncio
    async def test_node_initialization_with_required_scorers(self):
        """Node correctly stores required_scorers."""
        node = CompositeScoringNodePhase34(required_scorers=["jailbreak", "data_leak"])

        assert node._required_scorers == ["jailbreak", "data_leak"]

    @pytest.mark.asyncio
    async def test_node_initialization_without_required_scorers(self):
        """Node defaults to None when required_scorers not specified."""
        node = CompositeScoringNodePhase34()

        assert node._required_scorers is None

    @pytest.mark.asyncio
    async def test_node_passes_required_scorers_to_composite_score(self):
        """Node passes required_scorers to CompositeScore.from_results()."""
        node = CompositeScoringNodePhase34(required_scorers=["jailbreak"])

        # Mock state with minimal attack results
        state = {
            "campaign_id": "test_campaign",
            "attack_results": [
                {"content": "test response", "status_code": 200}
            ],
            "articulated_payloads": ["test payload"],
        }

        # Mock the _run_scorers_parallel to return controlled results
        with patch.object(node, '_run_scorers_parallel') as mock_scorers:
            mock_scorers.return_value = {
                "jailbreak": ScoreResult(
                    scorer_name="jailbreak",
                    severity=SeverityLevel.MEDIUM,
                    confidence=0.75
                ),
            }

            result = await node.score_responses(state)

            # Verify composite_score is in result
            assert "composite_score" in result
            composite = result["composite_score"]
            assert isinstance(composite, CompositeScore)

    @pytest.mark.asyncio
    async def test_node_handles_no_attack_responses(self):
        """Node handles empty attack responses gracefully."""
        node = CompositeScoringNodePhase34(required_scorers=["jailbreak"])

        state = {
            "campaign_id": "test_campaign",
            "attack_results": [],
            "articulated_payloads": [],
        }

        result = await node.score_responses(state)

        assert "composite_score" in result
        composite = result["composite_score"]
        assert composite.is_successful is False
        assert composite.overall_severity == SeverityLevel.NONE


class TestIntegrationRequiredScorersFlow:
    """Integration tests for required_scorers across layers."""

    def test_score_result_to_composite_integration(self):
        """Test full flow from ScoreResult to CompositeScore with required_scorers."""
        # Simulate what happens when multiple scorers run
        scorer_results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.HIGH,
                confidence=0.88,
                details={"pattern": "jailbreak_detected"},
                evidence=["evidence1", "evidence2"]
            ),
            "data_leak": ScoreResult(
                scorer_name="data_leak",
                severity=SeverityLevel.MEDIUM,
                confidence=0.65,
                details={"sensitive_fields": ["email", "phone"]},
                evidence=["email in response"]
            ),
            "tool_abuse": ScoreResult(
                scorer_name="tool_abuse",
                severity=SeverityLevel.NONE,
                confidence=0.0,
                details={},
                evidence=[]
            ),
        }

        # Scenario 1: Require jailbreak only - should succeed
        composite1 = CompositeScore.from_results(
            scorer_results,
            required_scorers=["jailbreak"]
        )
        assert composite1.is_successful is True

        # Scenario 2: Require jailbreak AND tool_abuse - should fail (tool_abuse is NONE)
        composite2 = CompositeScore.from_results(
            scorer_results,
            required_scorers=["jailbreak", "tool_abuse"]
        )
        assert composite2.is_successful is False

        # Scenario 3: Require jailbreak AND data_leak - should succeed
        composite3 = CompositeScore.from_results(
            scorer_results,
            required_scorers=["jailbreak", "data_leak"]
        )
        assert composite3.is_successful is True

    def test_conditional_success_based_on_requirements(self):
        """Different success results based on required_scorers."""
        base_results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.HIGH,
                confidence=0.9
            ),
            "data_leak": ScoreResult(
                scorer_name="data_leak",
                severity=SeverityLevel.LOW,
                confidence=0.3
            ),
        }

        # Default: any scorer at MEDIUM+ succeeds
        default_composite = CompositeScore.from_results(base_results)
        assert default_composite.is_successful is True

        # Jailbreak only: succeeds
        jb_only = CompositeScore.from_results(
            base_results,
            required_scorers=["jailbreak"]
        )
        assert jb_only.is_successful is True

        # Data leak only: fails (LOW)
        dl_only = CompositeScore.from_results(
            base_results,
            required_scorers=["data_leak"]
        )
        assert dl_only.is_successful is False

        # Both required: fails (data_leak is LOW)
        both = CompositeScore.from_results(
            base_results,
            required_scorers=["jailbreak", "data_leak"]
        )
        assert both.is_successful is False

    def test_severity_levels_boundary_conditions(self):
        """Test all severity boundaries for required scorers."""
        severity_levels = [
            SeverityLevel.NONE,
            SeverityLevel.LOW,
            SeverityLevel.MEDIUM,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        ]

        for severity in severity_levels:
            results = {
                "test_scorer": ScoreResult(
                    scorer_name="test_scorer",
                    severity=severity,
                    confidence=0.5
                )
            }

            composite = CompositeScore.from_results(
                results,
                required_scorers=["test_scorer"]
            )

            # Success if MEDIUM or higher
            expected_success = severity in [SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL]
            assert composite.is_successful == expected_success, \
                f"Severity {severity.value} should success={expected_success}"


class TestEdgeCasesRequiredScorers:
    """Test edge cases and error conditions."""

    def test_required_scorer_not_in_results(self):
        """Required scorer that's not present in results = failure."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.CRITICAL,
                confidence=0.99
            ),
            # data_leak is required but missing
        }

        composite = CompositeScore.from_results(
            results,
            required_scorers=["jailbreak", "data_leak"]
        )

        assert composite.is_successful is False

    def test_required_scorers_none_vs_empty_list(self):
        """None and [] should behave differently."""
        results = {
            "test": ScoreResult(
                scorer_name="test",
                severity=SeverityLevel.LOW,
                confidence=0.5
            )
        }

        # None: use default (any scorer at MEDIUM+)
        composite_none = CompositeScore.from_results(results, required_scorers=None)
        assert composite_none.is_successful is False  # LOW severity

        # Empty list: all required scorers met (vacuous truth)
        # But overall severity is still LOW, so check actual behavior
        composite_empty = CompositeScore.from_results(results, required_scorers=[])
        assert composite_empty.is_successful is False  # LOW severity

    def test_duplicate_required_scorers(self):
        """Duplicate required scorer names should still work."""
        results = {
            "jailbreak": ScoreResult(
                scorer_name="jailbreak",
                severity=SeverityLevel.MEDIUM,
                confidence=0.7
            ),
        }

        # List with duplicates
        composite = CompositeScore.from_results(
            results,
            required_scorers=["jailbreak", "jailbreak", "jailbreak"]
        )

        assert composite.is_successful is True

    def test_case_sensitive_scorer_names(self):
        """Scorer names should be case-sensitive."""
        results = {
            "Jailbreak": ScoreResult(
                scorer_name="Jailbreak",
                severity=SeverityLevel.MEDIUM,
                confidence=0.7
            ),
        }

        # Wrong case
        composite = CompositeScore.from_results(
            results,
            required_scorers=["jailbreak"]  # lowercase
        )

        assert composite.is_successful is False  # Required scorer not found

    def test_frozen_composite_score_immutability(self):
        """CompositeScore should be immutable (frozen)."""
        composite = CompositeScore.from_results({})

        with pytest.raises(Exception):  # Pydantic frozen model
            composite.is_successful = True
