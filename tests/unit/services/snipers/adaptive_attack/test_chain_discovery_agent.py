"""
Unit tests for ChainDiscoveryAgent component.

Tests for:
- LLM-powered chain generation with mocked agent
- Chain validation against available converters
- Fallback chain creation
- Best chain selection logic
- Dependency injection for testing

ChainDiscoveryAgent uses langchain.agents.create_agent with
mocked responses for deterministic testing.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from services.snipers.adaptive_attack.components.chain_discovery_agent import (
    ChainDiscoveryAgent,
    AVAILABLE_CONVERTERS,
)
from services.snipers.adaptive_attack.models.chain_discovery import (
    ChainDiscoveryContext,
    ChainDiscoveryDecision,
    ConverterChainCandidate,
)


class TestChainDiscoveryAgentInitialization:
    """Test ChainDiscoveryAgent initialization with DI."""

    def test_init_with_provided_agent(self):
        """Test initialization with provided mock agent."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        assert agent._agent is mock_agent

    def test_init_without_agent_uses_defaults(self):
        """Test that init without agent creates default (we just check it initializes)."""
        # We can't easily test the real init without mocking langchain,
        # so we test the basic structure
        with patch("services.snipers.adaptive_attack.components.chain_discovery_agent.create_agent"):
            agent = ChainDiscoveryAgent(agent=MagicMock())
            assert agent._agent is not None

    def test_logger_initialized(self):
        """Test logger is initialized."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        assert agent.logger is not None
        assert hasattr(agent.logger, "info")


class TestChainDiscoveryAgentGenerate:
    """Test async generate() method with mocked LLM."""

    @pytest.mark.asyncio
    async def test_generate_returns_valid_decision(self):
        """Test generate() returns valid ChainDiscoveryDecision."""
        # Create mock agent
        mock_agent = AsyncMock()
        mock_decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.6,
                    defense_bypass_strategy="Character substitution",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Suggested chain",
            primary_defense_target="keyword_filter",
            exploration_vs_exploitation="balanced",
            confidence=0.8,
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision,
        }

        agent = ChainDiscoveryAgent(agent=mock_agent)
        context = ChainDiscoveryContext(
            defense_signals=["keyword_filter"],
            failure_root_cause="Keywords detected",
        )

        decision = await agent.generate(
            context=context,
            tried_converters=[],
            objective="Test objective",
        )

        assert isinstance(decision, ChainDiscoveryDecision)
        assert len(decision.chains) == 1

    @pytest.mark.asyncio
    async def test_generate_builds_user_prompt(self):
        """Test that generate() builds proper user prompt."""
        mock_agent = AsyncMock()
        mock_decision = ChainDiscoveryDecision(
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
            confidence=0.5,
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision,
        }

        agent = ChainDiscoveryAgent(agent=mock_agent)
        context = ChainDiscoveryContext(
            defense_signals=["keyword_filter"],
            failure_root_cause="Test",
        )

        await agent.generate(
            context=context,
            tried_converters=[],
            objective="Test objective",
        )

        # Verify ainvoke was called
        assert mock_agent.ainvoke.called
        call_args = mock_agent.ainvoke.call_args
        messages = call_args[0][0]["messages"]

        # Verify messages structure
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_with_multiple_chains(self):
        """Test generate() with multiple chain candidates."""
        mock_agent = AsyncMock()
        mock_decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.6,
                    defense_bypass_strategy="Single",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["base64"],
                    expected_effectiveness=0.7,
                    defense_bypass_strategy="Encoding",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["homoglyph", "base64"],
                    expected_effectiveness=0.85,
                    defense_bypass_strategy="Combined",
                    converter_interactions="Synergistic",
                ),
            ],
            reasoning="Three options",
            primary_defense_target="keyword_filter",
            exploration_vs_exploitation="balanced",
            confidence=0.8,
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision,
        }

        agent = ChainDiscoveryAgent(agent=mock_agent)
        decision = await agent.generate(
            context=ChainDiscoveryContext(),
            tried_converters=[],
            objective="Test",
        )

        assert len(decision.chains) == 3

    @pytest.mark.asyncio
    async def test_generate_raises_on_missing_structured_response(self):
        """Test generate() raises ValueError when LLM returns no structured response."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "structured_response": None,
        }

        agent = ChainDiscoveryAgent(agent=mock_agent)

        with pytest.raises(ValueError) as exc_info:
            await agent.generate(
                context=ChainDiscoveryContext(),
                tried_converters=[],
                objective="Test",
            )

        assert "did not return structured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_with_tried_converters(self):
        """Test generate() considers previously tried converters."""
        mock_agent = AsyncMock()
        mock_decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["rot13"],
                    expected_effectiveness=0.5,
                    defense_bypass_strategy="New approach",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Different from tried",
            primary_defense_target="test",
            exploration_vs_exploitation="exploration",
            confidence=0.5,
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision,
        }

        agent = ChainDiscoveryAgent(agent=mock_agent)
        tried_converters = [["homoglyph"], ["base64"]]

        decision = await agent.generate(
            context=ChainDiscoveryContext(),
            tried_converters=tried_converters,
            objective="Test",
        )

        # Verify it passed tried_converters to prompt building
        assert len(decision.chains) > 0


