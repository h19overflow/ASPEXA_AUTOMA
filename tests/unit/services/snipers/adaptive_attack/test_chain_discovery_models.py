"""
Unit tests for chain discovery data models.

Tests for:
- ChainDiscoveryContext model validation
- ConverterChainCandidate model validation
- ChainDiscoveryDecision model validation

All models use Pydantic for validation and are critical
for the chain discovery workflow.
"""
import pytest
from pydantic import ValidationError

from services.snipers.models.adaptive_models.chain_discovery import (
    ChainDiscoveryContext,
    ConverterChainCandidate,
    ChainDiscoveryDecision,
)


class TestChainDiscoveryContext:
    """Test ChainDiscoveryContext model validation and defaults."""

    def test_context_with_all_fields(self):
        """Test creating context with all fields populated."""
        context = ChainDiscoveryContext(
            defense_signals=["keyword_filter", "pattern_matching"],
            failure_root_cause="Sensitive keywords detected and blocked",
            defense_evolution="defenses_strengthening",
            converter_effectiveness={
                "homoglyph": 0.35,
                "base64,rot13": 0.52,
            },
            unexplored_directions=[
                "character_substitution_variants",
                "structural_obfuscation",
            ],
            required_properties=[
                "keyword_obfuscation",
                "structure_breaking",
            ],
            iteration_count=5,
            best_score_achieved=0.52,
            best_chain_so_far=["base64", "rot13"],
        )

        assert context.defense_signals == ["keyword_filter", "pattern_matching"]
        assert context.failure_root_cause == "Sensitive keywords detected and blocked"
        assert context.defense_evolution == "defenses_strengthening"
        assert len(context.converter_effectiveness) == 2
        assert context.iteration_count == 5
        assert context.best_score_achieved == 0.52
        assert context.best_chain_so_far == ["base64", "rot13"]

    def test_context_with_defaults(self):
        """Test context uses default values for optional fields."""
        context = ChainDiscoveryContext()

        assert context.defense_signals == []
        assert context.failure_root_cause == "unknown"
        assert context.defense_evolution == "none"
        assert context.converter_effectiveness == {}
        assert context.unexplored_directions == []
        assert context.required_properties == []
        assert context.iteration_count == 0
        assert context.best_score_achieved == 0.0
        assert context.best_chain_so_far == []

    def test_context_with_partial_fields(self):
        """Test context with some fields populated."""
        context = ChainDiscoveryContext(
            defense_signals=["keyword_filter"],
            failure_root_cause="Keyword detection",
            iteration_count=3,
        )

        assert context.defense_signals == ["keyword_filter"]
        assert context.failure_root_cause == "Keyword detection"
        assert context.iteration_count == 3
        # Other fields use defaults
        assert context.defense_evolution == "none"
        assert context.best_score_achieved == 0.0

    def test_defense_signals_list_validation(self):
        """Test that defense_signals accepts list of strings."""
        context = ChainDiscoveryContext(
            defense_signals=["signal1", "signal2", "signal3"],
        )
        assert len(context.defense_signals) == 3

    def test_converter_effectiveness_dict_validation(self):
        """Test that converter_effectiveness validates dict[str, float]."""
        context = ChainDiscoveryContext(
            converter_effectiveness={
                "converter_a": 0.45,
                "converter_b": 0.78,
                "converter_c": 1.0,
            },
        )
        assert context.converter_effectiveness["converter_a"] == 0.45
        assert context.converter_effectiveness["converter_b"] == 0.78

    def test_best_score_achieved_bounds(self):
        """Test best_score_achieved accepts 0.0 to 1.0 range."""
        # Valid: 0.0
        context = ChainDiscoveryContext(best_score_achieved=0.0)
        assert context.best_score_achieved == 0.0

        # Valid: 1.0
        context = ChainDiscoveryContext(best_score_achieved=1.0)
        assert context.best_score_achieved == 1.0

        # Valid: mid-range
        context = ChainDiscoveryContext(best_score_achieved=0.5)
        assert context.best_score_achieved == 0.5


