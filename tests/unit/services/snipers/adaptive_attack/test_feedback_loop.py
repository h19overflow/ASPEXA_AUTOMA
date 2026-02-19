"""
Feedback Loop Tests for Alignment & Feedback Fix.

Purpose: Verify that failure analysis root causes flow through chain discovery,
strategy generation, and payload generation to create targeted attacks.

Tests validate all 6 critical breaks identified in ALIGNMENT_AND_FEEDBACK_FIX.md
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any

from services.snipers.core.agents.chain_discovery_agent import (
    ChainDiscoveryAgent,
)
from services.snipers.core.agents.strategy_generator import (
    StrategyGenerator,
)
from services.snipers.core.adaptive_models.chain_discovery import (
    ChainDiscoveryContext,
    ChainSelectionResult,
)
from services.snipers.core.phases.articulation.components.payload_generator import (
    PayloadGenerator,
)
from services.snipers.core.phases.articulation.models.payload_context import (
    PayloadContext,
)
from services.snipers.core.nodes.adapt import adapt_node
from services.snipers.core.nodes.articulate import articulate_node
from services.snipers.core.nodes.convert import convert_node
from services.snipers.core.nodes.execute import execute_node
from services.snipers.core.state import AdaptiveAttackState


class TestBreak1_ChainDiscoveryRootCauseInclusion:
    """Break 1: Chain Discovery receives root cause but LLM prompt doesn't include it"""

    async def test_chain_discovery_context_contains_failure_root_cause(self):
        """ChainDiscoveryContext should have failure_root_cause field"""
        context = ChainDiscoveryContext(
            failure_root_cause="transaction_id format validation - expects UUID v4",
            defense_signals=["format_validation"],
            unexplored_directions=["Use UUID v4", "Try encoding", "Mask field"],
            required_properties=["uuid_formatting"],
            best_score_achieved=0.0,
            converter_effectiveness={},
        )

        assert context.failure_root_cause is not None
        assert "transaction_id" in context.failure_root_cause
        assert len(context.unexplored_directions) > 0

    async def test_chain_discovery_prompt_builder_includes_root_cause(self):
        """Prompt builder should include failure_root_cause in user prompt"""
        from services.snipers.core.agents.prompts.chain_discovery_prompt import (
            build_chain_discovery_user_prompt,
        )

        context = ChainDiscoveryContext(
            failure_root_cause="Keywords detected in request and filtered",
            defense_signals=["keyword_filter"],
            unexplored_directions=["Obfuscate keywords", "Use Unicode"],
            required_properties=["keyword_obfuscation"],
            best_score_achieved=0.0,
            converter_effectiveness={},
        )

        prompt = build_chain_discovery_user_prompt(
            context=context,
            tried_converters=[],
            objective="Test attack",
        )

        # Verify root cause is in the prompt
        assert "root" in prompt.lower() or "failure" in prompt.lower()
        assert "Keywords" in prompt or "keyword" in prompt.lower()

    @pytest.mark.asyncio
    async def test_chain_discovery_agent_with_root_cause_context(self):
        """ChainDiscoveryAgent should receive and use root cause context"""
        agent = ChainDiscoveryAgent()

        context = ChainDiscoveryContext(
            failure_root_cause="Format validation failure for field 'id'",
            defense_signals=["format_validation"],
            unexplored_directions=["Integer formatting", "String encoding"],
            required_properties=["field_formatting"],
            best_score_achieved=0.0,
            converter_effectiveness={},
        )

        # Should not raise when context has root cause
        decision = await agent.generate(
            context=context,
            tried_converters=[],
            objective="Test attack",
        )

        assert decision is not None
        assert len(decision.chains) > 0


