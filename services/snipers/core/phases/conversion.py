"""
Phase 2: Conversion.

Purpose: Apply converter chains to articulated payloads
Role: Second phase of attack flow - transforms payloads through converter chains
Dependencies: ChainExecutor, ConverterChain

Usage:
    from services.snipers.core.phases import Conversion

    # From Phase 1 result
    phase2 = Conversion()
    result = await phase2.execute(
        payloads=phase1_result.articulated_payloads,
        chain=phase1_result.selected_chain,
    )

    # Or with manual chain override
    from services.snipers.models.chain_models.models import ConverterChain
    custom_chain = ConverterChain.from_converter_names(["homoglyph", "xml_escape"])
    result = await phase2.execute(payloads=my_payloads, chain=custom_chain)

Available converters:
- PyRIT: base64, rot13, caesar_cipher, url, hex, unicode_confusable
- Custom: html_entity, json_escape, xml_escape, leetspeak, morse_code,
          character_space, homoglyph, unicode_substitution
"""

import logging
from typing import Any

from services.snipers.models.chain_models.models import ConverterChain
from services.snipers.models import ConvertedPayload, Phase2Result
from services.snipers.core.phases.converters.chain_executor import ChainExecutor

logger = logging.getLogger(__name__)


class Conversion:
    """
    Phase 2: Payload Conversion.

    Applies converter chain to payloads from Phase 1.
    Produces attack-ready converted payloads.

    User intervention points:
    - Override the chain selection from Phase 1
    - Provide manually crafted payloads
    - Re-run with different converter parameters
    """

    def __init__(self):
        """Initialize with chain executor."""
        self.executor = ChainExecutor()
        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        payloads: list[str],
        chain: ConverterChain | None = None,
        converter_names: list[str] | None = None,
        converter_params: dict[str, dict[str, Any]] | None = None,
    ) -> Phase2Result:
        """
        Apply converter chain to payloads.

        Args:
            payloads: List of articulated payload strings (from Phase 1)
            chain: ConverterChain to apply (from Phase 1 or manual)
            converter_names: Alternative: specify converter names directly
            converter_params: Optional params for converters

        Returns:
            Phase2Result with converted payloads
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info("Phase 2: Conversion")
        self.logger.info(f"{'='*60}\n")

        # Build chain from names if no chain provided
        if chain is None:
            if converter_names:
                chain = ConverterChain.from_converter_names(
                    converter_names=converter_names,
                    params=converter_params,
                )
                self.logger.info(f"Created chain from names: {converter_names}")
            else:
                # No conversion - pass through
                self.logger.info("No chain specified - payloads will pass through unchanged")
                chain = ConverterChain.from_converter_names([])

        self.logger.info(f"Chain ID: {chain.chain_id}")
        self.logger.info(f"Converters: {chain.converter_names}")
        self.logger.info(f"Payloads to convert: {len(payloads)}")
        self.logger.info("-" * 40)

        # Execute chain on payloads
        raw_results = await self.executor.execute(chain, payloads)

        # Convert to dataclass format
        converted_payloads = []
        success_count = 0
        error_count = 0

        for i, raw in enumerate(raw_results):
            payload = ConvertedPayload(
                original=raw["original"],
                converted=raw["converted"],
                chain_id=raw["chain_id"],
                converters_applied=raw["converters_applied"],
                errors=raw.get("errors"),
            )
            converted_payloads.append(payload)

            if raw.get("errors"):
                error_count += 1
            else:
                success_count += 1

            # Log conversion summary
            orig_len = len(raw["original"])
            conv_len = len(raw["converted"])
            converters = " → ".join(raw["converters_applied"]) or "none"
            self.logger.info(f"  [{i+1}] {orig_len} chars → {conv_len} chars via [{converters}]")

        self.logger.info("-" * 40)
        self.logger.info(f"Success: {success_count}, Errors: {error_count}")
        self.logger.info(f"\n{'='*60}")
        self.logger.info("Phase 2 Complete - Payloads Ready for Attack")
        self.logger.info(f"{'='*60}\n")

        return Phase2Result(
            chain_id=chain.chain_id,
            converter_names=chain.converter_names,
            payloads=converted_payloads,
            success_count=success_count,
            error_count=error_count,
        )

    def list_available_converters(self) -> list[str]:
        """List available converter names for manual chain building."""
        return self.executor.list_available_converters()

