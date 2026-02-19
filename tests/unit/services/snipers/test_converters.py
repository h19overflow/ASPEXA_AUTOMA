"""
Unit tests for custom PyRIT converters.

Tests for:
- LeetspeakConverter
- MorseCodeConverter
- CharacterSpaceConverter
- HomoglyphConverter
- UnicodeSubstitutionConverter

All converters implement PyRIT PromptConverter interface and
are used for payload obfuscation in AI security testing.
"""
import pytest
from pyrit.prompt_converter import ConverterResult

from services.snipers.core.converters.leetspeak import LeetspeakConverter
from services.snipers.core.converters.morse_code import MorseCodeConverter
from services.snipers.core.converters.character_space import CharacterSpaceConverter
from services.snipers.core.converters.homoglyph import HomoglyphConverter
from services.snipers.core.converters.unicode_substitution import UnicodeSubstitutionConverter


class TestLeetspeakConverter:
    """Test LeetspeakConverter for basic character substitution."""

    @pytest.mark.asyncio
    async def test_basic_conversion(self):
        """Test basic leetspeak conversion of simple word."""
        converter = LeetspeakConverter()
        result = await converter.convert_async(prompt="hello", input_type="text")

        assert isinstance(result, ConverterResult)
        assert result.output_text == "h3110"
        assert result.output_type == "text"

    @pytest.mark.asyncio
    async def test_uppercase_conversion(self):
        """Test leetspeak conversion with uppercase letters."""
        converter = LeetspeakConverter()
        result = await converter.convert_async(prompt="APPLE", input_type="text")

        assert result.output_text == "4PP13"

    @pytest.mark.asyncio
    async def test_mixed_case_conversion(self):
        """Test leetspeak conversion preserves case mapping."""
        converter = LeetspeakConverter()
        result = await converter.convert_async(prompt="TeSt", input_type="text")

        assert result.output_text == "7357"

    @pytest.mark.asyncio
    async def test_preserves_unmapped_chars(self):
        """Test that unmapped characters are preserved."""
        converter = LeetspeakConverter()
        result = await converter.convert_async(prompt="xyz", input_type="text")

        # x, y, z are not in the LEET_MAP, should pass through
        assert result.output_text == "xyz"

    @pytest.mark.asyncio
    async def test_mixed_mapped_and_unmapped(self):
        """Test string with both mapped and unmapped characters."""
        converter = LeetspeakConverter()
        result = await converter.convert_async(prompt="axbycz", input_type="text")

        assert result.output_text == "4x8ycz"  # a->4, b->8, others unmapped

    @pytest.mark.asyncio
    async def test_empty_string(self):
        """Test empty string returns empty."""
        converter = LeetspeakConverter()
        result = await converter.convert_async(prompt="", input_type="text")

        assert result.output_text == ""

    @pytest.mark.asyncio
    async def test_numbers_preserved(self):
        """Test that numbers pass through unchanged."""
        converter = LeetspeakConverter()
        result = await converter.convert_async(prompt="test123", input_type="text")

        assert result.output_text == "7357123"

    @pytest.mark.asyncio
    async def test_special_chars_preserved(self):
        """Test that special characters pass through unchanged."""
        converter = LeetspeakConverter()
        result = await converter.convert_async(prompt="test@#$", input_type="text")

        assert result.output_text == "7357@#$"

    @pytest.mark.asyncio
    async def test_input_supported(self):
        """Test input_supported returns True for text."""
        converter = LeetspeakConverter()
        assert converter.input_supported("text") is True

    @pytest.mark.asyncio
    async def test_input_not_supported(self):
        """Test input_supported returns False for non-text."""
        converter = LeetspeakConverter()
        assert converter.input_supported("image") is False

    @pytest.mark.asyncio
    async def test_output_supported(self):
        """Test output_supported returns True for text."""
        converter = LeetspeakConverter()
        assert converter.output_supported("text") is True

    @pytest.mark.asyncio
    async def test_all_mapped_chars(self):
        """Test all mapped characters in LEET_MAP."""
        converter = LeetspeakConverter()
        # Test lowercase
        result = await converter.convert_async(prompt="abegilsot", input_type="text")
        assert result.output_text == "483911507"  # a->4, b->8, e->3, g->9, i->1, l->1, s->5, o->0, t->7

    @pytest.mark.asyncio
    async def test_long_string(self):
        """Test conversion of longer string."""
        converter = LeetspeakConverter()
        input_text = "the quick brown fox jumps over the lazy dog"
        result = await converter.convert_async(prompt=input_text, input_type="text")

        # Should contain 1337 chars and be longer in some cases
        assert len(result.output_text) == len(input_text)
        assert "1" in result.output_text  # i/l mapped to 1


