"""
PyRIT Bridge Module

Provides converter factory and payload transformation using PyRIT converters.
Maps agent's converter selection (strings) to PyRIT converter instances.
Applies converters sequentially with fault tolerance.
"""
import logging
from typing import Dict, List, Optional, Tuple

from pyrit.prompt_converter import (
    Base64Converter,
    ROT13Converter,
    CaesarConverter,
    UrlConverter,
    TextToHexConverter,
    UnicodeConfusableConverter,
    PromptConverter,
)

from services.snipers.core.converters import (
    JsonEscapeConverter,
    XmlEscapeConverter,
    MorseCodeConverter,
    CharacterSpaceConverter,
    HomoglyphConverter,
    UnicodeSubstitutionConverter,
    get_suffix_converters,
)

logger = logging.getLogger(__name__)


class ConverterFactoryError(Exception):
    """Raised when converter factory encounters an error."""
    pass


class ConverterFactory:
    """
    Creates and caches PyRIT converters.

    Initializes all converters once in constructor for reuse.
    Maps agent's string names to PyRIT converter instances.
    """

    def __init__(self):
        """Build expensive converter instances once."""
        self._converters: Dict[str, PromptConverter] = {}
        self._initialize_converters()

    def _initialize_converters(self) -> None:
        """Create all supported converter instances with dual naming."""
        # Create instances once
        base64 = Base64Converter()
        rot13 = ROT13Converter()
        caesar = CaesarConverter(caesar_offset=3)
        url = UrlConverter()
        hex_conv = TextToHexConverter()
        unicode_conf = UnicodeConfusableConverter()
        json_esc = JsonEscapeConverter()
        xml_esc = XmlEscapeConverter()
        morse = MorseCodeConverter()
        char_space = CharacterSpaceConverter()
        homoglyph = HomoglyphConverter()
        unicode_sub = UnicodeSubstitutionConverter()

        # Map both short names (API) and class names (backward compat)
        self._converters = {
            # Short names (used by API)
            "base64": base64,
            "rot13": rot13,
            "caesar_cipher": caesar,
            "url": url,
            "hex": hex_conv,
            "unicode_confusable": unicode_conf,
            "json_escape": json_esc,
            "xml_escape": xml_esc,
            "morse_code": morse,
            "character_space": char_space,
            "homoglyph": homoglyph,
            "unicode_substitution": unicode_sub,
            # Class names (backward compatibility)
            "Base64Converter": base64,
            "ROT13Converter": rot13,
            "CaesarConverter": caesar,
            "UrlConverter": url,
            "TextToHexConverter": hex_conv,
            "UnicodeConverter": unicode_conf,
            "JsonEscapeConverter": json_esc,
            "XmlEscapeConverter": xml_esc,
            "MorseCodeConverter": morse,
            "CharacterSpaceConverter": char_space,
            "HomoglyphConverter": homoglyph,
            "UnicodeSubstitutionConverter": unicode_sub,
        }

        # Add suffix converters (GCG, AutoDAN, defense-specific)
        suffix_converters = get_suffix_converters()
        self._converters.update(suffix_converters)

        logger.info(f"Initialized {len(self._converters)} PyRIT converter mappings")

    def get_converter(self, name: str) -> Optional[PromptConverter]:
        """
        Get cached converter by name.

        Args:
            name: Converter name (e.g., "Base64Converter")

        Returns:
            Converter instance or None if unavailable
        """
        return self._converters.get(name)

    def get_available_names(self) -> List[str]:
        """
        Get list of available converter names.

        Returns:
            List of converter name strings
        """
        return list(self._converters.keys())


class PayloadTransformer:
    """
    Applies PyRIT converters sequentially with fault tolerance.

    Skips failed converters and continues with remaining ones.
    """

    def __init__(self, converter_factory: ConverterFactory):
        """
        Initialize with converter factory.

        Args:
            converter_factory: Factory for creating converters
        """
        self._factory = converter_factory

    async def transform_async(
        self, payload: str, converter_names: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Apply converters sequentially to payload (async version).

        Args:
            payload: Original attack payload
            converter_names: List of converter names to apply

        Returns:
            Tuple of (transformed_payload, list_of_errors)

        Skips converters that fail or don't exist, logs errors.
        """
        # Validate inputs immediately (fail fast)
        if not payload:
            raise ValueError("Payload cannot be empty")

        if not converter_names:
            return payload, []  # No converters = identity transform

        result = payload
        errors = []

        for name in converter_names:
            converter = self._factory.get_converter(name)

            if converter is None:
                error_msg = f"Converter '{name}' not available"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue  # Skip unavailable converter

            try:
                converter_result = await converter.convert_async(
                    prompt=result, input_type="text"
                )
                result = converter_result.output_text
                logger.debug(f"Applied converter '{name}' successfully")
            except Exception as e:
                error_msg = f"Converter '{name}' failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Continue with next converter (fault tolerance)

        return result, errors

    def transform(
        self, payload: str, converter_names: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Apply converters sequentially to payload (sync wrapper).

        Args:
            payload: Original attack payload
            converter_names: List of converter names to apply

        Returns:
            Tuple of (transformed_payload, list_of_errors)

        Skips converters that fail or don't exist, logs errors.
        """
        import asyncio

        try:
            return asyncio.get_event_loop().run_until_complete(
                self.transform_async(payload, converter_names)
            )
        except RuntimeError:
            return asyncio.run(self.transform_async(payload, converter_names))