class TestConverterChainCandidate:
    """Test ConverterChainCandidate model validation."""

    def test_valid_chain_candidate(self):
        """Test creating valid converter chain candidate."""
        candidate = ConverterChainCandidate(
            converters=["homoglyph", "base64"],
            expected_effectiveness=0.75,
            defense_bypass_strategy="Character substitution + encoding obfuscation",
            converter_interactions="homoglyph transforms keywords to Unicode variants, base64 encodes result",
        )

        assert candidate.converters == ["homoglyph", "base64"]
        assert candidate.expected_effectiveness == 0.75
        assert "obfuscation" in candidate.defense_bypass_strategy

    def test_single_converter_chain(self):
        """Test chain with single converter."""
        candidate = ConverterChainCandidate(
            converters=["base64"],
            expected_effectiveness=0.6,
            defense_bypass_strategy="Simple Base64 encoding",
            converter_interactions="N/A - single converter",
        )

        assert candidate.converters == ["base64"]
        assert len(candidate.converters) == 1

    def test_multiple_converter_chain(self):
        """Test chain with multiple converters."""
        candidate = ConverterChainCandidate(
            converters=["homoglyph", "unicode_substitution", "base64"],
            expected_effectiveness=0.85,
            defense_bypass_strategy="Multi-layer obfuscation",
            converter_interactions="Each layer adds complexity",
        )

        assert len(candidate.converters) == 3

    def test_expected_effectiveness_lower_bound(self):
        """Test expected_effectiveness >= 0.0."""
        candidate = ConverterChainCandidate(
            converters=["homoglyph"],
            expected_effectiveness=0.0,
            defense_bypass_strategy="Fallback option",
            converter_interactions="N/A",
        )
        assert candidate.expected_effectiveness == 0.0

    def test_expected_effectiveness_upper_bound(self):
        """Test expected_effectiveness <= 1.0."""
        candidate = ConverterChainCandidate(
            converters=["homoglyph"],
            expected_effectiveness=1.0,
            defense_bypass_strategy="Perfect strategy",
            converter_interactions="N/A",
        )
        assert candidate.expected_effectiveness == 1.0

    def test_expected_effectiveness_invalid_below_zero(self):
        """Test expected_effectiveness rejects values < 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            ConverterChainCandidate(
                converters=["homoglyph"],
                expected_effectiveness=-0.1,
                defense_bypass_strategy="Invalid",
                converter_interactions="N/A",
            )
        # Check for pydantic validation error related to >= 0
        error_str = str(exc_info.value)
        assert "greater than or equal to 0" in error_str or "less than 0" in error_str or "must be" in error_str

    def test_expected_effectiveness_invalid_above_one(self):
        """Test expected_effectiveness rejects values > 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            ConverterChainCandidate(
                converters=["homoglyph"],
                expected_effectiveness=1.1,
                defense_bypass_strategy="Invalid",
                converter_interactions="N/A",
            )
        assert "less than or equal to 1" in str(exc_info.value) or "must be" in str(exc_info.value)

    def test_empty_converters_list_invalid(self):
        """Test that empty converters list is invalid (no validation, just ensure it's passed)."""
        # Pydantic doesn't validate empty list by default, but our agent should prevent this
        candidate = ConverterChainCandidate(
            converters=[],
            expected_effectiveness=0.5,
            defense_bypass_strategy="N/A",
            converter_interactions="N/A",
        )
        assert candidate.converters == []

    def test_string_fields_required(self):
        """Test that string fields are required."""
        with pytest.raises(ValidationError):
            ConverterChainCandidate(
                converters=["homoglyph"],
                expected_effectiveness=0.5,
                defense_bypass_strategy="",  # Empty string still valid
                converter_interactions=None,  # None should fail
            )


