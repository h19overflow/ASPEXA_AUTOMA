"""Morse Code Converter.

Purpose: Convert text to morse code dots and dashes
Role: Payload encoding for AI security testing
Dependencies: pyrit.prompt_converter

Encoding Pattern:
- Full alphabet + digits + space + common punctuation
- Space between letters, ' / ' between words
- Unknown characters passed through as-is
"""
from pyrit.prompt_converter import PromptConverter, ConverterResult


class MorseCodeConverter(PromptConverter):
    """Converts text to morse code (dots and dashes).

    Uses international morse code standard with space separation
    between letters and ' / ' between words.
    """

    # International Morse Code mapping
    MORSE_MAP = {
        'A': '.-',    'B': '-...',  'C': '-.-.',  'D': '-..',   'E': '.',
        'F': '..-.',  'G': '--.',   'H': '....',  'I': '..',    'J': '.---',
        'K': '-.-',   'L': '.-..',  'M': '--',    'N': '-.',    'O': '---',
        'P': '.--.',  'Q': '--.-',  'R': '.-.',   'S': '...',   'T': '-',
        'U': '..-',   'V': '...-',  'W': '.--',   'X': '-..-',  'Y': '-.--',
        'Z': '--..',
        '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
        '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
        '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.',
        '!': '-.-.--', '/': '-..-.', '(': '-.--.', ')': '-.--.-',
        '&': '.-...', ':': '---...', ';': '-.-.-.', '=': '-...-',
        '+': '.-.-.', '-': '-....-', '_': '..--.-', '"': '.-..-.',
        '$': '...-..-', '@': '.--.-.', ' ': '/',
    }

    async def convert_async(
        self, *, prompt: str, input_type: str = "text"
    ) -> ConverterResult:
        """Convert text to morse code.

        Args:
            prompt: Input text to convert
            input_type: Type of input (must be "text")

        Returns:
            ConverterResult with morse code encoded text
        """
        if not prompt:
            return ConverterResult(output_text="", output_type="text")

        morse_chars = []
        for char in prompt.upper():
            if char in self.MORSE_MAP:
                morse_chars.append(self.MORSE_MAP[char])
            else:
                # Unknown characters passed through
                morse_chars.append(char)

        # Join with space, replace consecutive '/ ' with single ' / '
        converted = ' '.join(morse_chars).replace(' / ', ' / ')

        return ConverterResult(output_text=converted, output_type="text")

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"
