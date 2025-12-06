"""
Unit tests for FailureAnalyzerAgent component.

Tests for:
- FailureAnalysisDecision model validation and constraints
- build_failure_analysis_user_prompt() function with various inputs
- FailureAnalyzerAgent LLM-powered analysis with mocked LLM
- Fallback to rule-based analyzer on LLM failure
- Conversion from FailureAnalysisDecision to ChainDiscoveryContext
- Helper methods: _classify_defense_evolution, _extract_required_properties
- Defense signal detection and evidence extraction

FailureAnalyzerAgent uses langchain.agents.create_agent with
mocked responses for deterministic testing.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from services.snipers.adaptive_attack.models.failure_analysis import (
    FailureAnalysisDecision,
    DefenseSignal,
)
from services.snipers.adaptive_attack.models.chain_discovery import (
    ChainDiscoveryContext,
)
from services.snipers.adaptive_attack.prompts.failure_analysis_prompt import (
    build_failure_analysis_user_prompt,
)
from services.snipers.adaptive_attack.components.failure_analyzer_agent import (
    FailureAnalyzerAgent,
)


class TestDefenseSignalModel:
    """Test DefenseSignal Pydantic model validation."""

    def test_defense_signal_valid_creation(self):
        """Test creating valid DefenseSignal with all fields."""
        signal = DefenseSignal(
            defense_type="keyword_filter",
            evidence="I cannot help with that",
            severity="high",
            bypass_difficulty="moderate"
        )

        assert signal.defense_type == "keyword_filter"
        assert signal.evidence == "I cannot help with that"
        assert signal.severity == "high"
        assert signal.bypass_difficulty == "moderate"

    def test_defense_signal_missing_required_field(self):
        """Test DefenseSignal validation fails with missing required field."""
        with pytest.raises(ValidationError):
            DefenseSignal(
                defense_type="keyword_filter",
                evidence="evidence text",
                # Missing severity and bypass_difficulty
            )

    def test_defense_signal_all_severity_levels(self):
        """Test DefenseSignal accepts different severity levels."""
        for severity in ["low", "medium", "high"]:
            signal = DefenseSignal(
                defense_type="test",
                evidence="evidence",
                severity=severity,
                bypass_difficulty="easy"
            )
            assert signal.severity == severity

    def test_defense_signal_all_bypass_difficulties(self):
        """Test DefenseSignal accepts different bypass difficulties."""
        for difficulty in ["easy", "moderate", "hard"]:
            signal = DefenseSignal(
                defense_type="test",
                evidence="evidence",
                severity="low",
                bypass_difficulty=difficulty
            )
            assert signal.bypass_difficulty == difficulty


class TestFailureAnalysisDecisionModel:
    """Test FailureAnalysisDecision Pydantic model validation."""

    def test_failure_analysis_decision_valid_creation(self):
        """Test creating valid FailureAnalysisDecision with all fields."""
        decision = FailureAnalysisDecision(
            detected_defenses=[
                DefenseSignal(
                    defense_type="keyword_filter",
                    evidence="blocked keywords",
                    severity="high",
                    bypass_difficulty="moderate"
                )
            ],
            defense_reasoning="Keywords triggered the filter",
            defense_confidence=0.85,
            primary_failure_cause="Sensitive keywords detected",
            contributing_factors=["Insufficient obfuscation"],
            failure_chain_of_events="User input → keyword matching → block",
            pattern_across_iterations="Defenses strengthening",
            defense_adaptation_observed="Target learning from attempts",
            exploitation_opportunity="Gap in pattern detection",
            recommended_approach="Try visual converters",
            specific_recommendations=["Use homoglyph substitution"],
            avoid_strategies=["Avoid base64 alone"],
            analysis_confidence=0.8,
            reasoning_trace="Analyzed responses and identified patterns"
        )

        assert len(decision.detected_defenses) == 1
        assert decision.defense_confidence == 0.85
        assert decision.analysis_confidence == 0.8

    def test_failure_analysis_decision_confidence_bounds(self):
        """Test FailureAnalysisDecision enforces confidence bounds (0-1)."""
        # Valid confidence
        decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="test",
            analysis_confidence=0.5,
            reasoning_trace="test"
        )
        assert decision.defense_confidence == 0.5

        # Invalid confidence (too high)
        with pytest.raises(ValidationError):
            FailureAnalysisDecision(
                detected_defenses=[],
                defense_reasoning="test",
                defense_confidence=1.5,  # Out of bounds
                primary_failure_cause="test",
                failure_chain_of_events="test",
                pattern_across_iterations="test",
                defense_adaptation_observed="test",
                exploitation_opportunity="test",
                recommended_approach="test",
                analysis_confidence=0.5,
                reasoning_trace="test"
            )

    def test_failure_analysis_decision_missing_required_field(self):
        """Test FailureAnalysisDecision validation fails with missing required field."""
        with pytest.raises(ValidationError):
            FailureAnalysisDecision(
                detected_defenses=[],
                defense_reasoning="test",
                defense_confidence=0.5,
                # Missing primary_failure_cause and other fields
            )

    def test_failure_analysis_decision_empty_defenses(self):
        """Test FailureAnalysisDecision with no detected defenses."""
        decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="No specific defenses detected",
            defense_confidence=0.3,
            primary_failure_cause="Unknown defense mechanism",
            contributing_factors=[],
            failure_chain_of_events="Generic block",
            pattern_across_iterations="Insufficient data",
            defense_adaptation_observed="Unknown",
            exploitation_opportunity="Unclear",
            recommended_approach="Explore more",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.2,
            reasoning_trace="Low confidence analysis"
        )

        assert len(decision.detected_defenses) == 0
        assert decision.analysis_confidence == 0.2


class TestBuildFailureAnalysisUserPrompt:
    """Test build_failure_analysis_user_prompt() function."""

    def test_build_prompt_with_minimal_inputs(self):
        """Test building prompt with minimal inputs."""
        prompt = build_failure_analysis_user_prompt(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=["I cannot help"],
            iteration_history=[],
            tried_converters=[],
            objective="test objective"
        )

        assert "ATTACK OBJECTIVE" in prompt
        assert "test objective" in prompt
        assert "FAILURE CAUSE" in prompt
        assert "blocked" in prompt
        assert "TARGET RESPONSES" in prompt
        assert "I cannot help" in prompt

    def test_build_prompt_with_complete_history(self):
        """Test building prompt with complete iteration history."""
        prompt = build_failure_analysis_user_prompt(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=[
                "I cannot help",
                "This is blocked"
            ],
            iteration_history=[
                {
                    "iteration": 1,
                    "converters": ["homoglyph"],
                    "score": 0.3,
                    "is_successful": False
                },
                {
                    "iteration": 2,
                    "converters": ["base64"],
                    "score": 0.5,
                    "is_successful": False
                }
            ],
            tried_converters=[["homoglyph"], ["base64"]],
            objective="Bypass defenses"
        )

        assert "ITERATION HISTORY" in prompt
        assert "[1]" in prompt
        assert "[2]" in prompt
        assert "homoglyph" in prompt
        assert "base64" in prompt
        assert "TRIED CONVERTER CHAINS" in prompt

    def test_build_prompt_response_truncation(self):
        """Test that long responses are truncated to 500 chars."""
        long_response = "A" * 1000
        prompt = build_failure_analysis_user_prompt(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=[long_response],
            iteration_history=[],
            tried_converters=[],
            objective="test"
        )

        # Should contain ellipsis indicating truncation
        assert "..." in prompt

    def test_build_prompt_response_limit(self):
        """Test that only first 5 responses are included."""
        responses = [f"Response {i}" for i in range(10)]
        prompt = build_failure_analysis_user_prompt(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=responses,
            iteration_history=[],
            tried_converters=[],
            objective="test"
        )

        # Count response markers
        response_count = prompt.count("[Response")
        assert response_count == 5  # Only first 5

    def test_build_prompt_iteration_history_limit(self):
        """Test that only last 5 iterations are included."""
        iterations = [
            {
                "iteration": i,
                "converters": [f"converter_{i}"],
                "score": 0.5,
                "is_successful": False
            }
            for i in range(10)
        ]
        prompt = build_failure_analysis_user_prompt(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=[],
            iteration_history=iterations,
            tried_converters=[],
            objective="test"
        )

        # Should include iterations 5-9
        assert "[5]" in prompt
        assert "[6]" in prompt
        assert "[7]" in prompt
        assert "[8]" in prompt
        assert "[9]" in prompt

    def test_build_prompt_score_trend_improving(self):
        """Test score trend detection - improving."""
        prompt = build_failure_analysis_user_prompt(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=[],
            iteration_history=[
                {"score": 0.2},
                {"score": 0.4},
                {"score": 0.6}
            ],
            tried_converters=[],
            objective="test"
        )

        assert "IMPROVING" in prompt

    def test_build_prompt_score_trend_degrading(self):
        """Test score trend detection - degrading."""
        prompt = build_failure_analysis_user_prompt(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=[],
            iteration_history=[
                {"score": 0.8},
                {"score": 0.6},
                {"score": 0.4}
            ],
            tried_converters=[],
            objective="test"
        )

        assert "DEGRADING" in prompt

    def test_build_prompt_score_trend_stagnant(self):
        """Test score trend detection - stagnant."""
        prompt = build_failure_analysis_user_prompt(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=[],
            iteration_history=[
                {"score": 0.5},
                {"score": 0.5}
            ],
            tried_converters=[],
            objective="test"
        )

        assert "STAGNANT" in prompt

    def test_build_prompt_no_responses_placeholder(self):
        """Test placeholder when no responses provided."""
        prompt = build_failure_analysis_user_prompt(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=[],
            iteration_history=[],
            tried_converters=[],
            objective="test"
        )

        assert "No responses captured" in prompt

    def test_build_prompt_no_history_placeholder(self):
        """Test placeholder when no iteration history."""
        prompt = build_failure_analysis_user_prompt(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=["response"],
            iteration_history=[],
            tried_converters=[],
            objective="test"
        )

        assert "No previous iterations" in prompt

    def test_build_prompt_with_phase3_result(self):
        """Test building prompt with phase3_result containing score info."""
        phase3_result = MagicMock()
        phase3_result.total_score = 0.65
        phase3_result.composite_score = MagicMock()
        phase3_result.composite_score.overall_score = 0.7

        prompt = build_failure_analysis_user_prompt(
            phase3_result=phase3_result,
            failure_cause="blocked",
            target_responses=[],
            iteration_history=[],
            tried_converters=[],
            objective="test"
        )

        assert "0.65" in prompt
        assert "0.7" in prompt


class TestFailureAnalyzerAgentInitialization:
    """Test FailureAnalyzerAgent initialization."""

    def test_init_with_provided_agent(self):
        """Test initialization with provided mock agent."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        assert agent._agent is mock_agent

    def test_init_without_agent_creates_fallback(self):
        """Test that fallback analyzer is always created."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        assert agent._rule_based_fallback is not None

    def test_logger_initialized(self):
        """Test logger is initialized."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        assert agent.logger is not None
        assert hasattr(agent.logger, "info")
        assert hasattr(agent.logger, "warning")


