"""HTML Entity Converter.

Purpose: Convert special characters to HTML entities with diverse encoding
Role: Payload encoding for HTML context attacks with evasion capabilities
Dependencies: pyrit.prompt_converter

Encoding Strategies:
- Mixed Entity Types: Rotates through named, decimal, hex entities
- Positional Selective: Encodes only prime-positioned characters
- Vowel + Special: Encodes vowels and HTML special characters
- Padded Decimals: Uses decimal entities with variable zero-padding
"""

from pyrit.prompt_converter import PromptConverter, ConverterResult


class HtmlEntityConverter(PromptConverter):
    """Converts special characters to HTML entities with diverse encoding strategies.

    Uses rule-based strategies to generate diverse, universally-decodable
    encodings that evade simple pattern matching while maintaining
    full compatibility with standard HTML parsers.
    """

    # HTML special characters that should always be encoded
    HTML_SPECIAL_CHARS = {'<', '>', '&', '"', "'"}
    
    # Vowels for vowel-based encoding strategy
    VOWELS = {'a', 'e', 'i', 'o', 'u', 'A', 'E', 'I', 'O', 'U'}
    
    # Prime numbers for positional encoding (up to 100)
    PRIMES = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97}

    async def convert_async(
        self, *, prompt: str, input_type: str = "text"
    ) -> ConverterResult:
        """Convert text to HTML entities using rule-based diverse encoding.

        Args:
            prompt: Input text to convert
            input_type: Type of input (must be "text")

        Returns:
            ConverterResult with HTML-encoded text using selected strategy
        """
        if not prompt:
            return ConverterResult(output_text="", output_type="text")
        
        # Select strategy based on prompt hash (deterministic)
        strategy_id = hash(prompt) % 4
        
        if strategy_id == 0:
            converted = self._mixed_entity_types(prompt)
        elif strategy_id == 1:
            converted = self._positional_selective(prompt)
        elif strategy_id == 2:
            converted = self._vowel_and_special(prompt)
        else:  # strategy_id == 3
            converted = self._padded_decimals(prompt)
        
        return ConverterResult(output_text=converted, output_type="text")

    def _mixed_entity_types(self, text: str) -> str:
        """Strategy A: Mix named, decimal, hex-lower, hex-upper entities.
        
        Rotates entity type based on character position and value.
        All forms are universally decodable by HTML parsers.
        """
        result = []
        for pos, char in enumerate(text):
            if char in self.HTML_SPECIAL_CHARS or ord(char) > 127:
                # Determine entity type based on position and char
                entity_type = hash(char + str(pos)) % 4
                
                if entity_type == 0 and char in {'<', '>', '&', '"', "'"}:
                    # Named entity (when available)
                    named_map = {'<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;'}
                    result.append(named_map.get(char, f'&#x{ord(char):x};'))
                elif entity_type == 1:
                    # Decimal entity
                    result.append(f'&#x{ord(char):x};')
                elif entity_type == 2:
                    # Hex lowercase
                    result.append(f'&#x{ord(char):x};')
                else:
                    # Hex uppercase
                    result.append(f'&#x{ord(char):X};')
            else:
                result.append(char)
        return ''.join(result)

    def _positional_selective(self, text: str) -> str:
        """Strategy B: Encode only characters at prime positions.
        
        Encodes selectively to reduce signature while maintaining evasion.
        Always encodes HTML special characters regardless of position.
        """
        result = []
        for pos, char in enumerate(text):
            if char in self.HTML_SPECIAL_CHARS or pos in self.PRIMES:
                # Use hex entity with mixed case
                if hash(char) % 2 == 0:
                    result.append(f'&#x{ord(char):x};')
                else:
                    result.append(f'&#x{ord(char):X};')
            else:
                result.append(char)
        return ''.join(result)

    def _vowel_and_special(self, text: str) -> str:
        """Strategy C: Encode vowels and HTML special characters.
        
        Targets common characters while preserving structure.
        Uses decimal entities for vowels, hex for special chars.
        """
        result = []
        for char in text:
            if char in self.HTML_SPECIAL_CHARS:
                # Special chars use hex
                result.append(f'&#x{ord(char):x};')
            elif char in self.VOWELS:
                # Vowels use decimal
                result.append(f'&#x{ord(char):x};')
            else:
                result.append(char)
        return ''.join(result)

    def _padded_decimals(self, text: str) -> str:
        """Strategy D: Use decimal entities with variable zero-padding.
        
        Adds confusion through padding variation while maintaining
        universal decodability (parsers ignore leading zeros).
        """
        result = []
        for pos, char in enumerate(text):
            if char in self.HTML_SPECIAL_CHARS or ord(char) > 127:
                # Variable padding based on position
                padding = pos % 5
                decimal_code = ord(char)
                result.append(f'&#{decimal_code:0{padding + 1}d};')
            else:
                result.append(char)
        return ''.join(result)

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"
