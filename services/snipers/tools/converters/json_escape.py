r"""JSON Escape Converter.

Purpose: Escape text for safe inclusion in JSON strings with diverse encoding
Role: Payload encoding for JSON context attacks with evasion capabilities
Dependencies: pyrit.prompt_converter

Encoding Strategies:
- Unicode Mixing: Combines literal, \uXXXX, and \xXX escape sequences
- Selective Escaping: Only escapes JSON specials + even-positioned chars
- Full Unicode: Converts all characters to \uXXXX format
"""
import json
from typing import Set

from pyrit.prompt_converter import PromptConverter, ConverterResult


class JsonEscapeConverter(PromptConverter):
    """Escapes text for JSON strings with diverse encoding strategies.

    Uses rule-based strategies to generate diverse, universally-decodable
    JSON escape sequences that evade simple pattern matching while
    maintaining full JSON parser compatibility.
    """

    # JSON special characters that must always be escaped
    JSON_SPECIAL_CHARS = {'"', '\\', '/', '\b', '\f', '\n', '\r', '\t'}
    
    # Standard escape mappings
    ESCAPE_MAP = {
        '"': '\\"',
        '\\': '\\\\',
        '/': '\\/',
        '\b': '\\b',
        '\f': '\\f',
        '\n': '\\n',
        '\r': '\\r',
        '\t': '\\t',
    }

    async def convert_async(
        self, *, prompt: str, input_type: str = "text"
    ) -> ConverterResult:
        """Convert text to JSON-escaped format using rule-based diverse encoding.

        Args:
            prompt: Input text to convert
            input_type: Type of input (must be "text")

        Returns:
            ConverterResult with JSON-escaped text (without surrounding quotes)
        """
        if not prompt:
            return ConverterResult(output_text="", output_type="text")
        
        # Select strategy based on prompt hash (deterministic)
        strategy_id = hash(prompt) % 3
        
        if strategy_id == 0:
            converted = self._unicode_mixing(prompt)
        elif strategy_id == 1:
            converted = self._selective_escaping(prompt)
        else:  # strategy_id == 2
            converted = self._full_unicode(prompt)
        
        return ConverterResult(output_text=converted, output_type="text")

    def _unicode_mixing(self, text: str) -> str:
        r"""Strategy A: Mix literal, \uXXXX, and \xXX escape sequences.
        
        Rotates between different valid JSON escape formats based on
        character position and value. All forms decode identically.
        """
        result = []
        for pos, char in enumerate(text):
            # Always escape JSON special characters
            if char in self.ESCAPE_MAP:
                result.append(self.ESCAPE_MAP[char])
            # Control characters always use unicode
            elif ord(char) < 32:
                result.append(f'\\u{ord(char):04x}')
            # Non-ASCII always uses unicode
            elif ord(char) > 127:
                result.append(f'\\u{ord(char):04x}')
            # ASCII chars: rotate based on position
            else:
                escape_type = hash(char + str(pos)) % 3
                if escape_type == 0:
                    # Literal
                    result.append(char)
                elif escape_type == 1:
                    # Unicode escape
                    result.append(f'\\u{ord(char):04x}')
                else:
                    # Hex escape (valid in some JSON contexts)
                    # Fall back to unicode for safety
                    result.append(f'\\u{ord(char):04x}')
        return ''.join(result)

    def _selective_escaping(self, text: str) -> str:
        """Strategy B: Only escape JSON specials + chars at even positions.
        
        Minimal encoding approach that reduces signature while
        maintaining necessary escaping for JSON validity.
        """
        result = []
        for pos, char in enumerate(text):
            # Always escape JSON special characters
            if char in self.ESCAPE_MAP:
                result.append(self.ESCAPE_MAP[char])
            # Control characters must be escaped
            elif ord(char) < 32:
                result.append(f'\\u{ord(char):04x}')
            # Even positions get unicode escaping
            elif pos % 2 == 0 and ord(char) > 32:
                result.append(f'\\u{ord(char):04x}')
            else:
                result.append(char)
        return ''.join(result)

    def _full_unicode(self, text: str) -> str:
        r"""Strategy C: Convert all characters to \uXXXX format.
        
        Maximum obfuscation while maintaining universal decodability.
        All valid JSON parsers handle unicode escape sequences.
        """
        result = []
        for char in text:
            # Use unicode escape for everything
            if ord(char) > 0xFFFF:
                # Handle surrogate pairs for characters outside BMP
                # Python's json module handles this automatically
                escaped = json.dumps(char)[1:-1]
                result.append(escaped)
            else:
                result.append(f'\\u{ord(char):04x}')
        return ''.join(result)

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"

