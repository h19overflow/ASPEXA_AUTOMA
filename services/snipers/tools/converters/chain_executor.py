"""
Converter Chain Executor.

Purpose: Apply a sequence of PyRIT converters to payloads
Role: Phase 2 of attack flow - transform articulated payloads through converter chains
Dependencies: PyRIT converters (built-in + custom), ConverterChain model

Available converters (from pyrit_bridge):
- PyRIT built-in: base64, rot13, caesar_cipher, url, hex, unicode_confusable
- Custom: html_entity, json_escape, xml_escape, leetspeak, morse_code,
          character_space, homoglyph, unicode_substitution
"""

import logging
from typing import Any

from services.snipers.chain_discovery.models import ConverterChain
from services.snipers.tools.pyrit_bridge import ConverterFactory, PayloadTransformer

logger = logging.getLogger(__name__)


class ChainExecutor:
    """
    Executes converter chains on payloads.

    Uses PyRIT bridge's ConverterFactory and PayloadTransformer
    which includes both PyRIT built-in and custom converters.

    Available converters:
    - PyRIT: base64, rot13, caesar_cipher, url, hex, unicode_confusable
    - Custom: html_entity, json_escape, xml_escape, leetspeak, morse_code,
              character_space, homoglyph, unicode_substitution
    """

    def __init__(self):
        """Initialize with PyRIT converter factory."""
        self._factory = ConverterFactory()
        self._transformer = PayloadTransformer(self._factory)
        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        chain: ConverterChain,
        payloads: list[str],
    ) -> list[dict[str, Any]]:
        """
        Apply converter chain to list of payloads.

        Args:
            chain: ConverterChain with converter names and params
            payloads: List of raw payload strings

        Returns:
            List of dicts with original, converted payload, and metadata
        """
        if not payloads:
            return []

        if not chain or not chain.converter_names:
            # No converters - return payloads unchanged
            return [
                {
                    "original": p,
                    "converted": p,
                    "chain_id": "none",
                    "converters_applied": [],
                }
                for p in payloads
            ]

        # Apply chain to each payload using PayloadTransformer
        results = []
        for payload in payloads:
            converted, errors = await self._transformer.transform_async(
                payload, chain.converter_names
            )

            # Determine which converters were actually applied (no errors)
            applied = [
                name for name in chain.converter_names
                if not any(name in err for err in errors)
            ]

            results.append({
                "original": payload,
                "converted": converted,
                "chain_id": chain.chain_id,
                "converters_applied": applied,
                "errors": errors if errors else None,
            })

        return results

    def list_available_converters(self) -> list[str]:
        """Return list of available converter names."""
        # Get unique short names (filter out class name duplicates)
        all_names = self._factory.get_available_names()
        # Return only lowercase names (short names)
        return sorted([n for n in all_names if n[0].islower()])
