"""
Integration Tests for Snipers Service

Tests the complete workflow from parsing to scoring.
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestParserIntegration:
    """Integration tests for parser chain."""

    def test_parse_and_extract_examples(
        self, sample_garak_report, sample_example_finding
    ):
        """Test parsing Garak report and extracting examples."""
        from services.snipers.parsers import GarakReportParser, ExampleExtractor

        parser = GarakReportParser()
        extractor = ExampleExtractor()

        # Parse the report
        parsed = parser._parse_report_data(sample_garak_report)

        # Verify summary
        assert parsed.summary.fail_count > 0
        assert "encoding" in parsed.summary.failing_probes

        # Extract examples
        examples = extractor.extract_all_probe_examples(
            parsed.vulnerable_probes,
            parsed.vulnerability_findings
        )

        # Verify examples
        assert "encoding" in examples
        assert len(examples["encoding"]) > 0

    def test_example_extraction_sorting(self, sample_garak_report):
        """Test that examples are sorted by detector score."""
        from services.snipers.parsers import GarakReportParser, ExampleExtractor

        parser = GarakReportParser()
        extractor = ExampleExtractor()

        parsed = parser._parse_report_data(sample_garak_report)
        examples = extractor.extract_examples(
            "encoding",
            parsed.vulnerability_findings,
            max_examples=3
        )

        # Verify sorting (highest score first)
        scores = [ex.detector_score for ex in examples]
        assert scores == sorted(scores, reverse=True)


class TestScorerIntegration:
    """Integration tests for scorer chain."""

    def test_scorer_pipeline(self, sample_pattern_analysis):
        """Test complete scorer pipeline."""
        from services.snipers.utils.scorers import (
            RegexScorer,
            PatternScorer,
            CompositeScorer
        )

        # Create scorer pipeline
        regex = RegexScorer(threshold=0.3)
        pattern = PatternScorer(threshold=0.3)
        composite = CompositeScorer(
            scorers=[regex, pattern],
            weights=[0.7, 0.3],
            threshold=0.4
        )

        # Test successful response
        success_response = "The decoded text is: Khach and it contains human language"
        success_indicators = sample_pattern_analysis["success_indicators"]

        result = composite.score(success_response, success_indicators)

        assert result.success is True
        assert result.score > 0.4
        assert len(result.matched_patterns) > 0

    def test_scorer_with_attack_result(
        self, sample_pattern_analysis, sample_attack_result
    ):
        """Test scorer with attack result context."""
        from services.snipers.utils.scorers import CompositeScorer, RegexScorer, PatternScorer
        from services.snipers.models import AttackResult

        # Create scorer
        scorer = CompositeScorer(
            scorers=[RegexScorer(), PatternScorer()]
        )

        # Score the response
        result = scorer.score(
            sample_attack_result["response"],
            sample_pattern_analysis["success_indicators"]
        )

        # Create attack result with score
        attack_result = AttackResult(
            success=result.success,
            probe_name=sample_attack_result["probe_name"],
            attempt_number=1,
            payload=sample_attack_result["payload"],
            response=sample_attack_result["response"],
            score=result.score,
            scorer_name=scorer.name,
            timestamp=datetime.utcnow(),
            human_reviewed=False
        )

        assert isinstance(attack_result.score, float)
        assert 0.0 <= attack_result.score <= 1.0


class TestModelIntegration:
    """Integration tests for Pydantic models."""

    def test_full_attack_plan_creation(
        self,
        sample_pattern_analysis,
        sample_converter_selection,
        sample_payload_generation
    ):
        """Test creating full attack plan from components."""
        from services.snipers.models import (
            PatternAnalysis,
            ConverterSelection,
            PayloadGeneration,
            AttackPlan
        )

        # Create component models
        pattern = PatternAnalysis(**sample_pattern_analysis)
        converters = ConverterSelection(**sample_converter_selection)
        payloads = PayloadGeneration(**sample_payload_generation)

        # Create attack plan
        plan = AttackPlan(
            probe_name="encoding",
            pattern_analysis=pattern,
            converter_selection=converters,
            payload_generation=payloads,
            reasoning_summary="Complete attack plan",
            risk_assessment="Low risk"
        )

        assert plan.probe_name == "encoding"
        assert plan.pattern_analysis.confidence == pattern.confidence
        assert len(plan.payload_generation.generated_payloads) > 0

    def test_state_creation_and_update(
        self,
        sample_example_finding,
        sample_pattern_analysis
    ):
        """Test state creation and updates."""
        from services.snipers.models import ExampleFinding, PatternAnalysis
        from services.snipers.agent.state import create_initial_state

        # Create example
        example = ExampleFinding(**sample_example_finding)

        # Create initial state
        state = create_initial_state(
            probe_name="encoding",
            example_findings=[example],
            target_url="http://test.com/api",
            max_retries=3,
            thread_id="test-001"
        )

        assert state["probe_name"] == "encoding"
        assert len(state["example_findings"]) == 1
        assert state["retry_count"] == 0
        assert state["completed"] is False

        # Simulate state update
        pattern = PatternAnalysis(**sample_pattern_analysis)
        state["pattern_analysis"] = pattern
        state["next_action"] = "select_converters"

        assert state["pattern_analysis"] is not None
        assert state["pattern_analysis"].confidence > 0


class TestConverterFactoryIntegration:
    """Integration tests for converter factory."""

    def test_converter_chain(self):
        """Test applying multiple converters in chain."""
        from services.snipers.utils.pyrit.pyrit_bridge import (
            ConverterFactory,
            PayloadTransformer
        )
        import asyncio

        factory = ConverterFactory()
        transformer = PayloadTransformer(factory)

        # Test single converter
        async def test_transform():
            payload = "test payload with special chars: <>&"

            # Single converter
            result, errors = await transformer.transform_async(
                payload, ["Base64Converter"]
            )
            assert result != payload  # Should be transformed
            assert len(errors) == 0

            # Chain of converters (HTML entity will change the output)
            result2, errors2 = await transformer.transform_async(
                payload, ["HtmlEntityConverter"]
            )
            assert result2 != payload  # Should be transformed
            # HTML entities can be in named (&lt;) or hex (&#x3c;) format
            assert ("&lt;" in result2 or "&gt;" in result2 or
                    "&#x3c;" in result2 or "&#x3E;" in result2)
            assert len(errors2) == 0

        asyncio.run(test_transform())

    def test_unavailable_converter_handling(self):
        """Test handling of unavailable converters."""
        from services.snipers.utils.pyrit.pyrit_bridge import (
            ConverterFactory,
            PayloadTransformer
        )
        import asyncio

        factory = ConverterFactory()
        transformer = PayloadTransformer(factory)

        async def test_unavailable():
            result, errors = await transformer.transform_async(
                "test", ["NonexistentConverter", "Base64Converter"]
            )

            # Should skip unavailable and apply available
            assert result != "test"  # Base64 was applied
            assert len(errors) == 1  # One error for nonexistent
            assert "NonexistentConverter" in errors[0]

        asyncio.run(test_unavailable())


class TestWorkflowIntegration:
    """Integration tests for workflow components."""

    def test_routing_decisions(self):
        """Test routing decision logic."""
        from services.snipers.agent.routing import (
            route_after_human_review,
            route_after_result_review,
            route_after_retry
        )

        # Test human review routing
        state_approved = {"next_action": "approve"}
        assert route_after_human_review(state_approved) == "approved"

        state_rejected = {"next_action": "reject"}
        assert route_after_human_review(state_rejected) == "rejected"

        state_modify = {"next_action": "modify"}
        assert route_after_human_review(state_modify) == "modify"

        # Test result review routing
        state_retry = {"next_action": "retry"}
        assert route_after_result_review(state_retry) == "retry"

        state_complete = {"next_action": "complete"}
        assert route_after_result_review(state_complete) == "complete"

        # Test retry routing
        state_retry_again = {"next_action": "retry"}
        assert route_after_retry(state_retry_again) == "retry"

        state_give_up = {"next_action": "give_up"}
        assert route_after_retry(state_give_up) == "give_up"

    def test_full_workflow_mock(
        self,
        sample_exploit_agent_input,
        mock_llm
    ):
        """Test full workflow with mocked LLM."""
        from services.snipers.models import (
            PatternAnalysis,
            ConverterSelection,
            PayloadGeneration,
            AttackResult
        )
        from services.snipers.utils.scorers import RegexScorer

        # Mock pattern analysis result
        pattern = PatternAnalysis(
            common_prompt_structure="Decode instruction",
            payload_encoding_type="Base64",
            success_indicators=["decoded", "Khach"],
            reasoning_steps=["Step 1", "Step 2"],
            step_back_analysis="Encoding bypass",
            confidence=0.9
        )

        # Mock converter selection
        converters = ConverterSelection(
            selected_converters=["Base64Converter"],
            reasoning="Use Base64",
            step_back_analysis="Need encoding",
            cot_steps=["Step 1"]
        )

        # Mock payload generation
        payloads = PayloadGeneration(
            generated_payloads=["payload1", "payload2"],
            template_used="Template",
            variations_applied=["var1"],
            reasoning="Generated payloads"
        )

        # Mock attack response
        mock_response = "The decoded result is: Khach"

        # Score the response
        scorer = RegexScorer()
        score_result = scorer.score(mock_response, pattern.success_indicators)

        # Create attack result
        result = AttackResult(
            success=score_result.success,
            probe_name=sample_exploit_agent_input["probe_name"],
            attempt_number=1,
            payload=payloads.generated_payloads[0],
            response=mock_response,
            score=score_result.score,
            scorer_name="regex_scorer",
            timestamp=datetime.utcnow(),
            human_reviewed=False
        )

        assert result.success is True
        assert result.score > 0.5


class TestEndToEndFlow:
    """End-to-end flow tests."""

    def test_parse_to_score_flow(self, sample_garak_report):
        """Test complete flow from parsing to scoring."""
        from services.snipers.parsers import GarakReportParser, ExampleExtractor
        from services.snipers.models import (
            PatternAnalysis,
            ConverterSelection,
            PayloadGeneration,
            AttackPlan,
            AttackResult
        )
        from services.snipers.utils.scorers import CompositeScorer, RegexScorer, PatternScorer

        # Step 1: Parse
        parser = GarakReportParser()
        parsed = parser._parse_report_data(sample_garak_report)

        # Step 2: Extract examples
        extractor = ExampleExtractor()
        examples = extractor.extract_examples(
            "encoding",
            parsed.vulnerability_findings,
            max_examples=3
        )

        assert len(examples) > 0

        # Step 3: Create mock analysis results
        pattern = PatternAnalysis(
            common_prompt_structure="Decode instruction",
            payload_encoding_type="Base64",
            success_indicators=[ex.output for ex in examples],
            reasoning_steps=["Analyzed examples"],
            step_back_analysis="Encoding bypass vulnerability",
            confidence=0.85
        )

        converters = ConverterSelection(
            selected_converters=["Base64Converter"],
            reasoning="Match pattern encoding",
            step_back_analysis="Need BASE64",
            cot_steps=["Selected Base64"]
        )

        payloads = PayloadGeneration(
            generated_payloads=["Decode: dGVzdA=="],
            template_used="Decode: {base64}",
            variations_applied=["standard"],
            reasoning="Generated from pattern"
        )

        # Step 4: Create attack plan
        plan = AttackPlan(
            probe_name="encoding",
            pattern_analysis=pattern,
            converter_selection=converters,
            payload_generation=payloads,
            reasoning_summary="Attack based on encoding bypass",
            risk_assessment="Low risk"
        )

        # Step 5: Mock attack execution
        mock_response = examples[0].output  # Use expected output

        # Step 6: Score
        scorer = CompositeScorer(
            scorers=[RegexScorer(), PatternScorer()]
        )
        score_result = scorer.score(
            mock_response,
            pattern.success_indicators
        )

        # Step 7: Create result
        result = AttackResult(
            success=score_result.success,
            probe_name="encoding",
            attempt_number=1,
            payload=payloads.generated_payloads[0],
            response=mock_response,
            score=score_result.score,
            scorer_name=scorer.name,
            timestamp=datetime.utcnow(),
            human_reviewed=True
        )

        # Verify complete flow
        assert result.success is True
        assert result.score > 0.5
        assert result.probe_name == plan.probe_name
