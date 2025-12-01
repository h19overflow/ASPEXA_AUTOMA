"""LeetSpeak Converter.

Purpose: Convert text to leetspeak (1337) encoding
Role: Payload obfuscation for AI security testing
Dependencies: pyrit.prompt_converter

Encoding Pattern:
- Replaces letters with similar-looking numbers/symbols
- Preserves non-mapped characters
- Case-insensitive mapping
"""
from pyrit.prompt_converter import PromptConverter, ConverterResult


class LeetspeakConverter(PromptConverter):
    """Converts text to leetspeak (1337speak) encoding.

    Uses character substitution to replace letters with visually similar
    numbers and symbols while maintaining readability.
    """

    # LeetSpeak character mapping
    LEET_MAP = {
        'a': '4', 'A': '4',
        'b': '8', 'B': '8',
        'e': '3', 'E': '3',
        'g': '9', 'G': '9',
        'i': '1', 'I': '1',
        'l': '1', 'L': '1',
        'o': '0', 'O': '0',
        's': '5', 'S': '5',
        't': '7', 'T': '7',
    }

    async def convert_async(
        self, *, prompt: str, input_type: str = "text"
    ) -> ConverterResult:
        """Convert text to leetspeak encoding.

        Args:
            prompt: Input text to convert
            input_type: Type of input (must be "text")

        Returns:
            ConverterResult with leetspeak-encoded text
        """
        if not prompt:
            return ConverterResult(output_text="", output_type="text")

        converted = ''.join(self.LEET_MAP.get(char, char) for char in prompt)

        return ConverterResult(output_text=converted, output_type="text")

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"