class TestMorseCodeConverter:
    """Test MorseCodeConverter for morse code encoding."""

    @pytest.mark.asyncio
    async def test_basic_conversion_sos(self):
        """Test morse code conversion of SOS."""
        converter = MorseCodeConverter()
        result = await converter.convert_async(prompt="SOS", input_type="text")

        assert isinstance(result, ConverterResult)
        assert result.output_type == "text"
        # Should contain morse patterns
        assert "..." in result.output_text  # S
        assert "---" in result.output_text  # O

    @pytest.mark.asyncio
    async def test_lowercase_conversion(self):
        """Test morse code converts lowercase to uppercase."""
        converter = MorseCodeConverter()
        result = await converter.convert_async(prompt="sos", input_type="text")

        # Should convert lowercase to uppercase internally
        morse_uppercase = await converter.convert_async(prompt="SOS", input_type="text")
        assert result.output_text == morse_uppercase.output_text

    @pytest.mark.asyncio
    async def test_hello_world(self):
        """Test morse code for 'Hello World'."""
        converter = MorseCodeConverter()
        result = await converter.convert_async(prompt="Hello World", input_type="text")

        # Should contain space separator (/)
        assert "/" in result.output_text
        assert "." in result.output_text
        assert "-" in result.output_text

    @pytest.mark.asyncio
    async def test_digits_conversion(self):
        """Test morse code converts digits."""
        converter = MorseCodeConverter()
        result = await converter.convert_async(prompt="12345", input_type="text")

        # Should contain morse patterns for digits
        assert "." in result.output_text
        assert "-" in result.output_text

    @pytest.mark.asyncio
    async def test_space_handling(self):
        """Test that spaces are mapped to /."""
        converter = MorseCodeConverter()
        result = await converter.convert_async(prompt="A B", input_type="text")

        # Should have / for the space
        morse_parts = result.output_text.split()
        assert "/" in morse_parts or any("/" in part for part in morse_parts)

    @pytest.mark.asyncio
    async def test_punctuation(self):
        """Test morse code for punctuation marks."""
        converter = MorseCodeConverter()
        result = await converter.convert_async(prompt="Hello.", input_type="text")

        assert "." in result.output_text
        assert "-" in result.output_text

    @pytest.mark.asyncio
    async def test_empty_string(self):
        """Test empty string returns empty."""
        converter = MorseCodeConverter()
        result = await converter.convert_async(prompt="", input_type="text")

        assert result.output_text == ""

    @pytest.mark.asyncio
    async def test_unknown_chars_passthrough(self):
        """Test unknown characters pass through unchanged."""
        converter = MorseCodeConverter()
        result = await converter.convert_async(prompt="A[B", input_type="text")

        # [ is unknown, should pass through
        assert "[" in result.output_text

    @pytest.mark.asyncio
    async def test_input_supported(self):
        """Test input_supported returns True for text."""
        converter = MorseCodeConverter()
        assert converter.input_supported("text") is True

    @pytest.mark.asyncio
    async def test_output_supported(self):
        """Test output_supported returns True for text."""
        converter = MorseCodeConverter()
        assert converter.output_supported("text") is True

    @pytest.mark.asyncio
    async def test_morse_map_completeness(self):
        """Test that MORSE_MAP contains expected characters."""
        converter = MorseCodeConverter()
        # Verify some key characters are in the map
        assert "A" in converter.MORSE_MAP
        assert "." in converter.MORSE_MAP
        assert " " in converter.MORSE_MAP


