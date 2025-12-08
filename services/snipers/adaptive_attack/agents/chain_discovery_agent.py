"""
Chain Discovery Agent.

Purpose: LLM-powered intelligent converter chain generation
Role: Generate optimal chains based on failure analysis context
Dependencies: langchain.agents.create_agent, ChainDiscoveryDecision model
"""

import logging
from typing import Any

from dotenv import load_dotenv
load_dotenv()

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from services.snipers.adaptive_attack.models.chain_discovery import (
    ChainDiscoveryContext,
    ChainDiscoveryDecision,
    ChainSelectionResult,
    ConverterChainCandidate,
)
from services.snipers.adaptive_attack.prompts.chain_discovery_prompt import (
    CHAIN_DISCOVERY_SYSTEM_PROMPT,
    build_chain_discovery_user_prompt,
)
from services.snipers.utils.converters import SUFFIX_CONVERTER_NAMES
from services.snipers.utils.prompt_articulation.models.tool_intelligence import ReconIntelligence

logger = logging.getLogger(__name__)

# Maximum converters per chain to prevent over-stacking and unrecognizable payloads
MAX_CHAIN_LENGTH = 3
# Length penalty: points deducted per converter over 2
LENGTH_PENALTY_FACTOR = 5
# Bonus for optimal length (2-3 converters)
OPTIMAL_LENGTH_BONUS = 10

# Base converters available in the system
_BASE_CONVERTERS = [
    "homoglyph",
    "unicode_substitution",
    "leetspeak",
    "base64",
    "rot13",
    "character_space",
    "morse_code",
    "html_entity",
    "xml_escape",
    "json_escape",
]

# All converters including suffix converters
AVAILABLE_CONVERTERS = _BASE_CONVERTERS + SUFFIX_CONVERTER_NAMES


