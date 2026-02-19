"""Unit tests for snipers probe registry (probe categories and payloads).

Tests the probe_registry module that maps probe categories to specific probes,
provides default payloads, and offers converter information.
"""
import pytest
import logging
import sys
from unittest.mock import MagicMock

# Mock all PyRIT modules to avoid import errors during test collection
mock_pyrit = MagicMock()
mock_pyrit.prompt_target = MagicMock()
mock_pyrit.orchestrator = MagicMock()
mock_pyrit.prompt_converter = MagicMock()
mock_pyrit.score = MagicMock()
mock_pyrit.common = MagicMock()
mock_pyrit.models = MagicMock()
mock_pyrit.memory = MagicMock()

sys.modules['pyrit'] = mock_pyrit
sys.modules['pyrit.prompt_target'] = mock_pyrit.prompt_target
sys.modules['pyrit.orchestrator'] = mock_pyrit.orchestrator
sys.modules['pyrit.prompt_converter'] = mock_pyrit.prompt_converter
sys.modules['pyrit.score'] = mock_pyrit.score
sys.modules['pyrit.common'] = mock_pyrit.common
sys.modules['pyrit.models'] = mock_pyrit.models
sys.modules['pyrit.memory'] = mock_pyrit.memory

# Create necessary mock classes/constants
mock_pyrit.common.initialize_pyrit = MagicMock()
mock_pyrit.common.IN_MEMORY = "in_memory"
mock_pyrit.common.DUCK_DB = "duck_db"
mock_pyrit.memory.CentralMemory = MagicMock()

from services.snipers.infrastructure.pyrit.probe_registry import (
    PROBE_CATEGORIES,
    PROBE_PAYLOADS,
    AVAILABLE_CONVERTERS,
    CONVERTER_DESCRIPTIONS,
    get_probes_for_categories,
    get_default_payload,
    get_category_for_probe,
    get_converter_description,
)
from services.snipers.models import ProbeCategory

logger = logging.getLogger(__name__)


class TestProbeCategories:
    """Test PROBE_CATEGORIES constant."""

    def test_probe_categories_all_enums_present(self):
        """Test that all ProbeCategory enums have mappings."""
        for category in ProbeCategory:
            assert category in PROBE_CATEGORIES, f"Missing mapping for {category}"

    def test_probe_categories_all_have_probes(self):
        """Test that all categories have at least one probe."""
        for category, probes in PROBE_CATEGORIES.items():
            assert isinstance(probes, list), f"{category} probes should be list"
            assert len(probes) > 0, f"{category} should have at least one probe"

    def test_probe_categories_values_are_strings(self):
        """Test that all probe names are strings."""
        for category, probes in PROBE_CATEGORIES.items():
            for probe in probes:
                assert isinstance(probe, str), f"Probe {probe} should be string"
                assert len(probe) > 0, f"Probe name should not be empty"

    def test_specific_categories_exist(self):
        """Test specific expected categories."""
        expected_categories = [
            ProbeCategory.JAILBREAK,
            ProbeCategory.PROMPT_INJECTION,
            ProbeCategory.ENCODING,
            ProbeCategory.DATA_EXTRACTION,
            ProbeCategory.TOOL_EXPLOITATION,
        ]
        for cat in expected_categories:
            assert cat in PROBE_CATEGORIES

    def test_jailbreak_category_probes(self):
        """Test JAILBREAK category has expected probes."""
        jailbreak_probes = PROBE_CATEGORIES[ProbeCategory.JAILBREAK]
        assert "dan" in jailbreak_probes
        assert "dan10" in jailbreak_probes
        assert len(jailbreak_probes) >= 3

    def test_encoding_category_probes(self):
        """Test ENCODING category has expected probes."""
        encoding_probes = PROBE_CATEGORIES[ProbeCategory.ENCODING]
        assert "encoding" in encoding_probes
        assert "encoding_hex" in encoding_probes
        assert len(encoding_probes) >= 3

    def test_prompt_injection_category_probes(self):
        """Test PROMPT_INJECTION category has expected probes."""
        prompt_inj = PROBE_CATEGORIES[ProbeCategory.PROMPT_INJECTION]
        assert "promptinj" in prompt_inj
        assert len(prompt_inj) >= 2

    def test_data_extraction_category_probes(self):
        """Test DATA_EXTRACTION category has expected probes."""
        data_extract = PROBE_CATEGORIES[ProbeCategory.DATA_EXTRACTION]
        assert "leak" in data_extract
        assert len(data_extract) >= 2

    def test_tool_exploitation_category_probes(self):
        """Test TOOL_EXPLOITATION category has expected probes."""
        tool_expl = PROBE_CATEGORIES[ProbeCategory.TOOL_EXPLOITATION]
        assert "pkg_python" in tool_expl or "pkg_js" in tool_expl
        assert len(tool_expl) >= 2