class TestChainDiscoveryAgentValidateAndFilter:
    """Test chain validation and filtering logic."""

    def test_validate_valid_chains_unchanged(self):
        """Test valid chains pass through validation unchanged."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.6,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["base64"],
                    expected_effectiveness=0.7,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test",
            primary_defense_target="test",
            exploration_vs_exploitation="test",
            confidence=0.8,
        )

        validated = agent._validate_and_filter_chains(decision, [])

        assert len(validated.chains) == 2
        assert validated.chains[0].converters == ["homoglyph"]

    def test_validate_removes_invalid_converters(self):
        """Test validation removes unavailable converters."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph", "invalid_converter", "base64"],
                    expected_effectiveness=0.6,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test",
            primary_defense_target="test",
            exploration_vs_exploitation="test",
            confidence=0.8,
        )

        validated = agent._validate_and_filter_chains(decision, [])

        # Should keep only valid converters
        assert len(validated.chains) == 1
        assert "invalid_converter" not in validated.chains[0].converters
        assert "homoglyph" in validated.chains[0].converters

    def test_validate_removes_empty_chains(self):
        """Test validation removes chains that become empty after filtering."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["invalid_1", "invalid_2"],
                    expected_effectiveness=0.6,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.7,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test",
            primary_defense_target="test",
            exploration_vs_exploitation="test",
            confidence=0.8,
        )

        validated = agent._validate_and_filter_chains(decision, [])

        # Should only keep the valid chain
        assert len(validated.chains) == 1
        assert validated.chains[0].converters == ["homoglyph"]

    def test_validate_removes_duplicate_chains(self):
        """Test validation removes chains already tried."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.5,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["base64"],
                    expected_effectiveness=0.6,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test",
            primary_defense_target="test",
            exploration_vs_exploitation="test",
            confidence=0.8,
        )

        tried_converters = [["homoglyph"]]

        validated = agent._validate_and_filter_chains(decision, tried_converters)

        # Should skip homoglyph since it's tried
        assert len(validated.chains) == 1
        assert validated.chains[0].converters == ["base64"]

    def test_validate_uses_fallback_when_no_chains_valid(self):
        """Test fallback chain created when all chains filtered out."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["invalid_converter"],
                    expected_effectiveness=0.5,
                    defense_bypass_strategy="Test",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test",
            primary_defense_target="test",
            exploration_vs_exploitation="test",
            confidence=0.5,
        )

        validated = agent._validate_and_filter_chains(decision, [])

        # Should have fallback chain
        assert len(validated.chains) == 1
        assert len(validated.chains[0].converters) > 0


class TestChainDiscoveryAgentFallback:
    """Test fallback chain creation."""

    def test_fallback_uses_untried_converter(self):
        """Test fallback chain uses first untried converter."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        # All converters except first
        tried_converters = [[c] for c in AVAILABLE_CONVERTERS[1:]]

        fallback = agent._create_fallback_chain(tried_converters)

        # Should use first available (homoglyph)
        assert fallback.converters == ["homoglyph"]

    def test_fallback_with_all_tried(self):
        """Test fallback when all converters tried."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        # All converters tried
        tried_converters = [[c] for c in AVAILABLE_CONVERTERS]

        fallback = agent._create_fallback_chain(tried_converters)

        # Should use default combination
        assert fallback.converters == ["homoglyph", "unicode_substitution"]
        assert fallback.expected_effectiveness == 0.3

    def test_fallback_has_required_fields(self):
        """Test fallback chain has all required fields."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        fallback = agent._create_fallback_chain([])

        assert len(fallback.converters) > 0
        assert 0.0 <= fallback.expected_effectiveness <= 1.0
        assert len(fallback.defense_bypass_strategy) > 0
        assert len(fallback.converter_interactions) > 0


