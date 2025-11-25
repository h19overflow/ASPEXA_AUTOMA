"""
PyRIT Bridge Module

Provides converter factory and payload transformation using PyRIT converters.
Maps agent's converter selection (strings) to PyRIT converter instances.
Applies converters sequentially with fault tolerance.
"""
import html
import json
import logging
import xml.sax.saxutils as xml_utils
from typing import Dict, List, Optional, Tuple

from pyrit.prompt_converter import (
    Base64Converter,
    ROT13Converter,
    CaesarConverter,
    UrlConverter,
    TextToHexConverter,
    UnicodeConfusableConverter,
    PromptConverter,
    ConverterResult,
)

logger = logging.getLogger(__name__)


class ConverterFactoryError(Exception):
    """Raised when converter factory encounters an error."""
    pass


class HtmlEntityConverter(PromptConverter):
    """Converts special characters to HTML entities."""

    async def convert_async(self, *, prompt: str, input_type: str = "text") -> ConverterResult:
        """Convert text to HTML entities."""
        converted = html.escape(prompt)
        return ConverterResult(output_text=converted, output_type="text")

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"


class JsonEscapeConverter(PromptConverter):
    """Escapes text for safe inclusion in JSON strings."""

    async def convert_async(self, *, prompt: str, input_type: str = "text") -> ConverterResult:
        """Convert text to JSON-escaped format."""
        converted = json.dumps(prompt)[1:-1]  # Remove surrounding quotes
        return ConverterResult(output_text=converted, output_type="text")

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"


class XmlEscapeConverter(PromptConverter):
    """Escapes text for safe inclusion in XML content."""

    async def convert_async(self, *, prompt: str, input_type: str = "text") -> ConverterResult:
        """Convert text to XML-escaped format."""
        converted = xml_utils.escape(prompt)
        return ConverterResult(output_text=converted, output_type="text")

    def input_supported(self, input_type: str) -> bool:
        """Check if input type is supported."""
        return input_type == "text"

    def output_supported(self, output_type: str) -> bool:
        """Check if output type is supported."""
        return output_type == "text"


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
        """Create all supported converter instances."""
        # PyRIT native converters
        self._converters = {
            "Base64Converter": Base64Converter(),
            "ROT13Converter": ROT13Converter(),
            "CaesarConverter": CaesarConverter(caesar_offset=3),  # Default offset
            "UrlConverter": UrlConverter(),
            "TextToHexConverter": TextToHexConverter(),
            "UnicodeConverter": UnicodeConfusableConverter(),
            # Custom converters
            "HtmlEntityConverter": HtmlEntityConverter(),
            "JsonEscapeConverter": JsonEscapeConverter(),
            "XmlEscapeConverter": XmlEscapeConverter(),
        }
        logger.info(f"Initialized {len(self._converters)} PyRIT converters")

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