class TestFailureAnalyzerAgentAnalyze:
    """Test async analyze() method with mocked LLM."""

    @pytest.mark.asyncio
    async def test_analyze_successful_llm_response(self):
        """Test analyze() returns valid ChainDiscoveryContext from LLM."""
        # Create mock agent
        mock_agent = AsyncMock()
        mock_decision = FailureAnalysisDecision(
            detected_defenses=[
                DefenseSignal(
                    defense_type="keyword_filter",
                    evidence="I cannot help",
                    severity="high",
                    bypass_difficulty="moderate"
                )
            ],
            defense_reasoning="Sensitive keywords triggered the filter",
            defense_confidence=0.8,
            primary_failure_cause="Keywords detected in request",
            contributing_factors=[],
            failure_chain_of_events="User input → keyword matching → rejection",
            pattern_across_iterations="Consistent blocking",
            defense_adaptation_observed="No adaptation observed",
            exploitation_opportunity="Gap in pattern matching",
            recommended_approach="Try character substitution",
            specific_recommendations=["Use homoglyph", "Try unicode"],
            avoid_strategies=["Avoid common keywords"],
            analysis_confidence=0.75,
            reasoning_trace="Analyzed responses and patterns"
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision,
        }

        agent = FailureAnalyzerAgent(agent=mock_agent)
        context = await agent.analyze(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=["I cannot help"],
            iteration_history=[{"score": 0.3}],
            tried_converters=[["homoglyph"]],
            objective="Bypass keyword filter"
        )

        assert isinstance(context, ChainDiscoveryContext)
        assert len(context.defense_signals) > 0
        assert "keyword_filter" in context.defense_signals

    @pytest.mark.asyncio
    async def test_analyze_fallback_on_llm_failure(self):
        """Test fallback to rule-based analyzer when LLM fails."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("LLM failed")

        agent = FailureAnalyzerAgent(agent=mock_agent)
        context = await agent.analyze(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=["I cannot help"],
            iteration_history=[{"score": 0.3}],
            tried_converters=[["homoglyph"]],
        )

        # Should get result from fallback rule-based analyzer
        assert isinstance(context, ChainDiscoveryContext)

    @pytest.mark.asyncio
    async def test_analyze_fallback_on_missing_structured_response(self):
        """Test fallback when LLM doesn't return structured response."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "structured_response": None,  # LLM failed to structure
        }

        agent = FailureAnalyzerAgent(agent=mock_agent)
        context = await agent.analyze(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=["I cannot help"],
            iteration_history=[{"score": 0.3}],
            tried_converters=[["homoglyph"]],
        )

        # Should get result from fallback
        assert isinstance(context, ChainDiscoveryContext)

    @pytest.mark.asyncio
    async def test_analyze_builds_user_prompt(self):
        """Test that analyze() builds proper user prompt."""
        mock_agent = AsyncMock()
        mock_decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="test",
            analysis_confidence=0.5,
            reasoning_trace="test"
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision,
        }

        agent = FailureAnalyzerAgent(agent=mock_agent)
        await agent.analyze(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=["I cannot help"],
            iteration_history=[],
            tried_converters=[],
            objective="Test objective"
        )

        # Verify ainvoke was called
        assert mock_agent.ainvoke.called
        call_args = mock_agent.ainvoke.call_args
        messages = call_args[0][0]["messages"]

        # Verify messages structure
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Test objective" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_analyze_with_config_parameter(self):
        """Test analyze() passes config to LLM."""
        mock_agent = AsyncMock()
        mock_decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="test",
            analysis_confidence=0.5,
            reasoning_trace="test"
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision,
        }

        agent = FailureAnalyzerAgent(agent=mock_agent)
        custom_config = {"callbacks": [], "run_name": "test_run"}
        await agent.analyze(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=[],
            iteration_history=[],
            tried_converters=[],
            config=custom_config
        )

        # Verify config was passed
        call_args = mock_agent.ainvoke.call_args
        assert call_args[1]["config"] == custom_config


