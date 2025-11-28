"""Converter chain builder and executor.

Reuses PyRIT bridge from automated Snipers service.
Dependencies: services.snipers.tools.pyrit_bridge
System role: Payload transformation orchestration
"""
from typing import List, Tuple

from services.snipers.tools.pyrit_bridge import ConverterFactory, PayloadTransformer
from ..models.converter import TransformResult, TransformStep, ConverterInfo


# Converter metadata for UI
CONVERTER_CATALOG: List[ConverterInfo] = [
    ConverterInfo(
        name="Base64Converter",
        display_name="Base64",
        description="Encode payload as Base64",
        category="encoding",
        example_input="hello",
        example_output="aGVsbG8=",
    ),
    ConverterInfo(
        name="ROT13Converter",
        display_name="ROT13",
        description="Apply ROT13 cipher (rotate 13 positions)",
        category="obfuscation",
        example_input="hello",
        example_output="uryyb",
    ),
    ConverterInfo(
        name="CaesarConverter",
        display_name="Caesar",
        description="Apply Caesar cipher (configurable shift)",
        category="obfuscation",
        example_input="hello",
        example_output="khoor",
    ),
    ConverterInfo(
        name="UrlConverter",
        display_name="URL Encode",
        description="URL-encode special characters",
        category="encoding",
        example_input="<script>",
        example_output="%3Cscript%3E",
    ),
    ConverterInfo(
        name="TextToHexConverter",
        display_name="Hex",
        description="Convert text to hexadecimal",
        category="encoding",
        example_input="AB",
        example_output="4142",
    ),
    ConverterInfo(
        name="UnicodeConverter",
        display_name="Unicode",
        description="Convert to Unicode escape sequences",
        category="encoding",
        example_input="<",
        example_output=r"\u003c",
    ),
    ConverterInfo(
        name="HtmlEntityConverter",
        display_name="HTML Entity",
        description="Encode as HTML entities (4 strategies)",
        category="escape",
        example_input="<div>",
        example_output="&#60;div&#62;",
    ),
    ConverterInfo(
        name="JsonEscapeConverter",
        display_name="JSON Escape",
        description="Escape for JSON strings (3 strategies)",
        category="escape",
        example_input='"test"',
        example_output=r'\"test\"',
    ),
    ConverterInfo(
        name="XmlEscapeConverter",
        display_name="XML Escape",
        description="Escape for XML content (4 strategies)",
        category="escape",
        example_input="<tag>",
        example_output="&lt;tag&gt;",
    ),
]


class ConverterChainExecutor:
    """Executes converter chains with step-by-step tracking.

    Wraps PayloadTransformer to provide detailed transformation steps.
    """

    def __init__(self):
        """Initialize with converter factory."""
        self._factory = ConverterFactory()
        self._transformer = PayloadTransformer(self._factory)

    def get_available_converters(self) -> List[ConverterInfo]:
        """Return metadata for all available converters.

        Returns:
            List of ConverterInfo objects
        """
        return CONVERTER_CATALOG

    async def transform_with_steps(
        self, payload: str, converter_names: List[str]
    ) -> TransformResult:
        """Apply converter chain with step-by-step results.

        Args:
            payload: Original payload text
            converter_names: Ordered list of converter names

        Returns:
            TransformResult with each step's input/output
        """
        steps: List[TransformStep] = []
        current = payload
        errors: List[str] = []

        for name in converter_names:
            converter = self._factory.get_converter(name)
            if converter is None:
                error = f"Converter '{name}' not available"
                errors.append(error)
                steps.append(
                    TransformStep(
                        converter_name=name,
                        input_payload=current,
                        output_payload=current,
                        success=False,
                        error=error,
                    )
                )
                continue

            try:
                result = await converter.convert_async(prompt=current, input_type="text")
                output = result.output_text
                steps.append(
                    TransformStep(
                        converter_name=name,
                        input_payload=current,
                        output_payload=output,
                        success=True,
                    )
                )
                current = output
            except Exception as e:
                error = f"Converter '{name}' failed: {str(e)}"
                errors.append(error)
                steps.append(
                    TransformStep(
                        converter_name=name,
                        input_payload=current,
                        output_payload=current,
                        success=False,
                        error=error,
                    )
                )

        return TransformResult(
            original_payload=payload,
            final_payload=current,
            steps=steps,
            total_converters=len(converter_names),
            successful_converters=sum(1 for s in steps if s.success),
            errors=errors,
        )

    def transform_sync(
        self, payload: str, converter_names: List[str]
    ) -> Tuple[str, List[str]]:
        """Synchronous transform (delegates to PayloadTransformer).

        Args:
            payload: Original payload
            converter_names: List of converter names

        Returns:
            Tuple of (transformed_payload, errors)
        """
        return self._transformer.transform(payload, converter_names)
