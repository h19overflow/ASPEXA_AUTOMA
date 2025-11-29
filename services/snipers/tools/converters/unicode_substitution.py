"""Unicode Substitution Converter.

Purpose: Replace ASCII letters with mathematical Unicode variants
Role: Payload obfuscation for AI security testing
Dependencies: pyrit.prompt_converter

Encoding Pattern:
- Uses mathematical sans-serif Unicode characters
- Full alphabet mapping (A-Z, a-z)
- Maintains letter structure while changing representation
"""
from pyrit.prompt_converter import PromptConverter, ConverterResult


class UnicodeSubstitutionConverter(PromptConverter):
    """Replaces ASCII letters with mathematical Unicode sans-serif variants.

    Uses Unicode mathematical alphanumeric symbols to encode text
    while maintaining visual similarity.
    """

    # Mathematical Sans-Serif Unicode mapping
    UNICODE_MAP = {
        # Uppercase A-Z (U+1D5A0 to U+1D5B9)
        'A': '\U0001d5a0', 'B': '\U0001d5a1', 'C': '\U0001d5a2', 'D': '\U0001d5a3',
        'E': '\U0001d5a4', 'F': '\U0001d5a5', 'G': '\U0001d5a6', 'H': '\U0001d5a7',
        'I': '\U0001d5a8', 'J': '\U0001d5a9', 'K': '\U0001d5aa', 'L': '\U0001d5ab',
        'M': '\U0001d5ac', 'N': '\U0001d5ad', 'O': '\U0001d5ae', 'P': '\U0001d5af',
        'Q': '\U0001d5b0', 'R': '\U0001d5b1', 'S': '\U0001d5b2', 'T': '\U0001d5b3',
        'U': '\U0001d5b4', 'V': '\U0001d5b5', 'W': '\U0001d5b6', 'X': '\U0001d5b7',
        'Y': '\U0001d5b8', 'Z': '\U0001d5b9',
        # Lowercase a-z (U+1D5BA to U+1D5D3)
        'a': '\U0001d5ba', 'b': '\U0001d5bb', 'c': '\U0001d5bc', 'd': '\U0001d5bd',
        'e': '\U0001d5be', 'f': '\U0001d5bf', 'g': '\U0001d5c0', 'h': '\U0001d5c1',
        'i': '\U0001d5c2', 'j': '\U0001d5c3', 'k': '\U0001d5c4', 'l': '\U0001d5c5',
        'm': '\U0001d5c6', 'n': '\U0001d5c7', 'o': '\U0001d5c8', 'p': '\U0001d5c9',
        'q': '\U0001d5ca', 'r': '\U0001d5cb', 's': '\U0001d5cc', 't': '\U0001d5cd',
        'u': '\U0001d5ce', 'v': '\U0001d5cf', 'w': '\U0001d5d0', 'x': '\U0001d5d1',
        'y': '\U0001d5d2', 'z': '\U0001d5d3',
    }

    async def convert_async(
        self, *, prompt: str, input_type: str = "text"
    ) -> ConverterResult:
        """Convert text using Unicode mathematical sans-serif substitution.

        Args:
            prompt: Input text to convert
            input_type: Type of input (must be "text")

        Returns:
            ConverterResult with Unicode-substituted text
        """
        if not prompt:
            return ConverterResult(output_text="", output_type="text")

        converted = ''.join(self.UNICODE_MAP.get(char, char) for char in prompt)

        return ConverterResult(output_text=converted, output_type="text")

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"