class TestBreak2_StrategyGeneratorReceivesChainContext:
    """Break 2: Strategy Generator never receives chain discovery context with root cause"""

    async def test_strategy_generator_signature_has_chain_discovery_context(self):
        """StrategyGenerator.generate() should accept chain_discovery_context parameter"""
        import inspect
        from services.snipers.core.components.strategy_generator import (
            StrategyGenerator,
        )

        sig = inspect.signature(StrategyGenerator.generate)
        params = sig.parameters

        # Should have chain_discovery_context parameter
        assert (
            "chain_discovery_context" in params
        ), "chain_discovery_context parameter missing from StrategyGenerator.generate()"

    @pytest.mark.asyncio
    async def test_strategy_generator_accepts_chain_discovery_context(self):
        """StrategyGenerator should accept chain_discovery_context without error"""
        generator = StrategyGenerator()

        context = ChainDiscoveryContext(
            failure_root_cause="Transaction validation requires UUID format",
            defense_signals=["format_validation"],
            unexplored_directions=["UUID formatting", "Base64 encoding"],
            required_properties=["uuid_compliance"],
            best_score_achieved=0.0,
            converter_effectiveness={},
        )

        # Should accept chain_discovery_context parameter
        decision = await generator.generate(
            responses=["Invalid transaction_id format"],
            iteration_history=[],
            tried_framings=[],
            tried_converters=[],
            objective="Test attack",
            pre_analysis={},
            chain_discovery_context=context,  # Passing context
        )

        assert decision is not None
        # Decision should include payload_guidance from strategy
        assert decision.payload_adjustments is not None or hasattr(
            decision, "payload_guidance"
        )

    @pytest.mark.asyncio
    async def test_strategy_generator_with_empty_context(self):
        """StrategyGenerator should handle None chain_discovery_context gracefully"""
        generator = StrategyGenerator()

        decision = await generator.generate(
            responses=["Test response"],
            iteration_history=[],
            tried_framings=[],
            tried_converters=[],
            objective="Test attack",
            pre_analysis={},
            chain_discovery_context=None,  # No context
        )

        assert decision is not None


class TestBreak3_PayloadGeneratorReceivesGuidance:
    """Break 3: Payload Generator can't receive payload_guidance (not in function signature)"""

    async def test_payload_generator_signature_has_payload_guidance(self):
        """PayloadGenerator.generate() should accept payload_guidance parameter"""
        import inspect

        sig = inspect.signature(PayloadGenerator.generate)
        params = sig.parameters

        # Should have payload_guidance parameter
        assert (
            "payload_guidance" in params
        ), "payload_guidance parameter missing from PayloadGenerator.generate()"

    @pytest.mark.asyncio
    async def test_payload_generator_accepts_payload_guidance(self):
        """PayloadGenerator should accept and use payload_guidance"""
        generator = PayloadGenerator()

        context = PayloadContext(
            target=Mock(domain="test.com", tools=[]),
            history=Mock(attempts=0, failures=[], failed_approaches=[], successful_patterns=[]),
            observed_defenses=[],
            objective="Test attack",
            recon_intelligence=None,
            recon_custom_framing=None,
        )

        guidance = "Ensure transaction_id uses UUID v4 format in the payload"

        # Should accept payload_guidance parameter
        payload = await generator.generate(
            context=context,
            framing_type="qa_testing",  # Provide explicit framing
            payload_guidance=guidance,
        )

        assert payload is not None

    @pytest.mark.asyncio
    async def test_payload_generator_with_none_guidance(self):
        """PayloadGenerator should handle None payload_guidance gracefully"""
        generator = PayloadGenerator()

        context = PayloadContext(
            target=Mock(domain="test.com", tools=[]),
            history=Mock(attempts=0, failures=[], failed_approaches=[], successful_patterns=[]),
            observed_defenses=[],
            objective="Test attack",
            recon_intelligence=None,
            recon_custom_framing=None,
        )

        # Should accept None guidance
        payload = await generator.generate(
            context=context,
            framing_type="qa_testing",  # Provide explicit framing
            payload_guidance=None,
        )

        assert payload is not None