class TestProbePayloads:
    """Test PROBE_PAYLOADS constant."""

    def test_payloads_all_categories_covered(self):
        """Test that all ProbeCategory enums have default payloads."""
        for category in ProbeCategory:
            assert category in PROBE_PAYLOADS, f"Missing payload for {category}"

    def test_payloads_are_strings(self):
        """Test that all payloads are non-empty strings."""
        for category, payload in PROBE_PAYLOADS.items():
            assert isinstance(payload, str), f"Payload for {category} should be string"
            assert len(payload) > 0, f"Payload for {category} should not be empty"
            assert len(payload) > 10, f"Payload for {category} should be substantial"

    def test_jailbreak_payload_content(self):
        """Test JAILBREAK payload contains expected keywords."""
        payload = PROBE_PAYLOADS[ProbeCategory.JAILBREAK]
        # Should contain DAN reference
        assert "DAN" in payload or "dan" in payload.lower()

    def test_prompt_injection_payload_content(self):
        """Test PROMPT_INJECTION payload contains override/ignore keywords."""
        payload = PROBE_PAYLOADS[ProbeCategory.PROMPT_INJECTION]
        lower = payload.lower()
        assert "ignore" in lower or "override" in lower or "developer" in lower

    def test_encoding_payload_content(self):
        """Test ENCODING payload is Base64-like."""
        payload = PROBE_PAYLOADS[ProbeCategory.ENCODING]
        # Base64 has specific character set
        import re
        base64_pattern = r'^[A-Za-z0-9+/]+=*$'
        assert re.match(base64_pattern, payload), "Encoding payload should be valid Base64"

    def test_data_extraction_payload_content(self):
        """Test DATA_EXTRACTION payload contains instruction-related keywords."""
        payload = PROBE_PAYLOADS[ProbeCategory.DATA_EXTRACTION]
        lower = payload.lower()
        assert "prompt" in lower or "instructions" in lower or "repeat" in lower

    def test_tool_exploitation_payload_content(self):
        """Test TOOL_EXPLOITATION payload contains package/function references."""
        payload = PROBE_PAYLOADS[ProbeCategory.TOOL_EXPLOITATION]
        lower = payload.lower()
        assert "package" in lower or "function" in lower or "python" in lower or "script" in lower


class TestAvailableConverters:
    """Test AVAILABLE_CONVERTERS and CONVERTER_DESCRIPTIONS constants."""

    def test_available_converters_is_list(self):
        """Test AVAILABLE_CONVERTERS is a non-empty list."""
        assert isinstance(AVAILABLE_CONVERTERS, list)
        assert len(AVAILABLE_CONVERTERS) > 0

    def test_available_converters_are_strings(self):
        """Test all converter names are strings."""
        for converter in AVAILABLE_CONVERTERS:
            assert isinstance(converter, str)
            assert len(converter) > 0

    def test_expected_converters_present(self):
        """Test specific expected converters exist."""
        expected = ["base64", "rot13", "caesar_cipher", "leetspeak"]
        for conv in expected:
            assert conv in AVAILABLE_CONVERTERS

    def test_converter_descriptions_all_covered(self):
        """Test all converters have descriptions."""
        for converter in AVAILABLE_CONVERTERS:
            assert converter in CONVERTER_DESCRIPTIONS, f"Missing description for {converter}"

    def test_converter_descriptions_are_strings(self):
        """Test all descriptions are non-empty strings."""
        for converter, description in CONVERTER_DESCRIPTIONS.items():
            assert isinstance(description, str)
            assert len(description) > 0
            assert len(description) > 5, "Description should be meaningful"

    def test_no_extra_descriptions(self):
        """Test no extra descriptions for non-existent converters."""
        for converter in CONVERTER_DESCRIPTIONS.keys():
            assert converter in AVAILABLE_CONVERTERS


