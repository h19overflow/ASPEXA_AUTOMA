"""
Internal helpers for ChainDiscoveryAgent.

Handles chain validation, fallback creation, length scoring,
and best-chain selection logic.
"""

import logging
from typing import Any

from services.snipers.core.adaptive_models.chain_discovery import (
    ChainDiscoveryContext,
    ChainDiscoveryDecision,
    ChainSelectionResult,
    ConverterChainCandidate,
)
from services.snipers.core.agents.consts import (
    AVAILABLE_CONVERTERS,
    LENGTH_PENALTY_FACTOR,
    MAX_CHAIN_LENGTH,
    OPTIMAL_LENGTH_BONUS,
)

logger = logging.getLogger(__name__)


def validate_and_filter_chains(
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
        invalid = [c for c in chain.converters if c not in AVAILABLE_CONVERTERS]
        if invalid:
            logger.warning(f"  Removing invalid converters: {invalid}")
            chain.converters = [c for c in chain.converters if c in AVAILABLE_CONVERTERS]

        if not chain.converters:
            continue

        if chain.converters in tried_converters:
            logger.info(f"  Skipping duplicate chain: {chain.converters}")
            continue

        valid_chains.append(chain)

    if not valid_chains:
        logger.warning("  No valid chains after filtering, using fallback")
        valid_chains = [create_fallback_chain(tried_converters)]

    return ChainDiscoveryDecision(
        chains=valid_chains,
        reasoning=decision.reasoning,
        primary_defense_target=decision.primary_defense_target,
        exploration_vs_exploitation=decision.exploration_vs_exploitation,
        confidence=decision.confidence,
    )


def create_fallback_chain(tried_converters: list[list[str]]) -> ConverterChainCandidate:
    """Create a fallback chain when LLM produces no valid chains."""
    tried_flat = {c for chain in tried_converters for c in chain}
    untried = [c for c in AVAILABLE_CONVERTERS if c not in tried_flat]

    converters = [untried[0]] if untried else ["homoglyph", "unicode_substitution"]

    return ConverterChainCandidate(
        converters=converters,
        expected_effectiveness=0.3,
        defense_bypass_strategy="Fallback chain - exploring untried options",
        converter_interactions="Single converter or basic combination",
    )


def calculate_length_score(chain_length: int) -> float:
    """
    Calculate length-based score adjustment.

    Penalizes longer chains to encourage simpler, more intelligible payloads.

    Args:
        chain_length: Number of converters in the chain

    Returns:
        Score adjustment (positive for optimal, negative for long chains)
    """
    if 2 <= chain_length <= 3:
        logger.debug(f"  Optimal length bonus: +{OPTIMAL_LENGTH_BONUS} ({chain_length} converters)")
        return float(OPTIMAL_LENGTH_BONUS)
    elif chain_length > 3:
        penalty = (chain_length - 2) * LENGTH_PENALTY_FACTOR
        logger.debug(f"  Length penalty: -{penalty} ({chain_length} converters)")
        return -float(penalty)
    else:
        logger.debug(f"  Single converter (minimal obfuscation): ({chain_length} converter)")
        return 0.0


def select_best_chain(
    decision: ChainDiscoveryDecision,
    context: ChainDiscoveryContext,
) -> ChainSelectionResult:
    """
    Select the best chain from candidates with full observability.

    Filters chains by MAX_CHAIN_LENGTH, then picks by defense match
    or highest effectiveness.

    Args:
        decision: ChainDiscoveryDecision with candidates
        context: ChainDiscoveryContext for additional scoring

    Returns:
        ChainSelectionResult with selected chain and full reasoning
    """
    rejected_chains: list[dict] = []
    defense_match_details: dict[str, Any] = {
        "defense_signals": context.defense_signals,
        "matches_found": [],
    }

    if not decision.chains:
        logger.warning("  No chains available, using ultimate fallback")
        return ChainSelectionResult(
            selected_chain=["homoglyph"],
            selection_method="fallback",
            selection_reasoning="No chain candidates available, using default homoglyph converter",
            all_candidates=[],
            defense_match_details=defense_match_details,
            rejected_chains=[],
        )

    valid_chains, rejected_chains = _filter_by_length(decision.chains, rejected_chains)
    sorted_chains = sorted(valid_chains, key=lambda c: c.expected_effectiveness, reverse=True)
    all_candidates = _build_candidates_list(sorted_chains)

    _log_candidates(context, all_candidates)

    defense_result = _find_defense_match(sorted_chains, context, defense_match_details, rejected_chains, all_candidates)
    if defense_result:
        return defense_result

    return _select_highest_effectiveness(sorted_chains, defense_match_details, all_candidates, rejected_chains)


# --- private helpers ---


def _filter_by_length(
    chains: list[ConverterChainCandidate],
    rejected_chains: list[dict],
) -> tuple[list[ConverterChainCandidate], list[dict]]:
    """Filter chains exceeding MAX_CHAIN_LENGTH, falling back to shortest if all exceed."""
    logger.info(f"\n  === Chain Length Filtering (max={MAX_CHAIN_LENGTH}) ===")
    valid, oversized = [], []

    for chain in chains:
        length = len(chain.converters)
        if length <= MAX_CHAIN_LENGTH:
            valid.append(chain)
        else:
            oversized.append(chain)
            rejected_chains.append({
                "chain": chain.converters,
                "reason": f"Exceeds MAX_CHAIN_LENGTH={MAX_CHAIN_LENGTH} (has {length})",
                "strategy_checked": chain.defense_bypass_strategy[:100],
            })

    logger.info(f"  Valid chains: {len(valid)}/{len(chains)}")

    if not valid:
        shortest = min(chains, key=lambda c: len(c.converters))
        logger.warning(f"  All chains exceed limit, using shortest ({len(shortest.converters)} converters)")
        valid = [shortest]

    return valid, rejected_chains


def _build_candidates_list(sorted_chains: list[ConverterChainCandidate]) -> list[dict]:
    return [
        {
            "rank": rank,
            "converters": chain.converters,
            "length": len(chain.converters),
            "expected_effectiveness": chain.expected_effectiveness,
            "length_score_adjustment": calculate_length_score(len(chain.converters)),
            "defense_bypass_strategy": chain.defense_bypass_strategy,
            "converter_interactions": chain.converter_interactions,
        }
        for rank, chain in enumerate(sorted_chains, 1)
    ]


def _log_candidates(context: ChainDiscoveryContext, all_candidates: list[dict]) -> None:
    logger.info(f"\n  === Chain Selection (defense signals: {context.defense_signals}) ===")
    for c in all_candidates:
        logger.info(
            f"    #{c['rank']}: {c['converters']} "
            f"(eff: {c['expected_effectiveness']:.2f}, len_adj: {c['length_score_adjustment']:+.1f})"
        )


def _find_defense_match(
    sorted_chains: list[ConverterChainCandidate],
    context: ChainDiscoveryContext,
    defense_match_details: dict,
    rejected_chains: list[dict],
    all_candidates: list[dict],
) -> ChainSelectionResult | None:
    """Return the first chain whose strategy mentions a detected defense, or None."""
    defense_keywords = set(context.defense_signals)

    for chain in sorted_chains:
        strategy_lower = chain.defense_bypass_strategy.lower()
        matched = [kw for kw in defense_keywords if kw.replace("_", " ") in strategy_lower]

        if matched:
            defense_match_details["matches_found"].append({
                "chain": chain.converters,
                "matched_defenses": matched,
                "strategy": chain.defense_bypass_strategy,
            })
            reasoning = (
                f"Strategy addresses detected defenses: {matched}. "
                f"Effectiveness: {chain.expected_effectiveness:.2f}. "
                f"Interactions: {chain.converter_interactions}"
            )
            logger.info(f"  MATCH FOUND: {chain.converters} → defenses {matched}")
            return ChainSelectionResult(
                selected_chain=chain.converters,
                selection_method="defense_match",
                selection_reasoning=reasoning,
                all_candidates=all_candidates,
                defense_match_details=defense_match_details,
                rejected_chains=rejected_chains,
            )

        rejected_chains.append({
            "chain": chain.converters,
            "reason": "Strategy does not match any defense signals",
            "strategy_checked": chain.defense_bypass_strategy[:100],
        })

    return None


def _select_highest_effectiveness(
    sorted_chains: list[ConverterChainCandidate],
    defense_match_details: dict,
    all_candidates: list[dict],
    rejected_chains: list[dict],
) -> ChainSelectionResult:
    best = sorted_chains[0]
    reasoning = (
        f"No defense match found. Selected highest effectiveness: {best.converters} "
        f"(effectiveness: {best.expected_effectiveness:.2f}). "
        f"Strategy: {best.defense_bypass_strategy}"
    )
    logger.info(f"  SELECTED (highest effectiveness): {best.converters}")
    return ChainSelectionResult(
        selected_chain=best.converters,
        selection_method="highest_confidence",
        selection_reasoning=reasoning,
        all_candidates=all_candidates,
        defense_match_details=defense_match_details,
        rejected_chains=rejected_chains,
    )