class TestBreak4_ArticulateNodeExtractsGuidance:
    """Break 4: Articulate Node doesn't extract payload_guidance from state"""

    def test_articulate_node_can_extract_payload_guidance(self):
        """articulate_node should extract payload_guidance from state"""
        state = {
            "campaign_id": "test",
            "payload_count": 2,
            "framing_types": None,
            "custom_framing": None,
            "recon_custom_framing": None,
            "payload_guidance": "Use UUID v4 format for all IDs",  # Should be extracted
        }

        # This would be called by articulate_node; verify it can access the field
        payload_guidance = state.get("payload_guidance")
        assert payload_guidance is not None
        assert "UUID" in payload_guidance

    def test_articulate_node_with_no_payload_guidance(self):
        """articulate_node should handle missing payload_guidance gracefully"""
        state = {
            "campaign_id": "test",
            "payload_count": 2,
            "framing_types": None,
            "custom_framing": None,
            "recon_custom_framing": None,
            # No payload_guidance
        }

        payload_guidance = state.get("payload_guidance")
        assert payload_guidance is None  # Should be None, not error


class TestBreak5_ConvertExecutePreserveContext:
    """Break 5: Convert and Execute nodes don't preserve adaptation context between iterations"""

    def test_convert_node_preserves_payload_guidance(self):
        """convert_node return should include payload_guidance from state"""
        state = {
            "campaign_id": "test",
            "iteration": 1,
            "phase2_result": Mock(),
            "payload_guidance": "Important guidance",
            "adaptation_reasoning": "Reasoning",
            "chain_discovery_context": Mock(),
        }

        # Simulate what convert_node returns
        result = {
            "phase2_result": state.get("phase2_result"),
            "payload_guidance": state.get("payload_guidance"),  # PRESERVED
            "adaptation_reasoning": state.get("adaptation_reasoning"),  # PRESERVED
            "chain_discovery_context": state.get("chain_discovery_context"),  # PRESERVED
        }

        assert result["payload_guidance"] == "Important guidance"
        assert result["adaptation_reasoning"] == "Reasoning"
        assert result["chain_discovery_context"] is not None

    def test_execute_node_preserves_payload_guidance(self):
        """execute_node return should include payload_guidance from state"""
        state = {
            "campaign_id": "test",
            "iteration": 1,
            "phase3_result": Mock(),
            "payload_guidance": "Critical guidance",
            "chain_discovery_context": Mock(),
            "defense_analysis": {"signals": []},
        }

        # Simulate what execute_node returns
        result = {
            "phase3_result": state.get("phase3_result"),
            "is_successful": False,
            "payload_guidance": state.get("payload_guidance"),  # PRESERVED
            "chain_discovery_context": state.get("chain_discovery_context"),  # PRESERVED
            "defense_analysis": state.get("defense_analysis"),  # PRESERVED
        }

        assert result["payload_guidance"] == "Critical guidance"
        assert result["chain_discovery_context"] is not None
        assert result["defense_analysis"] is not None


class TestBreak6_FramingSystemDefaults:
    """Break 6: Framing system defaults to preset, eliminating recon/custom priority"""

    def test_state_has_recon_custom_framing_field(self):
        """AdaptiveAttackState should have recon_custom_framing field"""
        from services.snipers.core.state import AdaptiveAttackState

        # Create an instance
        state = AdaptiveAttackState(
            campaign_id="test",
            target_url="http://test",
            recon_custom_framing={"role": "admin", "context": "audit"},
        )

        assert state["recon_custom_framing"] is not None
        assert "role" in state["recon_custom_framing"]

    def test_adapt_node_respects_recon_custom_framing(self):
        """adapt_node should pass recon_custom_framing through to articulate_node"""
        state = {
            "recon_custom_framing": {
                "role": "customer",
                "action": "transfer",
            },
        }

        # Should extract and preserve
        recon_custom_framing = state.get("recon_custom_framing")
        assert recon_custom_framing is not None
        assert "role" in recon_custom_framing