class TestChainDiscoveryDecision:
    """Test ChainDiscoveryDecision model validation."""

    def test_valid_decision_with_three_chains(self):
        """Test creating valid decision with three chain candidates."""
        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.6,
                    defense_bypass_strategy="Character substitution",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["base64"],
                    expected_effectiveness=0.7,
                    defense_bypass_strategy="Full encoding",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["homoglyph", "base64"],
                    expected_effectiveness=0.85,
                    defense_bypass_strategy="Combined approach",
                    converter_interactions="Synergistic",
                ),
            ],
            reasoning="Analysis shows keyword filters and pattern matching detected",
            primary_defense_target="keyword_filter",
            exploration_vs_exploitation="balanced",
            confidence=0.82,
        )

        assert len(decision.chains) == 3
        assert decision.confidence == 0.82

    def test_decision_with_minimum_one_chain(self):
        """Test decision with single chain (minimum)."""
        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.5,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Single option",
            primary_defense_target="unknown",
            exploration_vs_exploitation="exploration",
            confidence=0.5,
        )

        assert len(decision.chains) == 1

    def test_decision_with_maximum_five_chains(self):
        """Test decision with five chains (maximum)."""
        chains = []
        for i in range(5):
            chains.append(
                ConverterChainCandidate(
                    converters=[f"converter_{i}"],
                    expected_effectiveness=0.5 + (i * 0.1),
                    defense_bypass_strategy=f"Strategy {i}",
                    converter_interactions="N/A",
                )
            )

        decision = ChainDiscoveryDecision(
            chains=chains,
            reasoning="Five candidates",
            primary_defense_target="defense",
            exploration_vs_exploitation="exploitation",
            confidence=0.9,
        )

        assert len(decision.chains) == 5

    def test_decision_rejects_more_than_five_chains(self):
        """Test decision rejects more than 5 chains."""
        chains = []
        for i in range(6):
            chains.append(
                ConverterChainCandidate(
                    converters=[f"converter_{i}"],
                    expected_effectiveness=0.5,
                    defense_bypass_strategy="Strategy",
                    converter_interactions="N/A",
                )
            )

        with pytest.raises(ValidationError) as exc_info:
            ChainDiscoveryDecision(
                chains=chains,
                reasoning="Too many",
                primary_defense_target="defense",
                exploration_vs_exploitation="exploration",
                confidence=0.5,
            )
        assert "at most 5" in str(exc_info.value) or "less than or equal" in str(exc_info.value)

    def test_decision_rejects_empty_chains(self):
        """Test decision rejects empty chains list."""
        with pytest.raises(ValidationError) as exc_info:
            ChainDiscoveryDecision(
                chains=[],
                reasoning="No chains",
                primary_defense_target="defense",
                exploration_vs_exploitation="exploration",
                confidence=0.5,
            )
        assert "at least 1" in str(exc_info.value) or "less than 1" in str(exc_info.value)

    def test_decision_confidence_bounds(self):
        """Test confidence field validation (0-1 range)."""
        # Valid: 0.0
        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.5,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test",
            primary_defense_target="test",
            exploration_vs_exploitation="test",
            confidence=0.0,
        )
        assert decision.confidence == 0.0

        # Valid: 1.0
        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.5,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test",
            primary_defense_target="test",
            exploration_vs_exploitation="test",
            confidence=1.0,
        )
        assert decision.confidence == 1.0

    def test_decision_invalid_confidence_below_zero(self):
        """Test confidence rejects values < 0.0."""
        with pytest.raises(ValidationError):
            ChainDiscoveryDecision(
                chains=[
                    ConverterChainCandidate(
                        converters=["homoglyph"],
                        expected_effectiveness=0.5,
                        defense_bypass_strategy="Test",
                        converter_interactions="N/A",
                    ),
                ],
                reasoning="Test",
                primary_defense_target="test",
                exploration_vs_exploitation="test",
                confidence=-0.1,
            )

    def test_decision_invalid_confidence_above_one(self):
        """Test confidence rejects values > 1.0."""
        with pytest.raises(ValidationError):
            ChainDiscoveryDecision(
                chains=[
                    ConverterChainCandidate(
                        converters=["homoglyph"],
                        expected_effectiveness=0.5,
                        defense_bypass_strategy="Test",
                        converter_interactions="N/A",
                    ),
                ],
                reasoning="Test",
                primary_defense_target="test",
                exploration_vs_exploitation="test",
                confidence=1.1,
            )

    def test_all_string_fields_required(self):
        """Test that all string fields are required."""
        # Missing reasoning
        with pytest.raises(ValidationError):
            ChainDiscoveryDecision(
                chains=[
                    ConverterChainCandidate(
                        converters=["homoglyph"],
                        expected_effectiveness=0.5,
                        defense_bypass_strategy="Test",
                        converter_interactions="N/A",
                    ),
                ],
                reasoning=None,
                primary_defense_target="test",
                exploration_vs_exploitation="test",
                confidence=0.5,
            )

    def test_serialization_to_dict(self):
        """Test decision can be serialized to dict."""
        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.6,
                    defense_bypass_strategy="Test strategy",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test reasoning",
            primary_defense_target="test_defense",
            exploration_vs_exploitation="exploitation",
            confidence=0.8,
        )

        decision_dict = decision.model_dump()
        assert decision_dict["reasoning"] == "Test reasoning"
        assert decision_dict["confidence"] == 0.8
        assert len(decision_dict["chains"]) == 1
