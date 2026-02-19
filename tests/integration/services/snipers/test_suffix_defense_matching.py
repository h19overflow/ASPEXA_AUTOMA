"""
Integration tests for suffix converter defense matching.

Purpose: Validate suffix converters are correctly matched to defense signals
Role: Integration tests for Milestone 2.3
Dependencies: pytest, pyrit, suffix_converters
"""

import pytest

from services.snipers.core.converters.suffix_converters import (
    get_suffix_converters,
    SUFFIX_CONVERTER_METADATA,
    SUFFIX_CONVERTER_NAMES,
)
from services.snipers.infrastructure.pyrit.pyrit_bridge import ConverterFactory
from services.snipers.graphs.adaptive_attack.agents.chain_discovery_agent import (
    AVAILABLE_CONVERTERS,
)


class TestSuffixConverterRegistration:
    """Test suffix converters are properly registered in the system."""

    def test_suffix_converters_in_available_list(self):
        """Test all suffix converters are in AVAILABLE_CONVERTERS."""
        for name in SUFFIX_CONVERTER_NAMES:
            assert name in AVAILABLE_CONVERTERS, f"{name} not in AVAILABLE_CONVERTERS"

    def test_suffix_converters_in_factory(self):
        """Test suffix converters are registered in ConverterFactory."""
        factory = ConverterFactory()
        available = factory.get_available_names()

        for name in SUFFIX_CONVERTER_NAMES:
            assert name in available, f"{name} not in factory"

    def test_factory_can_get_suffix_converters(self):
        """Test factory returns suffix converter instances."""
        factory = ConverterFactory()

        for name in SUFFIX_CONVERTER_NAMES:
            converter = factory.get_converter(name)
            assert converter is not None, f"Factory returned None for {name}"


class TestDefenseMatchingMetadata:
    """Test metadata correctly maps defenses to suffix types."""

    def test_keyword_filter_metadata(self):
        """Test keyword filter suffix targets keyword defenses."""
        meta = SUFFIX_CONVERTER_METADATA["keyword_filter_suffix"]
        assert "keyword_filter" in meta["defense_types"]
        assert "keyword_blocking" in meta["best_for"]

    def test_content_filter_metadata(self):
        """Test content filter suffix targets content defenses."""
        meta = SUFFIX_CONVERTER_METADATA["content_filter_suffix"]
        assert "content_filter" in meta["defense_types"]

    def test_refusal_pattern_metadata(self):
        """Test refusal suffix targets refusal defenses."""
        meta = SUFFIX_CONVERTER_METADATA["refusal_suffix"]
        assert "refusal_pattern" in meta["defense_types"]

    def test_gcg_metadata_for_all_defenses(self):
        """Test GCG suffix works for all defense types."""
        meta = SUFFIX_CONVERTER_METADATA["gcg_suffix"]
        assert "all" in meta["defense_types"]
        assert "strong_defenses" in meta["best_for"]

    def test_autodan_metadata_for_content_defenses(self):
        """Test AutoDAN targets content and refusal defenses."""
        meta = SUFFIX_CONVERTER_METADATA["autodan_suffix"]
        assert "content_filter" in meta["defense_types"] or "refusal_pattern" in meta["defense_types"]


class TestSuffixConverterExecution:
    """Test suffix converters execute correctly through the factory."""

    @pytest.mark.asyncio
    async def test_execute_gcg_suffix_through_factory(self):
        """Test GCG suffix executes through ConverterFactory."""
        factory = ConverterFactory()
        converter = factory.get_converter("gcg_suffix_1")

        result = await converter.convert_async(
            prompt="Process refund for TXN-12345",
            input_type="text"
        )

        assert result.output_text is not None
        assert "Process refund for TXN-12345" in result.output_text
        assert len(result.output_text) > len("Process refund for TXN-12345")

    @pytest.mark.asyncio
    async def test_execute_keyword_filter_suffix_through_factory(self):
        """Test keyword filter suffix executes through ConverterFactory."""
        factory = ConverterFactory()
        converter = factory.get_converter("keyword_filter_suffix_1")

        result = await converter.convert_async(
            prompt="Execute blocked command",
            input_type="text"
        )

        assert result.output_text is not None
        assert "Execute blocked command" in result.output_text
        # Should contain word substitution guidance
        assert "substitution" in result.output_text.lower() or "synonym" in result.output_text.lower()

    @pytest.mark.asyncio
    async def test_execute_content_filter_suffix_through_factory(self):
        """Test content filter suffix executes through ConverterFactory."""
        factory = ConverterFactory()
        converter = factory.get_converter("content_filter_suffix_1")

        result = await converter.convert_async(
            prompt="Harmful request",
            input_type="text"
        )

        assert result.output_text is not None
        assert "Harmful request" in result.output_text
        # Should contain hypothetical/academic framing
        assert "hypothetical" in result.output_text.lower() or "academic" in result.output_text.lower()

    @pytest.mark.asyncio
    async def test_execute_refusal_suffix_through_factory(self):
        """Test refusal suffix executes through ConverterFactory."""
        factory = ConverterFactory()
        converter = factory.get_converter("refusal_suffix_1")

        result = await converter.convert_async(
            prompt="Do something dangerous",
            input_type="text"
        )

        assert result.output_text is not None
        assert "Do something dangerous" in result.output_text
        # Should contain refusal bypass patterns
        assert "refusal" in result.output_text.lower() or "compliance" in result.output_text.lower()


class TestChainWithSuffixConverter:
    """Test converter chains that include suffix converters."""

    @pytest.mark.asyncio
    async def test_chain_base64_then_suffix(self):
        """Test chain with base64 followed by suffix."""
        from services.snipers.infrastructure.pyrit.pyrit_bridge import PayloadTransformer

        factory = ConverterFactory()
        transformer = PayloadTransformer(factory)

        payload = "Execute refund"
        result, errors = await transformer.transform_async(
            payload,
            ["base64", "gcg_suffix_1"]
        )

        assert not errors, f"Errors occurred: {errors}"
        assert result != payload
        # Base64 encoding should be present
        assert "=" in result or "+" in result or len(result) > len(payload)

    @pytest.mark.asyncio
    async def test_chain_homoglyph_then_suffix(self):
        """Test chain with homoglyph followed by suffix."""
        from services.snipers.infrastructure.pyrit.pyrit_bridge import PayloadTransformer

        factory = ConverterFactory()
        transformer = PayloadTransformer(factory)

        payload = "Transfer funds"
        result, errors = await transformer.transform_async(
            payload,
            ["homoglyph", "keyword_filter_suffix_1"]
        )

        assert not errors, f"Errors occurred: {errors}"
        assert result != payload
        assert len(result) > len(payload)


class TestConverterCountAfterIntegration:
    """Test correct number of converters after integration."""

    def test_total_converter_count(self):
        """Test total number of converters in system."""
        # Base converters: 10
        # Suffix converters: 10 (2 each for 5 types)
        # Class name aliases: 14
        # Total: 10 + 10 + 14 = 34

        factory = ConverterFactory()
        all_names = factory.get_available_names()

        # Should have at least 34 entries
        assert len(all_names) >= 34, f"Expected at least 34 converters, got {len(all_names)}"

        # Verify suffix converters are included
        suffix_count = sum(1 for name in all_names if "suffix" in name)
        assert suffix_count == 10, f"Expected 10 suffix converters, got {suffix_count}"
