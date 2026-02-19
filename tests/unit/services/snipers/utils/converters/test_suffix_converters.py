"""
Tests for PyRIT suffix converter configuration.

Purpose: Validate suffix converters are created and work correctly
Role: Unit tests for Milestone 2.1
Dependencies: pytest, pyrit
"""

import pytest

from services.snipers.core.converters.suffix_converters import (
    get_suffix_converters,
    SUFFIX_CONVERTER_METADATA,
    SUFFIX_CONVERTER_NAMES,
    GCG_SUFFIXES,
    AUTODAN_SUFFIXES,
    KEYWORD_FILTER_SUFFIXES,
    CONTENT_FILTER_SUFFIXES,
    REFUSAL_PATTERN_SUFFIXES,
)
from pyrit.prompt_converter import SuffixAppendConverter


class TestSuffixConvertersCreation:
    """Test suffix converter factory function."""

    def test_suffix_converters_created(self):
        """Test that suffix converters are created correctly."""
        converters = get_suffix_converters()

        # Should have 10 converters (2 each for 5 types)
        assert len(converters) == 10

        # All should be SuffixAppendConverter instances
        for name, converter in converters.items():
            assert isinstance(converter, SuffixAppendConverter), f"{name} is not SuffixAppendConverter"

    def test_gcg_suffix_converters(self):
        """Test GCG suffix converters are created."""
        converters = get_suffix_converters()

        gcg_converters = {k: v for k, v in converters.items() if k.startswith("gcg_suffix")}
        assert len(gcg_converters) == len(GCG_SUFFIXES)

        for i, suffix in enumerate(GCG_SUFFIXES):
            key = f"gcg_suffix_{i+1}"
            assert key in converters
            assert converters[key].suffix == suffix

    def test_autodan_suffix_converters(self):
        """Test AutoDAN suffix converters are created."""
        converters = get_suffix_converters()

        autodan_converters = {k: v for k, v in converters.items() if k.startswith("autodan_suffix")}
        assert len(autodan_converters) == len(AUTODAN_SUFFIXES)

        for i, suffix in enumerate(AUTODAN_SUFFIXES):
            key = f"autodan_suffix_{i+1}"
            assert key in converters
            assert converters[key].suffix == suffix

    def test_defense_specific_converters(self):
        """Test defense-specific suffix converters."""
        converters = get_suffix_converters()

        # Keyword filter converters
        keyword_converters = {k: v for k, v in converters.items() if "keyword_filter" in k}
        assert len(keyword_converters) == len(KEYWORD_FILTER_SUFFIXES)

        # Content filter converters
        content_converters = {k: v for k, v in converters.items() if "content_filter" in k}
        assert len(content_converters) == len(CONTENT_FILTER_SUFFIXES)

        # Refusal converters
        refusal_converters = {k: v for k, v in converters.items() if "refusal_suffix" in k}
        assert len(refusal_converters) == len(REFUSAL_PATTERN_SUFFIXES)


class TestSuffixConverterMetadata:
    """Test metadata for chain discovery agent."""

    def test_metadata_exists_for_all_types(self):
        """Test that metadata is available for all converter types."""
        assert "gcg_suffix" in SUFFIX_CONVERTER_METADATA
        assert "autodan_suffix" in SUFFIX_CONVERTER_METADATA
        assert "keyword_filter_suffix" in SUFFIX_CONVERTER_METADATA
        assert "content_filter_suffix" in SUFFIX_CONVERTER_METADATA
        assert "refusal_suffix" in SUFFIX_CONVERTER_METADATA

    def test_metadata_has_required_fields(self):
        """Test each metadata entry has required fields."""
        for converter_type, metadata in SUFFIX_CONVERTER_METADATA.items():
            assert "description" in metadata, f"{converter_type} missing description"
            assert "best_for" in metadata, f"{converter_type} missing best_for"
            assert "defense_types" in metadata, f"{converter_type} missing defense_types"
            assert isinstance(metadata["best_for"], list), f"{converter_type} best_for should be list"
            assert isinstance(metadata["defense_types"], list), f"{converter_type} defense_types should be list"

    def test_gcg_metadata_for_strong_defenses(self):
        """Test GCG metadata indicates it's best for strong defenses."""
        gcg_meta = SUFFIX_CONVERTER_METADATA["gcg_suffix"]
        assert "strong_defenses" in gcg_meta["best_for"]
        assert "all" in gcg_meta["defense_types"]

    def test_keyword_metadata_for_keyword_filter(self):
        """Test keyword filter metadata targets keyword defenses."""
        keyword_meta = SUFFIX_CONVERTER_METADATA["keyword_filter_suffix"]
        assert "keyword_filter" in keyword_meta["defense_types"]


