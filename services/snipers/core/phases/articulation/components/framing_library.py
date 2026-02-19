"""
Catalog of framing strategies with effectiveness ratings.

Purpose: Provides repository of legitimate personas for payload framing.
Strategies are selected based on target domain and historical effectiveness.
"""

from typing import Protocol

from services.snipers.core.phases.articulation.config import (
    DEFAULT_STRATEGIES,
    DOMAIN_STRATEGY_BOOST,
)
from services.snipers.core.phases.articulation.models.framing_strategy import (
    FramingStrategy,
    FramingType,
)


class EffectivenessProvider(Protocol):
    """Interface for effectiveness data source."""

    def get_success_rate(self, framing_type: FramingType, domain: str) -> float:
        """Get historical success rate for framing/domain combo."""
        ...


class FramingLibrary:
    """Repository of framing strategies with effectiveness tracking.

    Selects optimal framing based on:
    1. Target domain fit (domain-specific boost)
    2. Historical effectiveness (learned from tracker)
    3. Detection risk (prefer low-risk when possible)
    """

    def __init__(
        self,
        strategies: dict[FramingType, FramingStrategy] | None = None,
        effectiveness_provider: EffectivenessProvider | None = None,
    ):
        """Initialize with strategy catalog and effectiveness tracker.

        Args:
            strategies: Strategy definitions (defaults to config if None)
            effectiveness_provider: Source of effectiveness data
        """
        self.strategies = strategies or DEFAULT_STRATEGIES.copy()
        self.effectiveness_provider = effectiveness_provider

    def get_strategy(self, framing_type: FramingType) -> FramingStrategy:
        """Retrieve strategy by type."""
        if framing_type not in self.strategies:
            raise ValueError(f"Unknown framing type: {framing_type}")
        return self.strategies[framing_type]

    def select_optimal_strategy(
        self,
        domain: str,
        exclude_high_risk: bool = True,
    ) -> FramingStrategy:
        """Select best framing strategy for domain.

        Args:
            domain: Target application domain
            exclude_high_risk: Skip high-detection-risk strategies

        Returns:
            Highest-scoring strategy for domain
        """
        candidates = [
            s for s in self.strategies.values()
            if not (exclude_high_risk and s.detection_risk == "high")
        ]

        if not candidates:
            # Fallback if all filtered out
            candidates = list(self.strategies.values())

        # Score each strategy
        scored = [
            (self._calculate_score(strategy, domain), strategy)
            for strategy in candidates
        ]

        # Return highest-scoring
        _, best_strategy = max(scored, key=lambda x: x[0])
        return best_strategy

    def list_strategies(self) -> list[FramingStrategy]:
        """List all available strategies."""
        return list(self.strategies.values())

    def _calculate_score(self, strategy: FramingStrategy, domain: str) -> float:
        """Calculate composite score for strategy.

        Combines:
        - Base domain effectiveness (from strategy config)
        - Domain-specific boost (from config constants)
        - Historical success rate (from effectiveness tracker)
        """
        base_score = strategy.get_effectiveness(domain)

        # Apply domain-specific boost
        boost = DOMAIN_STRATEGY_BOOST.get(domain, {}).get(strategy.type, 0.0)

        # Incorporate historical data if available
        historical_score = 0.0
        if self.effectiveness_provider:
            historical_score = self.effectiveness_provider.get_success_rate(
                strategy.type, domain
            )

        # Weighted combination: 40% config, 30% boost, 30% historical
        return (0.4 * base_score) + (0.3 * boost) + (0.3 * historical_score)