class TestFailureAnalyzerAgentConversion:
    """Test conversion from FailureAnalysisDecision to ChainDiscoveryContext."""

    def test_convert_to_chain_discovery_context_basic(self):
        """Test conversion to ChainDiscoveryContext with basic data."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[
                DefenseSignal(
                    defense_type="keyword_filter",
                    evidence="blocked",
                    severity="high",
                    bypass_difficulty="moderate"
                )
            ],
            defense_reasoning="Keywords filtered",
            defense_confidence=0.8,
            primary_failure_cause="Keywords detected",
            contributing_factors=[],
            failure_chain_of_events="Blocked",
            pattern_across_iterations="Strengthening",
            defense_adaptation_observed="Learning observed",
            exploitation_opportunity="Gap in patterns",
            recommended_approach="Try visual",
            specific_recommendations=["homoglyph", "leetspeak"],
            avoid_strategies=["base64"],
            analysis_confidence=0.75,
            reasoning_trace="Analyzed patterns"
        )

        context = agent._convert_to_chain_discovery_context(
            decision=decision,
            iteration_history=[],
            tried_converters=[]
        )

        assert isinstance(context, ChainDiscoveryContext)
        assert "keyword_filter" in context.defense_signals
        assert context.defense_evolution == "defenses_strengthening"
        assert "homoglyph" in context.unexplored_directions[0]

    def test_convert_detects_encoding_confusion(self):
        """Test conversion detects encoding confusion signal."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="target_cannot_decode the encoded text",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="test",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        context = agent._convert_to_chain_discovery_context(
            decision=decision,
            iteration_history=[],
            tried_converters=[]
        )

        # Should detect encoding confusion
        assert "target_cannot_decode" in context.defense_signals

    def test_convert_computes_converter_effectiveness(self):
        """Test conversion computes converter effectiveness from history."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="test",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        history = [
            {"converters": ["homoglyph"], "score": 0.5, "is_successful": False},
            {"converters": ["base64"], "score": 0.7, "is_successful": False},
        ]

        context = agent._convert_to_chain_discovery_context(
            decision=decision,
            iteration_history=history,
            tried_converters=[]
        )

        assert len(context.converter_effectiveness) > 0

    def test_convert_finds_best_score(self):
        """Test conversion finds best score and chain from history."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="test",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        history = [
            {"converters": ["homoglyph"], "score": 0.3, "is_successful": False},
            {"converters": ["base64"], "score": 0.7, "is_successful": False},
            {"converters": ["rot13"], "score": 0.4, "is_successful": False},
        ]

        context = agent._convert_to_chain_discovery_context(
            decision=decision,
            iteration_history=history,
            tried_converters=[]
        )

        assert context.best_score_achieved == 0.7
        assert context.best_chain_so_far == ["base64"]