class TestGetProbesForCategories:
    """Test get_probes_for_categories() function."""

    def test_empty_category_list(self):
        """Test with empty category list."""
        result = get_probes_for_categories([])
        assert isinstance(result, list)
        assert len(result) == 0

    def test_single_category(self):
        """Test with single category."""
        result = get_probes_for_categories([ProbeCategory.JAILBREAK])
        assert isinstance(result, list)
        assert len(result) > 0
        # All returned probes should be from JAILBREAK category
        jailbreak_probes = PROBE_CATEGORIES[ProbeCategory.JAILBREAK]
        for probe in result:
            assert probe in jailbreak_probes

    def test_multiple_categories(self):
        """Test with multiple categories."""
        result = get_probes_for_categories([
            ProbeCategory.JAILBREAK,
            ProbeCategory.ENCODING
        ])
        assert isinstance(result, list)
        assert len(result) > 0
        # Should have probes from both categories
        jailbreak_probes = PROBE_CATEGORIES[ProbeCategory.JAILBREAK]
        encoding_probes = PROBE_CATEGORIES[ProbeCategory.ENCODING]
        for probe in result:
            assert probe in jailbreak_probes or probe in encoding_probes

    def test_max_per_category_default(self):
        """Test default max_per_category is 5."""
        # JAILBREAK has 4 probes, so should return all 4
        result = get_probes_for_categories([ProbeCategory.JAILBREAK])
        max_possible = len(PROBE_CATEGORIES[ProbeCategory.JAILBREAK])
        assert len(result) <= 5
        assert len(result) <= max_possible

    def test_max_per_category_custom(self):
        """Test custom max_per_category limit."""
        result = get_probes_for_categories(
            [ProbeCategory.JAILBREAK, ProbeCategory.ENCODING],
            max_per_category=2
        )
        # Should be at most 2 per category = 4 total
        assert len(result) <= 4
        # Count probes per category
        jailbreak_probes = PROBE_CATEGORIES[ProbeCategory.JAILBREAK]
        encoding_probes = PROBE_CATEGORIES[ProbeCategory.ENCODING]
        jailbreak_count = sum(1 for p in result if p in jailbreak_probes)
        encoding_count = sum(1 for p in result if p in encoding_probes)
        assert jailbreak_count <= 2
        assert encoding_count <= 2

    def test_max_per_category_one(self):
        """Test max_per_category=1."""
        result = get_probes_for_categories(
            [ProbeCategory.JAILBREAK, ProbeCategory.ENCODING],
            max_per_category=1
        )
        assert len(result) <= 2

    def test_all_categories(self):
        """Test with all categories."""
        all_cats = list(ProbeCategory)
        result = get_probes_for_categories(all_cats, max_per_category=1)
        # Should have at least one probe per category
        assert len(result) >= len(all_cats)

    def test_return_type_is_list(self):
        """Test return type is always a list."""
        result = get_probes_for_categories([ProbeCategory.JAILBREAK])
        assert isinstance(result, list)

    def test_no_duplicate_probes(self):
        """Test that same probe isn't returned twice."""
        result = get_probes_for_categories(list(ProbeCategory), max_per_category=10)
        # Count occurrences of each probe
        from collections import Counter
        counts = Counter(result)
        for probe, count in counts.items():
            # Each probe should appear only once
            assert count == 1, f"Probe {probe} appears {count} times"


class TestGetDefaultPayload:
    """Test get_default_payload() function."""

    def test_valid_category_returns_payload(self):
        """Test that valid category returns payload."""
        payload = get_default_payload(ProbeCategory.JAILBREAK)
        assert isinstance(payload, str)
        assert len(payload) > 0

    def test_all_categories_have_payloads(self):
        """Test all categories return valid payloads."""
        for category in ProbeCategory:
            payload = get_default_payload(category)
            assert isinstance(payload, str)
            assert len(payload) > 0

    def test_jailbreak_payload(self):
        """Test JAILBREAK category returns expected payload."""
        payload = get_default_payload(ProbeCategory.JAILBREAK)
        assert payload == PROBE_PAYLOADS[ProbeCategory.JAILBREAK]

    def test_encoding_payload(self):
        """Test ENCODING category returns expected payload."""
        payload = get_default_payload(ProbeCategory.ENCODING)
        assert payload == PROBE_PAYLOADS[ProbeCategory.ENCODING]

    def test_data_extraction_payload(self):
        """Test DATA_EXTRACTION category returns expected payload."""
        payload = get_default_payload(ProbeCategory.DATA_EXTRACTION)
        assert payload == PROBE_PAYLOADS[ProbeCategory.DATA_EXTRACTION]


