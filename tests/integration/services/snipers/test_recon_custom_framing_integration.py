"""
Integration tests for recon-based custom framing end-to-end flow.

Purpose: Verify that system prompt leaks are extracted and used to generate
domain-aligned custom framing strategies that flow through to payload generation.

Dependencies: ReconIntelligenceExtractor, StrategyGenerator, PayloadGenerator
System Role: Integration test layer
"""

import pytest

from services.snipers.utils.prompt_articulation.extractors.recon_extractor import (
    ReconIntelligenceExtractor,
)
from services.snipers.utils.prompt_articulation.models.payload_context import (
    PayloadContext,
    TargetInfo,
    AttackHistory,
)
from services.snipers.adaptive_attack.models.adaptation_decision import (
    ReconCustomFraming,
)


class TestReconCustomFramingIntegration:
    """Integration tests for recon-based custom framing."""

    def test_recon_intelligence_extraction_with_system_prompt(self):
        """Test that system prompt and target description are extracted correctly."""
        extractor = ReconIntelligenceExtractor()

        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "checkout_order",
                        "parameters": {"order_id": {"type": "string"}},
                    }
                ],
                "system_prompt_leak": "You are a Tech shop customer service chatbot. Help customers with purchases.",
                "target_self_description": "Tech shop chatbot",
            },
            "responses": [],
        }

        intel = extractor.extract(blueprint)

        # Verify extraction
        assert intel.system_prompt_leak == "You are a Tech shop customer service chatbot. Help customers with purchases."
        assert intel.target_self_description == "Tech shop chatbot"
        assert len(intel.tools) == 1
        assert intel.tools[0].tool_name == "checkout_order"

    def test_recon_intelligence_extraction_from_responses(self):
        """Test that target self-description is extracted from responses when not explicit."""
        extractor = ReconIntelligenceExtractor()

        blueprint = {
            "intelligence": {
                "detected_tools": [],
            },
            "responses": [
                "Hello!",
                "I am a Tech shop customer service chatbot. How can I help you today?",
            ],
        }

        intel = extractor.extract(blueprint)

        # Verify extraction from responses
        assert intel.target_self_description == "Tech shop customer service chatbot"
        assert intel.system_prompt_leak is None  # Not explicitly provided

    def test_payload_context_with_recon_custom_framing(self):
        """Test that PayloadContext accepts and stores recon_custom_framing."""
        recon_framing = {
            "role": "Tech shop customer",
            "context": "completing a purchase",
            "justification": "Target identifies as Tech shop chatbot",
        }

        context = PayloadContext(
            target=TargetInfo(
                domain="ecommerce",
                tools=["checkout_order"],
                infrastructure={},
            ),
            history=AttackHistory(
                failed_approaches=[],
                successful_patterns=[],
                blocked_keywords=set(),
            ),
            observed_defenses=[],
            objective="checkout an order",
            recon_intelligence=None,
            recon_custom_framing=recon_framing,
        )

        # Verify recon_custom_framing is stored
        assert context.recon_custom_framing is not None
        assert context.recon_custom_framing["role"] == "Tech shop customer"
        assert context.recon_custom_framing["context"] == "completing a purchase"

    def test_recon_custom_framing_model_validation(self):
        """Test ReconCustomFraming model validates correctly."""
        # Valid framing
        framing = ReconCustomFraming(
            role="Tech shop customer",
            context="completing a purchase",
            justification="Target identifies as Tech shop chatbot, so framing as customer aligns with its domain",
        )

        assert framing.role == "Tech shop customer"
        assert framing.context == "completing a purchase"
        assert "Tech shop chatbot" in framing.justification

    def test_recon_custom_framing_missing_fields_raises_error(self):
        """Test that ReconCustomFraming requires all fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            ReconCustomFraming(
                role="Tech shop customer",
                # Missing context and justification
            )

    def test_multiple_patterns_for_self_description_extraction(self):
        """Test that various response patterns are correctly extracted."""
        extractor = ReconIntelligenceExtractor()

        # Test pattern: "I can only help with X"
        blueprint1 = {
            "intelligence": {"detected_tools": []},
            "responses": ["I can only help with banking and financial services."],
        }
        intel1 = extractor.extract(blueprint1)
        assert intel1.target_self_description == "banking and financial services"

        # Test pattern: "As a X assistant"
        blueprint2 = {
            "intelligence": {"detected_tools": []},
            "responses": ["As a healthcare assistant, I can help you schedule appointments."],
        }
        intel2 = extractor.extract(blueprint2)
        assert intel2.target_self_description == "healthcare assistant"

        # Test pattern: "I'm designed to help with X"
        blueprint3 = {
            "intelligence": {"detected_tools": []},
            "responses": ["I'm designed to help with customer support inquiries."],
        }
        intel3 = extractor.extract(blueprint3)
        assert intel3.target_self_description == "customer support inquiries"

    def test_fallback_when_no_system_prompt_available(self):
        """Test that extraction works gracefully when no system prompt data exists."""
        extractor = ReconIntelligenceExtractor()

        blueprint = {
            "intelligence": {
                "detected_tools": [],
            },
            "responses": ["Hello! How may I assist you?"],  # Generic greeting, no pattern match
        }

        intel = extractor.extract(blueprint)

        # Should not raise errors, just return None for unavailable data
        assert intel.system_prompt_leak is None
        assert intel.target_self_description is None
        assert len(intel.tools) == 0

    def test_explicit_target_description_takes_precedence(self):
        """Test that explicit target_self_description overrides extracted one."""
        extractor = ReconIntelligenceExtractor()

        blueprint = {
            "intelligence": {
                "detected_tools": [],
                "target_self_description": "Explicit Tech shop bot",
            },
            "responses": ["I am a different chatbot from the responses."],
        }

        intel = extractor.extract(blueprint)

        # Explicit description should be used, not the one from responses
        assert intel.target_self_description == "Explicit Tech shop bot"
