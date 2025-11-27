"""XML Escape Converter.

Purpose: Escape text for safe inclusion in XML content with diverse encoding
Role: Payload encoding for XML context attacks with evasion capabilities
Dependencies: pyrit.prompt_converter

Encoding Strategies:
- Mixed XML Entities: Rotates through named, decimal, hex entities
- CDATA Wrapping: Strategically wraps segments in CDATA sections
- Attribute-Focused: Heavily encodes quotes and equals for attribute contexts
- Positional Hex: Uses hex entities with mixed case variation
"""
import xml.sax.saxutils as xml_utils
from typing import Set

from pyrit.prompt_converter import PromptConverter, ConverterResult


class XmlEscapeConverter(PromptConverter):
    """Escapes text for XML content with diverse encoding strategies.

    Uses rule-based strategies to generate diverse, universally-decodable
    XML encodings that evade simple pattern matching while maintaining
    full XML parser compatibility.
    """

    # XML special characters
    XML_SPECIAL_CHARS = {'<', '>', '&', '"', "'"}
    
    # Named entity mappings
    ENTITY_MAP = {
        '<': '&lt;',
        '>': '&gt;',
        '&': '&amp;',
        '"': '&quot;',
        "'": '&apos;',
    }
    
    # Characters commonly found in attributes
    ATTRIBUTE_CHARS = {'"', "'", '='}

    async def convert_async(
        self, *, prompt: str, input_type: str = "text"
    ) -> ConverterResult:
        """Convert text to XML-escaped format using rule-based diverse encoding.

        Args:
            prompt: Input text to convert
            input_type: Type of input (must be "text")

        Returns:
            ConverterResult with XML-encoded text using selected strategy
        """
        if not prompt:
            return ConverterResult(output_text="", output_type="text")
        
        # Select strategy based on prompt hash (deterministic)
        strategy_id = hash(prompt) % 4
        
        if strategy_id == 0:
            converted = self._mixed_xml_entities(prompt)
        elif strategy_id == 1:
            converted = self._cdata_wrapping(prompt)
        elif strategy_id == 2:
            converted = self._attribute_focused(prompt)
        else:  # strategy_id == 3
            converted = self._positional_hex(prompt)
        
        return ConverterResult(output_text=converted, output_type="text")

    def _mixed_xml_entities(self, text: str) -> str:
        """Strategy A: Mix named, decimal, hex, and padded decimal entities.
        
        Rotates through different entity representations based on
        position and character. All forms are universally decodable.
        """
        result = []
        for pos, char in enumerate(text):
            if char in self.XML_SPECIAL_CHARS or ord(char) > 127:
                entity_type = hash(char + str(pos)) % 4
                
                if entity_type == 0 and char in self.ENTITY_MAP:
                    # Named entity
                    result.append(self.ENTITY_MAP[char])
                elif entity_type == 1:
                    # Decimal entity
                    result.append(f'&#x{ord(char)};')
                elif entity_type == 2:
                    # Hex entity lowercase
                    result.append(f'&#x{ord(char):x};')
                else:
                    # Padded decimal
                    padding = pos % 4
                    result.append(f'&#{ord(char):0{padding + 1}d};')
            else:
                result.append(char)
        return ''.join(result)

    def _cdata_wrapping(self, text: str) -> str:
        """Strategy B: Wrap content in CDATA sections strategically.
        
        CDATA sections prevent XML parsing of enclosed content,
        allowing special characters to pass through literally.
        Useful for preserving payload structure.
        """
        # If text is short or contains CDATA markers, use entity encoding
        if len(text) < 5 or ']]>' in text:
            return xml_utils.escape(text)
        
        # Check if text contains XML special chars that benefit from CDATA
        has_specials = any(c in text for c in self.XML_SPECIAL_CHARS)
        
        if has_specials:
            # Wrap in CDATA
            # Note: CDATA cannot contain ]]>, must be escaped
            safe_text = text.replace(']]>', ']]&gt;')
            return f'<![CDATA[{safe_text}]]>'
        else:
            # No special chars, return as-is
            return text

    def _attribute_focused(self, text: str) -> str:
        """Strategy C: Heavily encode quotes and equals for attribute contexts.
        
        Focuses on characters critical in XML attributes while
        leaving element content minimally encoded.
        """
        result = []
        for char in text:
            if char in self.ATTRIBUTE_CHARS:
                # Always hex-encode attribute-critical chars
                result.append(f'&#x{ord(char):x};')
            elif char in self.XML_SPECIAL_CHARS:
                # Use named entities for other specials
                result.append(self.ENTITY_MAP.get(char, char))
            else:
                result.append(char)
        return ''.join(result)

    def _positional_hex(self, text: str) -> str:
        """Strategy D: Use hex entities with mixed case variation.
        
        Hex entities support both uppercase and lowercase.
        Mixing case adds diversity without affecting decodability.
        """
        result = []
        for pos, char in enumerate(text):
            if char in self.XML_SPECIAL_CHARS or ord(char) > 127:
                # Mix uppercase/lowercase based on position
                if pos % 2 == 0:
                    # Lowercase hex
                    result.append(f'&#x{ord(char):x};')
                else:
                    # Uppercase hex
                    result.append(f'&#x{ord(char):X};')
            else:
                result.append(char)
        return ''.join(result)

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"