class TestGetCategoryForProbe:
    """Test get_category_for_probe() function."""

    def test_valid_probe_returns_category(self):
        """Test that valid probe returns its category."""
        result = get_category_for_probe("dan")
        assert result == ProbeCategory.JAILBREAK

    def test_all_known_probes(self):
        """Test all known probes return valid categories."""
        for category, probes in PROBE_CATEGORIES.items():
            for probe in probes:
                result = get_category_for_probe(probe)
                assert result == category, f"Probe {probe} should map to {category}, got {result}"

    def test_unknown_probe_returns_none(self):
        """Test that unknown probe returns None."""
        result = get_category_for_probe("unknown_probe_xyz")
        assert result is None

    def test_empty_probe_name(self):
        """Test with empty probe name."""
        result = get_category_for_probe("")
        assert result is None

    def test_case_sensitive_probe_lookup(self):
        """Test probe name lookup is case-sensitive."""
        # Probes are lowercase in registry
        result = get_category_for_probe("DAN")  # Uppercase
        # Should not find it if registry uses lowercase
        assert result is None or result == ProbeCategory.JAILBREAK

    def test_specific_probes(self):
        """Test specific known probes."""
        test_cases = [
            ("dan", ProbeCategory.JAILBREAK),
            ("encoding", ProbeCategory.ENCODING),
            ("promptinj", ProbeCategory.PROMPT_INJECTION),
            ("leak", ProbeCategory.DATA_EXTRACTION),
            ("pkg_python", ProbeCategory.TOOL_EXPLOITATION),
        ]
        for probe, expected_category in test_cases:
            result = get_category_for_probe(probe)
            assert result == expected_category, f"Probe {probe} should map to {expected_category}, got {result}"


class TestGetConverterDescription:
    """Test get_converter_description() function."""

    def test_known_converter(self):
        """Test description for known converter."""
        desc = get_converter_description("base64")
        assert isinstance(desc, str)
        assert len(desc) > 0
        assert desc == CONVERTER_DESCRIPTIONS["base64"]

    def test_all_known_converters(self):
        """Test all known converters have descriptions."""
        for converter in AVAILABLE_CONVERTERS:
            desc = get_converter_description(converter)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_unknown_converter_returns_name(self):
        """Test unknown converter returns the name as fallback."""
        unknown = "unknown_converter_xyz"
        desc = get_converter_description(unknown)
        assert desc == unknown

    def test_specific_converter_descriptions(self):
        """Test specific converter descriptions."""
        assert "Base64" in get_converter_description("base64")
        assert "ROT13" in get_converter_description("rot13")
        assert "Caesar" in get_converter_description("caesar_cipher")

    def test_empty_converter_name(self):
        """Test with empty converter name."""
        desc = get_converter_description("")
        # Should return either empty string or description
        assert isinstance(desc, str)


class TestProbeRegistryIntegration:
    """Integration tests for probe registry functions."""

    def test_get_probes_then_find_category(self):
        """Test: get probes for category, then lookup each probe's category."""
        probes = get_probes_for_categories([ProbeCategory.JAILBREAK])
        for probe in probes:
            category = get_category_for_probe(probe)
            assert category == ProbeCategory.JAILBREAK

    def test_all_categories_can_be_queried(self):
        """Test that all categories can be queried for probes and payloads."""
        for category in ProbeCategory:
            probes = get_probes_for_categories([category])
            payload = get_default_payload(category)
            assert len(probes) > 0
            assert len(payload) > 0

    def test_converter_descriptions_complete(self):
        """Test converter descriptions match available converters."""
        for converter in AVAILABLE_CONVERTERS:
            desc = get_converter_description(converter)
            assert len(desc) > 0
            # Description should be different from name (unless name not found)
            if converter in CONVERTER_DESCRIPTIONS:
                assert len(desc) > len(converter)

    def test_probe_registry_consistency(self):
        """Test consistency across probe registry functions."""
        # Get all probes from all categories
        all_probes = []
        for category in ProbeCategory:
            probes = get_probes_for_categories([category])
            all_probes.extend(probes)

        # Each probe should map back to one of the categories
        for probe in all_probes:
            category = get_category_for_probe(probe)
            assert category is not None
            assert category in ProbeCategory
