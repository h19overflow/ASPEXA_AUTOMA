"""Homoglyph Converter.

Purpose: Replace ASCII with visually similar Unicode characters
Role: Payload obfuscation for AI security testing
Dependencies: pyrit.prompt_converter

Encoding Pattern:
- Uses Cyrillic homoglyphs that look identical to ASCII
- Probabilistic replacement (default 50%)
- Maintains visual appearance while changing byte representation
"""
import random
from pyrit.prompt_converter import PromptConverter, ConverterResult


class HomoglyphConverter(PromptConverter):
    """Replaces ASCII characters with visually similar Unicode homoglyphs.

    Uses Cyrillic and other Unicode characters that appear identical
    to ASCII letters but have different byte representations.
    """

    # Cyrillic and other Unicode homoglyphs
    HOMOGLYPH_MAP = {
        'a': '\u0430',  # Cyrillic small letter a
        'c': '\u0441',  # Cyrillic small letter es
        'e': '\u0435',  # Cyrillic small letter ie
        'o': '\u043e',  # Cyrillic small letter o
        'p': '\u0440',  # Cyrillic small letter er
        'x': '\u0445',  # Cyrillic small letter ha
        'y': '\u0443',  # Cyrillic small letter u
        'A': '\u0410',  # Cyrillic capital letter A
        'B': '\u0412',  # Cyrillic capital letter Ve
        'C': '\u0421',  # Cyrillic capital letter Es
        'E': '\u0415',  # Cyrillic capital letter Ie
        'H': '\u041d',  # Cyrillic capital letter En
        'K': '\u041a',  # Cyrillic capital letter Ka
        'M': '\u041c',  # Cyrillic capital letter Em
        'O': '\u041e',  # Cyrillic capital letter O
        'P': '\u0420',  # Cyrillic capital letter Er
        'T': '\u0422',  # Cyrillic capital letter Te
        'X': '\u0425',  # Cyrillic capital letter Ha
        'Y': '\u0423',  # Cyrillic capital letter U
    }

    def __init__(self, replace_probability: float = 0.5) -> None:
        """Initialize converter with replacement probability.

        Args:
            replace_probability: Probability of replacing each eligible character (0.0-1.0)
        """
        self.replace_probability = max(0.0, min(1.0, replace_probability))

    async def convert_async(
        self, *, prompt: str, input_type: str = "text"
    ) -> ConverterResult:
        """Convert text using homoglyph substitution.

        Args:
            prompt: Input text to convert
            input_type: Type of input (must be "text")

        Returns:
            ConverterResult with homoglyph-substituted text
        """
        if not prompt:
            return ConverterResult(output_text="", output_type="text")

        result = []
        for char in prompt:
            if char in self.HOMOGLYPH_MAP and random.random() < self.replace_probability:
                result.append(self.HOMOGLYPH_MAP[char])
            else:
                result.append(char)

        converted = ''.join(result)

        return ConverterResult(output_text=converted, output_type="text")

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"