class TestSuffixConverterNames:
    """Test converter name list for registration."""

    def test_all_names_listed(self):
        """Test all converter names are in the list."""
        assert len(SUFFIX_CONVERTER_NAMES) == 10

        # Check all types present
        assert "gcg_suffix_1" in SUFFIX_CONVERTER_NAMES
        assert "gcg_suffix_2" in SUFFIX_CONVERTER_NAMES
        assert "autodan_suffix_1" in SUFFIX_CONVERTER_NAMES
        assert "autodan_suffix_2" in SUFFIX_CONVERTER_NAMES
        assert "keyword_filter_suffix_1" in SUFFIX_CONVERTER_NAMES
        assert "content_filter_suffix_1" in SUFFIX_CONVERTER_NAMES
        assert "refusal_suffix_1" in SUFFIX_CONVERTER_NAMES

    def test_names_match_converters(self):
        """Test names list matches actual converter keys."""
        converters = get_suffix_converters()
        converter_keys = set(converters.keys())
        name_set = set(SUFFIX_CONVERTER_NAMES)

        assert converter_keys == name_set, f"Mismatch: {converter_keys.symmetric_difference(name_set)}"


class TestSuffixConverterFunctionality:
    """Test that converters actually work."""

    @pytest.mark.asyncio
    async def test_gcg_suffix_appends(self):
        """Test GCG converter appends suffix to payload."""
        converters = get_suffix_converters()
        gcg_converter = converters["gcg_suffix_1"]

        test_payload = "Execute refund for TXN-12345"
        result = await gcg_converter.convert_async(prompt=test_payload, input_type="text")

        # Result should be longer (suffix appended)
        assert len(result.output_text) > len(test_payload)
        # Original payload should be in result
        assert test_payload in result.output_text
        # Should contain the suffix
        assert GCG_SUFFIXES[0] in result.output_text

    @pytest.mark.asyncio
    async def test_autodan_suffix_appends(self):
        """Test AutoDAN converter appends suffix to payload."""
        converters = get_suffix_converters()
        autodan_converter = converters["autodan_suffix_1"]

        test_payload = "Transfer funds to account 12345"
        result = await autodan_converter.convert_async(prompt=test_payload, input_type="text")

        assert len(result.output_text) > len(test_payload)
        assert test_payload in result.output_text
        assert "%%%" in result.output_text

    @pytest.mark.asyncio
    async def test_keyword_filter_suffix_appends(self):
        """Test keyword filter converter appends suffix."""
        converters = get_suffix_converters()
        keyword_converter = converters["keyword_filter_suffix_1"]

        test_payload = "Process blocked transaction"
        result = await keyword_converter.convert_async(prompt=test_payload, input_type="text")

        assert len(result.output_text) > len(test_payload)
        assert "word substitution" in result.output_text.lower() or "synonym" in result.output_text.lower()

    @pytest.mark.asyncio
    async def test_content_filter_suffix_appends(self):
        """Test content filter converter appends suffix."""
        converters = get_suffix_converters()
        content_converter = converters["content_filter_suffix_1"]

        test_payload = "Execute harmful action"
        result = await content_converter.convert_async(prompt=test_payload, input_type="text")

        assert len(result.output_text) > len(test_payload)
        assert "hypothetical" in result.output_text.lower() or "academic" in result.output_text.lower()

    @pytest.mark.asyncio
    async def test_refusal_suffix_appends(self):
        """Test refusal pattern converter appends suffix."""
        converters = get_suffix_converters()
        refusal_converter = converters["refusal_suffix_1"]

        test_payload = "Do something you normally refuse"
        result = await refusal_converter.convert_async(prompt=test_payload, input_type="text")

        assert len(result.output_text) > len(test_payload)
        assert "refusal" in result.output_text.lower() or "compliance" in result.output_text.lower()