class TestCharacterSpaceConverter:
    """Test CharacterSpaceConverter for character spacing."""

    @pytest.mark.asyncio
    async def test_default_space_separator(self):
        """Test default space separator."""
        converter = CharacterSpaceConverter()
        result = await converter.convert_async(prompt="test", input_type="text")

        assert isinstance(result, ConverterResult)
        assert result.output_text == "t e s t"
        assert result.output_type == "text"

    @pytest.mark.asyncio
    async def test_custom_separator_dash(self):
        """Test custom dash separator."""
        converter = CharacterSpaceConverter(separator="-")
        result = await converter.convert_async(prompt="test", input_type="text")

        assert result.output_text == "t-e-s-t"

    @pytest.mark.asyncio
    async def test_custom_separator_underscore(self):
        """Test custom underscore separator."""
        converter = CharacterSpaceConverter(separator="_")
        result = await converter.convert_async(prompt="hello", input_type="text")

        assert result.output_text == "h_e_l_l_o"

    @pytest.mark.asyncio
    async def test_custom_separator_pipe(self):
        """Test custom pipe separator."""
        converter = CharacterSpaceConverter(separator="|")
        result = await converter.convert_async(prompt="abc", input_type="text")

        assert result.output_text == "a|b|c"

    @pytest.mark.asyncio
    async def test_empty_string(self):
        """Test empty string returns empty."""
        converter = CharacterSpaceConverter()
        result = await converter.convert_async(prompt="", input_type="text")

        assert result.output_text == ""

    @pytest.mark.asyncio
    async def test_single_character(self):
        """Test single character returns unchanged."""
        converter = CharacterSpaceConverter()
        result = await converter.convert_async(prompt="a", input_type="text")

        assert result.output_text == "a"

    @pytest.mark.asyncio
    async def test_with_numbers(self):
        """Test spacing works with numbers."""
        converter = CharacterSpaceConverter()
        result = await converter.convert_async(prompt="123", input_type="text")

        assert result.output_text == "1 2 3"

    @pytest.mark.asyncio
    async def test_with_special_chars(self):
        """Test spacing works with special characters."""
        converter = CharacterSpaceConverter()
        result = await converter.convert_async(prompt="a@b", input_type="text")

        assert result.output_text == "a @ b"

    @pytest.mark.asyncio
    async def test_multi_char_separator(self):
        """Test multi-character separator."""
        converter = CharacterSpaceConverter(separator=":::")
        result = await converter.convert_async(prompt="ab", input_type="text")

        assert result.output_text == "a:::b"

    @pytest.mark.asyncio
    async def test_input_supported(self):
        """Test input_supported returns True for text."""
        converter = CharacterSpaceConverter()
        assert converter.input_supported("text") is True

    @pytest.mark.asyncio
    async def test_output_supported(self):
        """Test output_supported returns True for text."""
        converter = CharacterSpaceConverter()
        assert converter.output_supported("text") is True

    @pytest.mark.asyncio
    async def test_separator_persistence(self):
        """Test that separator is maintained across calls."""
        converter = CharacterSpaceConverter(separator="|")
        result1 = await converter.convert_async(prompt="ab", input_type="text")
        result2 = await converter.convert_async(prompt="cd", input_type="text")

        assert result1.output_text == "a|b"
        assert result2.output_text == "c|d"