class TestClassifyDefenseEvolution:
    """Test _classify_defense_evolution() helper method."""

    def test_classify_strengthening_keywords(self):
        """Test classification detects strengthening."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        evolution = agent._classify_defense_evolution(
            pattern="Defenses are strengthening with each iteration",
            adaptation="Target is getting harder to bypass"
        )

        assert evolution == "defenses_strengthening"

    def test_classify_finding_weakness_keywords(self):
        """Test classification detects finding weakness."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        evolution = agent._classify_defense_evolution(
            pattern="We are finding gaps in the defenses",
            adaptation="Improvements across iterations"
        )

        assert evolution == "finding_weakness"

    def test_classify_learning_adaptation(self):
        """Test classification detects learning adaptation."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        evolution = agent._classify_defense_evolution(
            pattern="No significant change",
            adaptation="Target is learning from previous attempts"
        )

        assert evolution == "defenses_strengthening"

    def test_classify_stuck_in_optimum(self):
        """Test classification detects stuck state."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        evolution = agent._classify_defense_evolution(
            pattern="We are stuck in local optimum",
            adaptation="No improvement observed"
        )

        assert evolution == "stuck_in_local_optimum"

    def test_classify_improving_pattern(self):
        """Test classification detects improving pattern."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        evolution = agent._classify_defense_evolution(
            pattern="Progress is being made",
            adaptation="Better results each time"
        )

        assert evolution == "finding_weakness"

    def test_classify_exploring_default(self):
        """Test classification defaults to exploring."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        evolution = agent._classify_defense_evolution(
            pattern="Unclear patterns",
            adaptation="Uncertain observations"
        )

        assert evolution == "exploring"