class ChainDiscoveryAgent:
    """
    LLM-powered chain discovery using structured output.

    Uses create_agent with ToolStrategy(ChainDiscoveryDecision) for
    guaranteed structured chain candidates.
    """

    def __init__(self, agent: Any = None):
        """
        Initialize agent with LangChain.

        Args:
            agent: Optional agent for dependency injection (testing)
        """
        if agent is None:
            agent = create_agent(
                model="google_genai:gemini-2.5-flash",
                response_format=ToolStrategy(ChainDiscoveryDecision),
            )
        self._agent = agent
        self.logger = logging.getLogger(__name__)

    async def generate(
        self,
        context: ChainDiscoveryContext,
        tried_converters: list[list[str]],
        objective: str,
        recon_intelligence: ReconIntelligence | None = None,
        config: dict = None,
    ) -> ChainDiscoveryDecision:
        """
        Generate converter chain candidates via LLM.

        Args:
            context: ChainDiscoveryContext from failure analysis
            tried_converters: All converter chains attempted so far
            objective: Attack objective
            recon_intelligence: Structured recon data for context-aware chain selection

        Returns:
            ChainDiscoveryDecision with chain candidates and reasoning

        Raises:
            ValueError: If LLM fails to produce structured output
        """
        user_prompt = build_chain_discovery_user_prompt(
            context=context,
            tried_converters=tried_converters,
            objective=objective,
            recon_intelligence=recon_intelligence,
        )

        self.logger.info("[ChainDiscoveryAgent] Generating chain candidates via LLM")
        self.logger.info(f"  Context: {len(context.defense_signals)} defense signals")
        self.logger.info(f"  Tried chains: {len(tried_converters)}")

        result = await self._agent.ainvoke(
            {
                "messages": [
                    {"role": "system", "content": CHAIN_DISCOVERY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            },
            config=config or {},
        )

        decision: ChainDiscoveryDecision | None = result.get("structured_response")

        if decision is None:
            raise ValueError("LLM did not return structured ChainDiscoveryDecision")

        # Validate chains against available converters
        decision = self._validate_and_filter_chains(decision, tried_converters)

        self.logger.info(
            f"  Generated {len(decision.chains)} chain candidates"
        )
        for i, chain in enumerate(decision.chains):
            self.logger.info(
                f"    {i+1}. {chain.converters} (confidence: {chain.expected_effectiveness:.2f})"
            )

        return decision

    def _validate_and_filter_chains(
        self,
        decision: ChainDiscoveryDecision,
        tried_converters: list[list[str]],
    ) -> ChainDiscoveryDecision:
        """
        Validate chains against available converters and filter duplicates.

        Args:
            decision: Raw LLM decision
            tried_converters: Already tried chains

        Returns:
            Validated decision with only valid, novel chains
        """
        valid_chains: list[ConverterChainCandidate] = []

        for chain in decision.chains:
            # Check all converters are valid
            invalid_converters = [
                c for c in chain.converters if c not in AVAILABLE_CONVERTERS
            ]
            if invalid_converters:
                self.logger.warning(
                    f"  Removing invalid converters: {invalid_converters}"
                )
                chain.converters = [
                    c for c in chain.converters if c in AVAILABLE_CONVERTERS
                ]

            # Skip empty chains
            if not chain.converters:
                continue

            # Skip exact duplicates of tried chains
            if chain.converters in tried_converters:
                self.logger.info(
                    f"  Skipping duplicate chain: {chain.converters}"
                )
                continue

            valid_chains.append(chain)

        # Ensure at least one chain
        if not valid_chains:
            self.logger.warning("  No valid chains after filtering, using fallback")
            valid_chains = [self._create_fallback_chain(tried_converters)]

        return ChainDiscoveryDecision(
            chains=valid_chains,
            reasoning=decision.reasoning,
            primary_defense_target=decision.primary_defense_target,
            exploration_vs_exploitation=decision.exploration_vs_exploitation,
            confidence=decision.confidence,
        )

    def _create_fallback_chain(
        self, tried_converters: list[list[str]]
    ) -> ConverterChainCandidate:
        """Create a fallback chain when LLM produces no valid chains."""
        tried_flat = set()
        for chain in tried_converters:
            tried_flat.update(chain)

        # Find untried converters
        untried = [c for c in AVAILABLE_CONVERTERS if c not in tried_flat]

        if untried:
            # Use first untried converter
            converters = [untried[0]]
        else:
            # Use least-tried combination
            converters = ["homoglyph", "unicode_substitution"]

        return ConverterChainCandidate(
            converters=converters,
            expected_effectiveness=0.3,
            defense_bypass_strategy="Fallback chain - exploring untried options",
            converter_interactions="Single converter or basic combination",
        )

    def _calculate_length_score(self, chain_length: int) -> float:
        """
        Calculate length-based score adjustment.

        Penalizes longer chains to encourage simpler, more intelligible payloads.
        - Bonus for 2-3 converters (optimal range)
        - Penalty for chains over 3 converters (though filtered earlier)

        Args:
            chain_length: Number of converters in the chain

        Returns:
            Score adjustment (can be positive or negative)
        """
        if 2 <= chain_length <= 3:
            # Bonus for optimal length
            self.logger.debug(
                f"  Optimal length bonus: +{OPTIMAL_LENGTH_BONUS} "
                f"(chain has {chain_length} converters)"
            )
            return float(OPTIMAL_LENGTH_BONUS)
        elif chain_length > 3:
            # Penalty for longer chains
            penalty = (chain_length - 2) * LENGTH_PENALTY_FACTOR
            self.logger.debug(
                f"  Length penalty: -{penalty} (chain has {chain_length} converters)"
            )
            return -float(penalty)
        else:
            # Single converter (neutral, slight penalty)
            self.logger.debug(
                f"  Single converter (minimal obfuscation): (chain has {chain_length} converter)"
            )
            return 0.0

    def select_best_chain(
        self,
        decision: ChainDiscoveryDecision,
        context: ChainDiscoveryContext,
    ) -> ChainSelectionResult:
        """
        Select the best chain from candidates with full observability.
        Filters chains by MAX_CHAIN_LENGTH to prevent over-stacking.

        Args:
            decision: ChainDiscoveryDecision with candidates
            context: ChainDiscoveryContext for additional scoring

        Returns:
            ChainSelectionResult with selected chain and full reasoning
        """
        rejected_chains: list[dict] = []
        all_candidates: list[dict] = []
        defense_match_details: dict = {
            "defense_signals": context.defense_signals,
            "matches_found": [],
        }

        # Handle empty chains - fallback
        if not decision.chains:
            self.logger.warning("  No chains available, using ultimate fallback")
            return ChainSelectionResult(
                selected_chain=["homoglyph"],
                selection_method="fallback",
                selection_reasoning="No chain candidates available, using default homoglyph converter",
                all_candidates=[],
                defense_match_details=defense_match_details,
                rejected_chains=[],
            )

        # Phase 0: Filter chains by MAX_CHAIN_LENGTH
        self.logger.info(f"\n  === Chain Length Filtering ===")
        self.logger.info(f"  MAX_CHAIN_LENGTH: {MAX_CHAIN_LENGTH}")
        self.logger.info(f"  Total candidates: {len(decision.chains)}")

        valid_chains = []
        oversized_chains = []

        for chain in decision.chains:
            chain_length = len(chain.converters)
            if chain_length <= MAX_CHAIN_LENGTH:
                valid_chains.append(chain)
                self.logger.debug(
                    f"    ✓ Chain length {chain_length}: {chain.converters}"
                )
            else:
                oversized_chains.append(chain)
                rejected_chains.append({
                    "chain": chain.converters,
                    "reason": f"Exceeds MAX_CHAIN_LENGTH={MAX_CHAIN_LENGTH} (has {chain_length})",
                    "strategy_checked": chain.defense_bypass_strategy[:100],
                })
                self.logger.debug(
                    f"    ✗ Chain length {chain_length} (exceeds limit): {chain.converters}"
                )

        self.logger.info(f"  Valid chains (within limit): {len(valid_chains)}/{len(decision.chains)}")

        # Fallback: if all chains exceed limit, use the shortest one
        if not valid_chains:
            self.logger.warning(
                f"  All chains exceed MAX_CHAIN_LENGTH={MAX_CHAIN_LENGTH}. "
                f"Using shortest chain as fallback."
            )
            shortest = min(decision.chains, key=lambda c: len(c.converters))
            shortest_length = len(shortest.converters)
            self.logger.info(
                f"  Fallback chain length: {shortest_length} converters"
            )
            valid_chains = [shortest]

        # Sort by expected effectiveness
        sorted_chains = sorted(
            valid_chains,
            key=lambda c: c.expected_effectiveness,
            reverse=True
        )

        # Build all candidates list with ranking and length scoring
        for rank, chain in enumerate(sorted_chains, 1):
            # Calculate length-based score adjustment
            chain_length = len(chain.converters)
            length_score_adjustment = self._calculate_length_score(chain_length)

            all_candidates.append({
                "rank": rank,
                "converters": chain.converters,
                "length": chain_length,
                "expected_effectiveness": chain.expected_effectiveness,
                "length_score_adjustment": length_score_adjustment,
                "defense_bypass_strategy": chain.defense_bypass_strategy,
                "converter_interactions": chain.converter_interactions,
            })

        self.logger.info("\n  === Chain Selection Process ===")
        self.logger.info(f"  Defense signals to match: {context.defense_signals}")
        self.logger.info(f"  Candidates ranked by effectiveness:")
        for candidate in all_candidates:
            self.logger.info(
                f"    #{candidate['rank']}: {candidate['converters']} "
                f"(len: {candidate['length']}, eff: {candidate['expected_effectiveness']:.2f}, "
                f"length_adj: {candidate['length_score_adjustment']:+.1f})"
            )

        # Phase 1: Try to find chains that match detected defenses
        defense_keywords = set(context.defense_signals)
        self.logger.info(f"\n  Phase 1: Searching for defense-matching chains...")

        for chain in sorted_chains:
            strategy_lower = chain.defense_bypass_strategy.lower()
            matched_defenses = []

            for kw in defense_keywords:
                kw_normalized = kw.replace("_", " ")
                if kw_normalized in strategy_lower:
                    matched_defenses.append(kw)

            if matched_defenses:
                defense_match_details["matches_found"].append({
                    "chain": chain.converters,
                    "matched_defenses": matched_defenses,
                    "strategy": chain.defense_bypass_strategy,
                })

                reasoning = (
                    f"Selected because strategy '{chain.defense_bypass_strategy[:80]}...' "
                    f"addresses detected defenses: {matched_defenses}. "
                    f"Expected effectiveness: {chain.expected_effectiveness:.2f}. "
                    f"Converter interactions: {chain.converter_interactions}"
                )

                self.logger.info(f"  MATCH FOUND: {chain.converters}")
                self.logger.info(f"    Matched defenses: {matched_defenses}")
                self.logger.info(f"    Strategy: {chain.defense_bypass_strategy[:60]}...")

                return ChainSelectionResult(
                    selected_chain=chain.converters,
                    selection_method="defense_match",
                    selection_reasoning=reasoning,
                    all_candidates=all_candidates,
                    defense_match_details=defense_match_details,
                    rejected_chains=rejected_chains,
                )
            else:
                rejected_chains.append({
                    "chain": chain.converters,
                    "reason": f"Strategy does not match any defense signals",
                    "strategy_checked": chain.defense_bypass_strategy[:100],
                })

        # Phase 2: No defense match - use highest effectiveness
        self.logger.info(f"\n  Phase 2: No defense match, selecting highest effectiveness...")
        best = sorted_chains[0]

        reasoning = (
            f"No chain strategy matched detected defenses {list(defense_keywords)}. "
            f"Selected highest effectiveness chain: {best.converters} "
            f"(effectiveness: {best.expected_effectiveness:.2f}). "
            f"Strategy: {best.defense_bypass_strategy}. "
            f"Interactions: {best.converter_interactions}"
        )

        self.logger.info(f"  SELECTED: {best.converters}")
        self.logger.info(f"    Effectiveness: {best.expected_effectiveness:.2f}")
        self.logger.info(f"    Strategy: {best.defense_bypass_strategy[:60]}...")

        return ChainSelectionResult(
            selected_chain=best.converters,
            selection_method="highest_confidence",
            selection_reasoning=reasoning,
            all_candidates=all_candidates,
            defense_match_details=defense_match_details,
            rejected_chains=rejected_chains,
        )