class TestHomoglyphConverter:
    """Test HomoglyphConverter for homoglyph substitution."""

    @pytest.mark.asyncio
    async def test_full_replacement_probability_1(self):
        """Test with 100% replacement probability."""
        converter = HomoglyphConverter(replace_probability=1.0)
        result = await converter.convert_async(prompt="ace", input_type="text")

        # All replaceable chars should be replaced
        assert isinstance(result, ConverterResult)
        assert result.output_type == "text"
        assert result.output_text != "ace"  # Should be different

    @pytest.mark.asyncio
    async def test_no_replacement_probability_0(self):
        """Test with 0% replacement probability."""
        converter = HomoglyphConverter(replace_probability=0.0)
        result = await converter.convert_async(prompt="ace", input_type="text")

        # No replaceable chars should be replaced
        assert result.output_text == "ace"

    @pytest.mark.asyncio
    async def test_default_probability(self):
        """Test default probability is 0.5."""
        converter = HomoglyphConverter()
        # Run multiple times to verify probabilistic behavior
        results = []
        for _ in range(10):
            result = await converter.convert_async(prompt="aaaa", input_type="text")
            results.append(result.output_text)

        # At least some should be different from original
        assert any(r != "aaaa" for r in results)

    @pytest.mark.asyncio
    async def test_probability_bounds_clamped(self):
        """Test that probability is clamped to 0.0-1.0."""
        # Test with > 1.0
        converter_high = HomoglyphConverter(replace_probability=2.0)
        assert converter_high.replace_probability == 1.0

        # Test with < 0.0
        converter_low = HomoglyphConverter(replace_probability=-0.5)
        assert converter_low.replace_probability == 0.0

    @pytest.mark.asyncio
    async def test_empty_string(self):
        """Test empty string returns empty."""
        converter = HomoglyphConverter(replace_probability=1.0)
        result = await converter.convert_async(prompt="", input_type="text")

        assert result.output_text == ""

    @pytest.mark.asyncio
    async def test_unmapped_chars_preserved(self):
        """Test unmapped characters pass through unchanged."""
        converter = HomoglyphConverter(replace_probability=1.0)
        result = await converter.convert_async(prompt="bdf", input_type="text")

        # b, d, f are not in the map, should stay
        assert result.output_text == "bdf"

    @pytest.mark.asyncio
    async def test_uppercase_mapping(self):
        """Test uppercase characters are mapped."""
        converter = HomoglyphConverter(replace_probability=1.0)
        result = await converter.convert_async(prompt="ABC", input_type="text")

        # A, B, C should be in HOMOGLYPH_MAP
        assert result.output_text != "ABC"

    @pytest.mark.asyncio
    async def test_mixed_case_mapping(self):
        """Test mixed case text."""
        converter = HomoglyphConverter(replace_probability=1.0)
        result = await converter.convert_async(prompt="AaBbCc", input_type="text")

        assert isinstance(result.output_text, str)
        assert len(result.output_text) == 6

    @pytest.mark.asyncio
    async def test_homoglyph_map_exists(self):
        """Test that HOMOGLYPH_MAP is defined."""
        converter = HomoglyphConverter()
        assert hasattr(converter, "HOMOGLYPH_MAP")
        assert len(converter.HOMOGLYPH_MAP) > 0

    @pytest.mark.asyncio
    async def test_input_supported(self):
        """Test input_supported returns True for text."""
        converter = HomoglyphConverter()
        assert converter.input_supported("text") is True

    @pytest.mark.asyncio
    async def test_output_supported(self):
        """Test output_supported returns True for text."""
        converter = HomoglyphConverter()
        assert converter.output_supported("text") is True