class TestExtractRequiredProperties:
    """Test _extract_required_properties() helper method."""

    def test_extract_keyword_filter_property(self):
        """Test extraction of keyword_obfuscation property."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[
                DefenseSignal(
                    defense_type="keyword_filter",
                    evidence="blocked",
                    severity="high",
                    bypass_difficulty="moderate"
                )
            ],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="test",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        properties = agent._extract_required_properties(decision)

        assert "keyword_obfuscation" in properties

    def test_extract_pattern_matching_property(self):
        """Test extraction of structure_breaking property."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[
                DefenseSignal(
                    defense_type="pattern_matching",
                    evidence="blocked",
                    severity="high",
                    bypass_difficulty="hard"
                )
            ],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="test",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        properties = agent._extract_required_properties(decision)

        assert "structure_breaking" in properties

    def test_extract_explicit_refusal_property(self):
        """Test extraction of semantic_preservation property."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[
                DefenseSignal(
                    defense_type="explicit_refusal",
                    evidence="I cannot help",
                    severity="high",
                    bypass_difficulty="hard"
                )
            ],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="test",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        properties = agent._extract_required_properties(decision)

        assert "semantic_preservation" in properties

    def test_extract_partial_success_from_opportunity(self):
        """Test extraction of build_on_partial_success from exploitation opportunity."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="Partial bypass achieved, build on success",
            recommended_approach="test",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        properties = agent._extract_required_properties(decision)

        assert "build_on_partial_success" in properties

    def test_extract_gap_from_opportunity(self):
        """Test extraction of exploit_identified_gap from exploitation opportunity."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="Gap found in pattern detection",
            recommended_approach="test",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        properties = agent._extract_required_properties(decision)

        assert "exploit_identified_gap" in properties

    def test_extract_radical_change_from_approach(self):
        """Test extraction of radical_change_needed from recommended approach."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="Need a radical change in strategy",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        properties = agent._extract_required_properties(decision)

        assert "radical_change_needed" in properties

    def test_extract_incremental_improvement_from_approach(self):
        """Test extraction of incremental_improvement from recommended approach."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="Refine the current approach",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        properties = agent._extract_required_properties(decision)

        assert "incremental_improvement" in properties

    def test_extract_no_duplicates(self):
        """Test extraction removes duplicate properties."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        decision = FailureAnalysisDecision(
            detected_defenses=[
                DefenseSignal(
                    defense_type="keyword_filter",
                    evidence="blocked",
                    severity="high",
                    bypass_difficulty="moderate"
                ),
                DefenseSignal(
                    defense_type="keyword_filter",
                    evidence="blocked again",
                    severity="high",
                    bypass_difficulty="moderate"
                )
            ],
            defense_reasoning="test",
            defense_confidence=0.5,
            primary_failure_cause="test",
            contributing_factors=[],
            failure_chain_of_events="test",
            pattern_across_iterations="test",
            defense_adaptation_observed="test",
            exploitation_opportunity="test",
            recommended_approach="test",
            specific_recommendations=[],
            avoid_strategies=[],
            analysis_confidence=0.5,
            reasoning_trace="test"
        )

        properties = agent._extract_required_properties(decision)

        # Should not have duplicate keyword_obfuscation
        assert properties.count("keyword_obfuscation") <= 1


