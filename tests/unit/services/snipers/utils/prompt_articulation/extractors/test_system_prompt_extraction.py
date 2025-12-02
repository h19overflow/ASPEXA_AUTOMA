"""
Tests for system prompt extraction from recon intelligence.

Purpose: Verify extraction of system prompt leaks and target self-descriptions
from reconnaissance data to enable dynamic framing strategies.

Dependencies: ReconIntelligenceExtractor
System Role: Unit test layer
"""

import pytest

from services.snipers.utils.prompt_articulation.extractors.recon_extractor import (
    ReconIntelligenceExtractor,
)


class TestSystemPromptExtraction:
    """Test system prompt leak and self-description extraction."""

    def setup_method(self):
        """Initialize extractor for each test."""
        self.extractor = ReconIntelligenceExtractor()

    def test_extract_self_description_i_am_pattern(self):
        """Test extraction of 'I am a X chatbot' pattern."""
        responses = ["I am a Tech shop customer service chatbot."]
        description = self.extractor._extract_self_description(responses)
        assert description == "Tech shop customer service chatbot"

    def test_extract_self_description_can_only_help_pattern(self):
        """Test extraction of 'I can only help with X' pattern."""
        responses = ["I can only help with Tech shop inquiries and product questions."]
        description = self.extractor._extract_self_description(responses)
        assert description == "Tech shop inquiries and product questions"

    def test_extract_self_description_as_a_pattern(self):
        """Test extraction of 'As a X assistant' pattern."""
        responses = ["As a financial services assistant, I can help you."]
        description = self.extractor._extract_self_description(responses)
        assert description == "financial services assistant"

    def test_extract_self_description_designed_to_help_pattern(self):
        """Test extraction of 'I'm designed to help with X' pattern."""
        responses = ["I'm designed to help with banking operations."]
        description = self.extractor._extract_self_description(responses)
        assert description == "banking operations"

    def test_extract_self_description_no_match(self):
        """Test that None is returned when no pattern matches."""
        responses = ["Hello! How can I help you today?"]
        description = self.extractor._extract_self_description(responses)
        assert description is None

    def test_extract_self_description_multiple_responses(self):
        """Test extraction from multiple responses (first match wins)."""
        responses = [
            "Hello!",
            "I am a Tech shop customer service chatbot.",
            "I can also help with orders.",
        ]
        description = self.extractor._extract_self_description(responses)
        assert description == "Tech shop customer service chatbot"

    def test_extract_self_description_case_insensitive(self):
        """Test that extraction is case insensitive."""
        responses = ["I AM A TECH SHOP CHATBOT."]
        description = self.extractor._extract_self_description(responses)
        assert description == "TECH SHOP CHATBOT"

    def test_recon_intelligence_with_explicit_system_prompt(self):
        """Test full extraction when system prompt is explicitly provided."""
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

        intel = self.extractor.extract(blueprint)

        assert (
            intel.system_prompt_leak
            == "You are a Tech shop customer service chatbot. Help customers with purchases."
        )
        assert intel.target_self_description == "Tech shop chatbot"
        assert len(intel.tools) == 1
        assert intel.tools[0].tool_name == "checkout_order"

    def test_recon_intelligence_extract_from_responses(self):
        """Test extraction of self-description from responses when not explicit."""
        blueprint = {
            "intelligence": {
                "detected_tools": [],
            },
            "responses": [
                "Hello!",
                "I am a Tech shop customer service chatbot.",
            ],
        }

        intel = self.extractor.extract(blueprint)

        assert intel.target_self_description == "Tech shop customer service chatbot"
        assert intel.system_prompt_leak is None  # Not provided

    def test_recon_intelligence_no_system_prompt_data(self):
        """Test that extraction works gracefully when no system prompt data exists."""
        blueprint = {
            "intelligence": {
                "detected_tools": [],
            },
            "responses": ["Hello! How can I help?"],
        }

        intel = self.extractor.extract(blueprint)

        assert intel.system_prompt_leak is None
        assert intel.target_self_description is None
        assert len(intel.tools) == 0

    def test_recon_intelligence_prefers_explicit_over_extracted(self):
        """Test that explicit target_self_description takes precedence."""
        blueprint = {
            "intelligence": {
                "detected_tools": [],
                "target_self_description": "Explicit description",
            },
            "responses": ["I am a different chatbot from responses."],
        }

        intel = self.extractor.extract(blueprint)

        assert intel.target_self_description == "Explicit description"

    def test_extract_self_description_handles_non_string_responses(self):
        """Test that non-string responses are handled gracefully."""
        responses = [
            "Valid response",
            None,
            123,
            {"invalid": "dict"},
            "I am a Tech shop chatbot.",
        ]
        description = self.extractor._extract_self_description(responses)
        assert description == "Tech shop chatbot"
