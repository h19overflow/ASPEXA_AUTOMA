"""
Chain generator strategies for discovering converter combinations.

Implements multiple strategies:
1. Heuristic: Match converters to defense patterns
2. Combinatorial: Generate promising combinations
3. Evolutionary: GA-based optimization (delegated to optimizer)
"""

import logging
from typing import Any
from itertools import combinations
from services.snipers.chain_discovery.models import ConverterChain

logger = logging.getLogger(__name__)


class HeuristicChainGenerator:
    """
    Generate chains using heuristic matching of converters to defenses.

    Maps defense mechanisms to likely effective converters.
    """

    # Defense mechanism -> converter mapping
    DEFENSE_CONVERTER_MAP = {
        "keyword_filter": ["leetspeak", "unicode_substitution", "homoglyph"],
        "pattern_matching": ["character_space", "morse_code", "base64"],
        "rate_limit": ["batch_payload"],  # Combine into fewer turns
        "content_analysis": ["base64", "rot13", "hex_encoding"],
        "instruction_following": ["prompt_injection", "role_play"],
    }

    # Available converters in system
    ALL_CONVERTERS = [
        "leetspeak", "unicode_substitution", "homoglyph",
        "character_space", "morse_code", "base64", "rot13",
        "rot13", "html_entity", "xml_escape", "json_escape"
    ]

    def __init__(self):
        """Initialize generator."""
        self.logger = logging.getLogger(__name__)

    async def generate_chains(
        self,
        context: dict[str, Any],
        count: int = 5
    ) -> list[ConverterChain]:
        """
        Generate chains by heuristic defense-to-converter matching.

        Args:
            context: Attack context with defense_patterns
            count: Number of chains to generate

        Returns:
            List of candidate chains
        """
        defense_patterns = context.get("defense_patterns", [])

        if not defense_patterns:
            return await self._generate_fallback_chains(count)

        chains = []

        # Match converters to each defense
        suggested_converters = []
        for defense in defense_patterns:
            converters = self.DEFENSE_CONVERTER_MAP.get(defense, [])
            suggested_converters.extend(converters)

        # Deduplicate and limit
        suggested_converters = list(set(suggested_converters))[:count + 2]

        # Generate combinations of 2-3 converters
        for size in [2, 3]:
            for combo in combinations(suggested_converters, size):
                if len(chains) >= count:
                    break
                chain = ConverterChain.from_converter_names(
                    converter_names=list(combo),
                    defense_patterns=defense_patterns
                )
                chains.append(chain)

        self.logger.info(
            f"Generated {len(chains)} heuristic chains",
            extra={"defenses": defense_patterns, "suggested_converters": suggested_converters}
        )

        return chains[:count]

    async def _generate_fallback_chains(self, count: int) -> list[ConverterChain]:
        """Generate fallback chains when no defense patterns available."""
        chains = []

        # Create some diverse chains
        default_combos = [
            ["leetspeak", "base64"],
            ["unicode_substitution", "rot13"],
            ["character_space", "html_entity"],
            ["homoglyph", "json_escape"],
            ["morse_code", "base64"],
        ]

        for combo in default_combos[:count]:
            chain = ConverterChain.from_converter_names(converter_names=combo)
            chains.append(chain)

        return chains


class CombinatorialChainGenerator:
    """
    Generate all promising combinations of converters.

    Starts with heuristic suggestions, expands to combinations.
    Useful for exhaustive search in high-value targets.
    """

    def __init__(self, heuristic_gen: HeuristicChainGenerator):
        """
        Initialize with heuristic generator.

        Args:
            heuristic_gen: Heuristic generator for base suggestions
        """
        self.heuristic = heuristic_gen
        self.logger = logging.getLogger(__name__)

    async def generate_chains(
        self,
        context: dict[str, Any],
        count: int = 20
    ) -> list[ConverterChain]:
        """
        Generate combinatorial chains.

        Args:
            context: Attack context
            count: Maximum chains to generate

        Returns:
            List of candidate chains
        """
        # Start with heuristic suggestions
        heuristic_chains = await self.heuristic.generate_chains(context, count=5)

        chains = heuristic_chains.copy()

        # Expand to more combinations if needed
        available_converters = set()
        for chain in heuristic_chains:
            available_converters.update(chain.converter_names)

        available_converters = list(available_converters)

        # Generate 2-3 converter combinations from available set
        for size in [2, 3]:
            if len(chains) >= count:
                break
            for combo in combinations(available_converters, size):
                if len(chains) >= count:
                    break
                # Avoid duplicates
                if not any(
                    set(c.converter_names) == set(combo)
                    for c in chains
                ):
                    chain = ConverterChain.from_converter_names(
                        converter_names=list(combo),
                        defense_patterns=context.get("defense_patterns", [])
                    )
                    chains.append(chain)

        self.logger.info(
            f"Generated {len(chains)} combinatorial chains",
            extra={"available_converters": available_converters}
        )

        return chains[:count]