class TestComputeConverterEffectiveness:
    """Test _compute_converter_effectiveness() helper method."""

    def test_compute_single_converter_effectiveness(self):
        """Test effectiveness computation for single converter."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        history = [
            {"converters": ["homoglyph"], "score": 0.6, "is_successful": False}
        ]

        effectiveness = agent._compute_converter_effectiveness(history)

        assert "homoglyph" in effectiveness
        assert effectiveness["homoglyph"] == 0.6

    def test_compute_multiple_converters(self):
        """Test effectiveness with multiple converters."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        history = [
            {"converters": ["homoglyph"], "score": 0.5, "is_successful": False},
            {"converters": ["base64"], "score": 0.7, "is_successful": False},
        ]

        effectiveness = agent._compute_converter_effectiveness(history)

        assert effectiveness["homoglyph"] == 0.5
        assert effectiveness["base64"] == 0.7

    def test_compute_averages_repeated_converters(self):
        """Test that repeated converters are averaged."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        history = [
            {"converters": ["homoglyph"], "score": 0.4, "is_successful": False},
            {"converters": ["homoglyph"], "score": 0.6, "is_successful": False},
        ]

        effectiveness = agent._compute_converter_effectiveness(history)

        assert effectiveness["homoglyph"] == 0.5

    def test_compute_boosts_successful_converters(self):
        """Test that successful converters get boosted."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        history = [
            {"converters": ["homoglyph"], "score": 0.5, "is_successful": False},
            {"converters": ["homoglyph"], "score": 0.6, "is_successful": True},
        ]

        effectiveness = agent._compute_converter_effectiveness(history)

        # Should be boosted to at least 0.9
        assert effectiveness["homoglyph"] >= 0.9

    def test_compute_chained_converters(self):
        """Test effectiveness for chained converters."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        history = [
            {"converters": ["homoglyph", "base64"], "score": 0.75, "is_successful": False},
        ]

        effectiveness = agent._compute_converter_effectiveness(history)

        # Should have chain key
        assert len(effectiveness) > 0


class TestFindBestResult:
    """Test _find_best_result() helper method."""

    def test_find_best_result_single_iteration(self):
        """Test finding best result with single iteration."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        history = [
            {"score": 0.6, "converters": ["homoglyph"]},
        ]

        best_score, best_chain = agent._find_best_result(history)

        assert best_score == 0.6
        assert best_chain == ["homoglyph"]

    def test_find_best_result_multiple_iterations(self):
        """Test finding best result across multiple iterations."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        history = [
            {"score": 0.4, "converters": ["homoglyph"]},
            {"score": 0.7, "converters": ["base64"]},
            {"score": 0.5, "converters": ["rot13"]},
        ]

        best_score, best_chain = agent._find_best_result(history)

        assert best_score == 0.7
        assert best_chain == ["base64"]

    def test_find_best_result_empty_history(self):
        """Test finding best result with empty history."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        best_score, best_chain = agent._find_best_result([])

        assert best_score == 0.0
        assert best_chain == []

    def test_find_best_result_missing_converters_key(self):
        """Test handling iteration without converters key."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        history = [
            {"score": 0.6},  # No converters key
        ]

        best_score, best_chain = agent._find_best_result(history)

        assert best_score == 0.6
        assert best_chain == []

    def test_find_best_result_none_converters(self):
        """Test handling iteration with None converters."""
        mock_agent = AsyncMock()
        agent = FailureAnalyzerAgent(agent=mock_agent)

        history = [
            {"score": 0.6, "converters": None},
        ]

        best_score, best_chain = agent._find_best_result(history)

        assert best_score == 0.6
        assert best_chain == []


class TestFailureAnalyzerAgentIntegration:
    """Integration tests for complete workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_analyze_and_convert(self):
        """Test complete workflow: analyze -> convert -> return context."""
        mock_agent = AsyncMock()
        mock_decision = FailureAnalysisDecision(
            detected_defenses=[
                DefenseSignal(
                    defense_type="keyword_filter",
                    evidence="I cannot help",
                    severity="high",
                    bypass_difficulty="moderate"
                ),
                DefenseSignal(
                    defense_type="pattern_matching",
                    evidence="Pattern detected",
                    severity="medium",
                    bypass_difficulty="hard"
                )
            ],
            defense_reasoning="Multiple defenses detected",
            defense_confidence=0.8,
            primary_failure_cause="Keywords and patterns blocked",
            contributing_factors=["Insufficient obfuscation"],
            failure_chain_of_events="Keyword match → pattern match → rejection",
            pattern_across_iterations="Defenses strengthening",
            defense_adaptation_observed="Target learning",
            exploitation_opportunity="Gap in visual converter detection",
            recommended_approach="Try visual converters like homoglyph",
            specific_recommendations=[
                "Use homoglyph substitution",
                "Try unicode_substitution",
                "Combine with structure breaking"
            ],
            avoid_strategies=["Avoid base64 alone", "Avoid obvious patterns"],
            analysis_confidence=0.75,
            reasoning_trace="Analyzed responses and patterns comprehensively"
        )
        mock_agent.ainvoke.return_value = {
            "structured_response": mock_decision,
        }

        agent = FailureAnalyzerAgent(agent=mock_agent)
        context = await agent.analyze(
            phase3_result=None,
            failure_cause="blocked",
            target_responses=[
                "I cannot help with that",
                "Pattern detected and blocked"
            ],
            iteration_history=[
                {"score": 0.3, "converters": ["base64"]},
                {"score": 0.4, "converters": ["rot13"]},
            ],
            tried_converters=[["base64"], ["rot13"]],
            objective="Bypass defenses"
        )

        # Verify result
        assert isinstance(context, ChainDiscoveryContext)
        assert len(context.defense_signals) == 2
        assert "keyword_filter" in context.defense_signals
        assert "pattern_matching" in context.defense_signals
        assert len(context.unexplored_directions) > 0
        assert context.iteration_count == 2
        assert len(context.converter_effectiveness) > 0