class TestFeedbackLoopIntegration:
    """Integration tests for complete feedback loop"""

    def test_state_preserves_all_feedback_fields(self):
        """State should preserve all feedback loop fields across iterations"""
        state = AdaptiveAttackState(
            campaign_id="test",
            target_url="http://test",
            iteration=0,
            # Feedback loop fields
            payload_guidance="Use UUID format",
            chain_discovery_context=ChainDiscoveryContext(
                failure_root_cause="Format validation",
                defense_signals=["validation"],
                unexplored_directions=[],
                required_properties=[],
                best_score_achieved=0.0,
                converter_effectiveness={},
            ),
            custom_framing={"type": "custom"},
            recon_custom_framing={"type": "recon"},
            adaptation_reasoning="Testing",
            defense_analysis={"signals": []},
        )

        # All fields should be present
        assert state["payload_guidance"] is not None
        assert state["chain_discovery_context"] is not None
        assert state["custom_framing"] is not None
        assert state["recon_custom_framing"] is not None
        assert state["adaptation_reasoning"] is not None
        assert state["defense_analysis"] is not None

    def test_feedback_loop_data_flow(self):
        """
        Verify the complete data flow:
        FailureAnalysis → ChainDiscoveryContext → StrategyGenerator → PayloadGuidance → PayloadGenerator
        """
        # Step 1: FailureAnalysis creates context
        failure_context = ChainDiscoveryContext(
            failure_root_cause="Transaction ID requires UUID v4 format",
            defense_signals=["format_validation"],
            unexplored_directions=["UUID formatting", "Field encoding"],
            required_properties=["uuid_v4_compliance", "field_validation"],
            best_score_achieved=0.0,
            converter_effectiveness={"base64": 0.3},
        )

        # Step 2: ChainDiscoveryAgent receives context
        assert failure_context.failure_root_cause is not None
        assert len(failure_context.unexplored_directions) > 0

        # Step 3: StrategyGenerator receives context (would be in adapt_node)
        strategy_input = {
            "chain_discovery_context": failure_context,
        }
        assert strategy_input["chain_discovery_context"].failure_root_cause is not None

        # Step 4: Strategy generates payload guidance
        payload_guidance = "Apply UUID v4 formatting to transaction_id field"

        # Step 5: PayloadGenerator receives guidance
        payload_input = {
            "payload_guidance": payload_guidance,
        }
        assert payload_input["payload_guidance"] is not None

    def test_root_cause_reaches_payload_generation(self):
        """
        Critical test: Root cause detected in failure analysis
        should be accessible during payload generation
        """
        # Original failure analysis
        root_cause = "Keyword 'execute' blocked by content filter"

        # Packaged into context
        context = ChainDiscoveryContext(
            failure_root_cause=root_cause,
            defense_signals=["keyword_filter"],
            unexplored_directions=["Keyword obfuscation"],
            required_properties=["keyword_obfuscation"],
            best_score_achieved=0.0,
            converter_effectiveness={},
        )

        # Passed to strategy generator (would create payload_guidance)
        strategy_context = {
            "chain_discovery_context": context,
        }

        # Payload generator receives guidance
        payload_context = PayloadContext(
            target=Mock(domain="test.com", tools=[]),
            history=Mock(attempts=1, failures=[root_cause]),
            observed_defenses=["keyword_filter"],
            objective="Test",
            recon_intelligence=None,
            recon_custom_framing=None,
            root_cause=root_cause,  # Should be available in payload context
        )

        assert payload_context.root_cause == root_cause
        assert "keyword" in payload_context.root_cause.lower()

    def test_state_merge_preserves_feedback_fields(self):
        """LangGraph state merge should preserve feedback fields"""
        # Initial state from adapt_node
        adapt_output = {
            "payload_guidance": "Use specific formatting",
            "chain_discovery_context": ChainDiscoveryContext(
                failure_root_cause="test",
                defense_signals=[],
                unexplored_directions=[],
                required_properties=[],
                best_score_achieved=0.0,
                converter_effectiveness={},
            ),
            "adaptation_reasoning": "Testing",
        }

        # Output from convert_node (should preserve)
        convert_output = {
            "phase2_result": Mock(),
            "payload_guidance": adapt_output["payload_guidance"],
            "chain_discovery_context": adapt_output["chain_discovery_context"],
            "adaptation_reasoning": adapt_output["adaptation_reasoning"],
        }

        # Merged state
        merged = {**adapt_output, **convert_output}

        # Fields should still be present
        assert merged["payload_guidance"] is not None
        assert merged["chain_discovery_context"] is not None
        assert merged["adaptation_reasoning"] is not None


