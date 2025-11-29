"""Character Space Converter.

Purpose: Insert separators between characters
Role: Payload obfuscation for AI security testing
Dependencies: pyrit.prompt_converter

Encoding Pattern:
- Inserts separator between each character
- Default separator is single space
- Configurable separator via constructor
"""
from pyrit.prompt_converter import PromptConverter, ConverterResult


class CharacterSpaceConverter(PromptConverter):
    """Inserts separator between each character in text.

    Breaks up character sequences to evade pattern matching while
    maintaining readability with configurable separation.
    """

    def __init__(self, separator: str = " ") -> None:
        """Initialize converter with custom separator.

        Args:
            separator: String to insert between characters (default: " ")
        """
        self.separator = separator

    async def convert_async(
        self, *, prompt: str, input_type: str = "text"
    ) -> ConverterResult:
        """Convert text by inserting separators between characters.

        Args:
            prompt: Input text to convert
            input_type: Type of input (must be "text")

        Returns:
            ConverterResult with character-spaced text
        """
        if not prompt:
            return ConverterResult(output_text="", output_type="text")

        converted = self.separator.join(char for char in prompt)

        return ConverterResult(output_text=converted, output_type="text")

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"