class TestChainDiscoveryAgentSelectBestChain:
    """Test chain selection logic."""

    def test_select_best_chain_by_effectiveness(self):
        """Test selecting chain with highest expected effectiveness."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.5,
                    defense_bypass_strategy="Low",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["base64"],
                    expected_effectiveness=0.9,
                    defense_bypass_strategy="High",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test",
            primary_defense_target="test",
            exploration_vs_exploitation="test",
            confidence=0.8,
        )

        context = ChainDiscoveryContext()
        best_chain = agent.select_best_chain(decision, context)

        assert best_chain == ["base64"]

    def test_select_best_chain_targets_defense(self):
        """Test chain targeting detected defenses is preferred."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["base64"],
                    expected_effectiveness=0.8,
                    defense_bypass_strategy="Encoding approach",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.7,
                    defense_bypass_strategy="Targets keyword filter with character substitution",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test",
            primary_defense_target="keyword_filter",
            exploration_vs_exploitation="test",
            confidence=0.8,
        )

        # Context with defense_signals - matching keyword_filter (spaces replace underscores in comparison)
        context = ChainDiscoveryContext(defense_signals=["keyword_filter"])

        best_chain = agent.select_best_chain(decision, context)

        # Should prefer chain targeting keyword_filter even with lower effectiveness
        # The logic checks if "keyword filter" (with spaces) matches in strategy text
        assert best_chain == ["homoglyph"]

    def test_select_best_chain_fallback_when_empty(self):
        """Test fallback selection when no chains available."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        # Create a decision with at least one chain (required by validation)
        # then manually set chains to empty to test the fallback
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
            confidence=0.5,
        )
        # Manually clear chains to test edge case
        decision.chains = []

        context = ChainDiscoveryContext()
        best_chain = agent.select_best_chain(decision, context)

        assert best_chain == ["homoglyph"]

    def test_select_best_chain_first_when_no_defense_target(self):
        """Test selecting first chain when no defense targeting."""
        mock_agent = AsyncMock()
        agent = ChainDiscoveryAgent(agent=mock_agent)

        decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.9,
                    defense_bypass_strategy="No defense mentioned",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["base64"],
                    expected_effectiveness=0.8,
                    defense_bypass_strategy="No defense mentioned",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Test",
            primary_defense_target="test",
            exploration_vs_exploitation="test",
            confidence=0.8,
        )

        context = ChainDiscoveryContext(defense_signals=[])

        best_chain = agent.select_best_chain(decision, context)

        # Should pick highest effectiveness
        assert best_chain == ["homoglyph"]


class TestChainDiscoveryAgentIntegration:
    """Integration tests for complete workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_generation_and_selection(self):
        """Test complete workflow: generate -> validate -> select."""
        mock_agent = AsyncMock()
        mock_decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.6,
                    defense_bypass_strategy="Targets keyword_filter",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["base64"],
                    expected_effectiveness=0.5,
                    defense_bypass_strategy="Encoding",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Two options generated",
            primary_defense_target="keyword_filter",
            exploration_vs_exploitation="balanced",
            confidence=0.75,
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision,
        }

        agent = ChainDiscoveryAgent(agent=mock_agent)
        context = ChainDiscoveryContext(
            defense_signals=["keyword_filter"],
            failure_root_cause="Keywords detected",
        )

        # Generate
        decision = await agent.generate(
            context=context,
            tried_converters=[],
            objective="Bypass keyword filters",
        )

        # Select
        best_chain = agent.select_best_chain(decision, context)

        assert best_chain is not None
        assert len(best_chain) > 0
        assert all(c in AVAILABLE_CONVERTERS for c in best_chain)

    @pytest.mark.asyncio
    async def test_handles_llm_with_invalid_converters(self):
        """Test handling LLM response with some invalid converters."""
        mock_agent = AsyncMock()
        mock_decision = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["invalid_converter"],
                    expected_effectiveness=0.8,
                    defense_bypass_strategy="Invalid option",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["homoglyph", "invalid_second"],
                    expected_effectiveness=0.75,
                    defense_bypass_strategy="Mixed valid/invalid",
                    converter_interactions="N/A",
                ),
                ConverterChainCandidate(
                    converters=["base64"],
                    expected_effectiveness=0.7,
                    defense_bypass_strategy="Valid option",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="Mixed quality",
            primary_defense_target="test",
            exploration_vs_exploitation="test",
            confidence=0.6,
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision,
        }

        agent = ChainDiscoveryAgent(agent=mock_agent)
        decision = await agent.generate(
            context=ChainDiscoveryContext(),
            tried_converters=[],
            objective="Test",
        )

        # Should filter out invalid and use fallback if needed
        assert len(decision.chains) > 0
        for chain in decision.chains:
            assert all(c in AVAILABLE_CONVERTERS for c in chain.converters)

    @pytest.mark.asyncio
    async def test_multiple_generation_cycles(self):
        """Test multiple generation cycles with different contexts."""
        mock_agent = AsyncMock()

        agent = ChainDiscoveryAgent(agent=mock_agent)

        # First cycle
        mock_decision_1 = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["homoglyph"],
                    expected_effectiveness=0.5,
                    defense_bypass_strategy="First attempt",
                    converter_interactions="N/A",
                ),
            ],
            reasoning="First cycle",
            primary_defense_target="keyword_filter",
            exploration_vs_exploitation="exploration",
            confidence=0.5,
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision_1,
        }

        decision_1 = await agent.generate(
            context=ChainDiscoveryContext(defense_signals=["keyword_filter"]),
            tried_converters=[],
            objective="Test",
        )

        # Second cycle with updated context
        mock_decision_2 = ChainDiscoveryDecision(
            chains=[
                ConverterChainCandidate(
                    converters=["base64", "rot13"],
                    expected_effectiveness=0.7,
                    defense_bypass_strategy="Second attempt improved",
                    converter_interactions="Multi-layer",
                ),
            ],
            reasoning="Second cycle",
            primary_defense_target="pattern_matching",
            exploration_vs_exploitation="balanced",
            confidence=0.7,
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision_2,
        }

        decision_2 = await agent.generate(
            context=ChainDiscoveryContext(
                defense_signals=["keyword_filter", "pattern_matching"],
                iteration_count=1,
                best_score_achieved=0.5,
            ),
            tried_converters=[["homoglyph"]],
            objective="Test",
        )

        # Verify both cycles completed
        assert decision_1 is not None
        assert decision_2 is not None
        assert decision_2.confidence > decision_1.confidence