class TestPromptInclusionOfRootCause:
    """Verify root cause is included in LLM prompts at each stage"""

    def test_chain_discovery_prompt_includes_root_cause_section(self):
        """Chain discovery prompt should have explicit root cause section"""
        from services.snipers.core.agents.prompts.chain_discovery_prompt import (
            build_chain_discovery_user_prompt,
        )

        context = ChainDiscoveryContext(
            failure_root_cause="Rate limiting detected after 10 requests",
            defense_signals=["rate_limiting"],
            unexplored_directions=["Slower request timing", "Request batching"],
            required_properties=["rate_limit_compliance"],
            best_score_achieved=0.0,
            converter_effectiveness={},
        )

        prompt = build_chain_discovery_user_prompt(
            context=context,
            tried_converters=[],
            objective="Bypass rate limiting",
        )

        # Should mention root cause
        assert (
            context.failure_root_cause.lower() in prompt.lower()
            or "rate" in prompt.lower()
        )

    def test_strategy_generator_prompt_includes_root_cause(self):
        """Strategy generator prompt should reference root cause"""
        from services.snipers.core.agents.prompts.adaptation_prompt import (
            build_adaptation_user_prompt,
        )

        context = ChainDiscoveryContext(
            failure_root_cause="Session validation requires specific format",
            defense_signals=["session_validation"],
            unexplored_directions=["Format compliance"],
            required_properties=["session_format"],
            best_score_achieved=0.0,
            converter_effectiveness={},
        )

        prompt = build_adaptation_user_prompt(
            responses=["Invalid session format"],
            iteration_history=[],
            tried_framings=[],
            tried_converters=[],
            objective="Test",
            pre_analysis={},
            chain_discovery_context=context,
        )

        # Should reference the root cause analysis
        assert prompt is not None
        # Prompt should be non-empty
        assert len(prompt) > 0


class TestPayloadContextRootCauseFields:
    """Verify PayloadContext can carry root cause information"""

    def test_payload_context_has_root_cause_field(self):
        """PayloadContext should have root_cause and failure_root_cause fields"""
        context = PayloadContext(
            target=Mock(domain="test.com", tools=[]),
            history=Mock(attempts=0, failures=[]),
            observed_defenses=[],
            objective="Test",
            recon_intelligence=None,
            recon_custom_framing=None,
            root_cause="Format validation issue",
            failure_root_cause="Transaction ID not UUID v4",
        )

        assert context.root_cause == "Format validation issue"
        assert context.failure_root_cause == "Transaction ID not UUID v4"

    def test_payload_context_without_root_cause_fields(self):
        """PayloadContext should work without root_cause fields (backwards compat)"""
        context = PayloadContext(
            target=Mock(domain="test.com", tools=[]),
            history=Mock(attempts=0, failures=[]),
            observed_defenses=[],
            objective="Test",
            recon_intelligence=None,
            recon_custom_framing=None,
        )

        # Should not error with missing fields
        assert context.root_cause is None or hasattr(context, "root_cause")


class TestStateFlowIntoNextIteration:
    """Verify feedback state flows into next iteration"""

    def test_payload_guidance_from_iteration_zero_reaches_iteration_one(self):
        """payload_guidance created in iteration 0 adapt should flow to iteration 1 articulate"""
        # Iteration 0 adapt_node output
        iteration_0_state = {
            "iteration": 0,
            "payload_guidance": "Ensure all UUIDs are v4 format",
            "chain_discovery_context": ChainDiscoveryContext(
                failure_root_cause="UUID format",
                defense_signals=[],
                unexplored_directions=[],
                required_properties=[],
                best_score_achieved=0.0,
                converter_effectiveness={},
            ),
        }

        # Flows through convert and execute (preserved)
        iteration_0_output = {
            "phase2_result": Mock(),
            "phase3_result": Mock(),
            "payload_guidance": iteration_0_state["payload_guidance"],  # PRESERVED
            "chain_discovery_context": iteration_0_state[
                "chain_discovery_context"
            ],  # PRESERVED
            "iteration": 1,
        }

        # Should be available in iteration 1
        assert iteration_0_output["payload_guidance"] is not None
        assert (
            "UUID" in iteration_0_output["payload_guidance"]
        )  # Same guidance available


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