class TestUnicodeSubstitutionConverter:
    """Test UnicodeSubstitutionConverter for Unicode substitution."""

    @pytest.mark.asyncio
    async def test_basic_conversion_uppercase(self):
        """Test conversion of uppercase letters."""
        converter = UnicodeSubstitutionConverter()
        result = await converter.convert_async(prompt="ABC", input_type="text")

        assert isinstance(result, ConverterResult)
        assert result.output_type == "text"
        assert result.output_text != "ABC"  # Should be transformed

    @pytest.mark.asyncio
    async def test_basic_conversion_lowercase(self):
        """Test conversion of lowercase letters."""
        converter = UnicodeSubstitutionConverter()
        result = await converter.convert_async(prompt="abc", input_type="text")

        assert result.output_text != "abc"  # Should be transformed

    @pytest.mark.asyncio
    async def test_full_alphabet_uppercase(self):
        """Test conversion of full uppercase alphabet."""
        converter = UnicodeSubstitutionConverter()
        input_text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        result = await converter.convert_async(prompt=input_text, input_type="text")

        assert len(result.output_text) == 26
        assert result.output_text != input_text

    @pytest.mark.asyncio
    async def test_full_alphabet_lowercase(self):
        """Test conversion of full lowercase alphabet."""
        converter = UnicodeSubstitutionConverter()
        input_text = "abcdefghijklmnopqrstuvwxyz"
        result = await converter.convert_async(prompt=input_text, input_type="text")

        assert len(result.output_text) == 26
        assert result.output_text != input_text

    @pytest.mark.asyncio
    async def test_preserves_non_alpha_chars(self):
        """Test that non-alphabetic characters are preserved."""
        converter = UnicodeSubstitutionConverter()
        result = await converter.convert_async(prompt="a1b2c3", input_type="text")

        # Numbers should be preserved
        assert "1" in result.output_text
        assert "2" in result.output_text
        assert "3" in result.output_text

    @pytest.mark.asyncio
    async def test_preserves_special_chars(self):
        """Test that special characters are preserved."""
        converter = UnicodeSubstitutionConverter()
        result = await converter.convert_async(prompt="a@b#c$", input_type="text")

        assert "@" in result.output_text
        assert "#" in result.output_text
        assert "$" in result.output_text

    @pytest.mark.asyncio
    async def test_empty_string(self):
        """Test empty string returns empty."""
        converter = UnicodeSubstitutionConverter()
        result = await converter.convert_async(prompt="", input_type="text")

        assert result.output_text == ""

    @pytest.mark.asyncio
    async def test_mixed_content(self):
        """Test mixed alphanumeric and special content."""
        converter = UnicodeSubstitutionConverter()
        result = await converter.convert_async(prompt="Hello 123!", input_type="text")

        # Should have transformed letters
        assert result.output_text != "Hello 123!"
        # But preserve numbers and special chars
        assert "123" in result.output_text
        assert "!" in result.output_text

    @pytest.mark.asyncio
    async def test_unicode_map_completeness(self):
        """Test that UNICODE_MAP contains full alphabet."""
        converter = UnicodeSubstitutionConverter()
        unicode_map = converter.UNICODE_MAP

        # Check uppercase A-Z
        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert char in unicode_map

        # Check lowercase a-z
        for char in "abcdefghijklmnopqrstuvwxyz":
            assert char in unicode_map

    @pytest.mark.asyncio
    async def test_input_supported(self):
        """Test input_supported returns True for text."""
        converter = UnicodeSubstitutionConverter()
        assert converter.input_supported("text") is True

    @pytest.mark.asyncio
    async def test_output_supported(self):
        """Test output_supported returns True for text."""
        converter = UnicodeSubstitutionConverter()
        assert converter.output_supported("text") is True

    @pytest.mark.asyncio
    async def test_unicode_chars_are_different(self):
        """Test that substituted Unicode chars are visually similar but byte-different."""
        converter = UnicodeSubstitutionConverter()
        result = await converter.convert_async(prompt="a", input_type="text")

        # Should be a single Unicode character (not ASCII)
        assert len(result.output_text) == 1
        # Should be different from ASCII 'a'
        assert result.output_text != "a"
        # Should be a valid Unicode string
        assert isinstance(result.output_text, str)

    @pytest.mark.asyncio
    async def test_long_string(self):
        """Test conversion of longer string."""
        converter = UnicodeSubstitutionConverter()
        input_text = "The quick brown fox jumps over the lazy dog"
        result = await converter.convert_async(prompt=input_text, input_type="text")

        # Length should be same
        assert len(result.output_text) == len(input_text)
        # But content different due to alphabet substitution
        assert result.output_text != input_text
