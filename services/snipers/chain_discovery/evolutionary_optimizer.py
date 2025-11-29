"""
Evolutionary chain optimizer using genetic algorithm.

Uses mutation, crossover, and selection to evolve effective converter chains.
Designed for continuous improvement across multiple attack iterations.
"""

import random
import logging
from typing import Any
from services.snipers.chain_discovery.models import ConverterChain

logger = logging.getLogger(__name__)


class EvolutionaryChainOptimizer:
    """
    Evolve converter chains through genetic algorithm.

    Operators:
    - Mutation: Swap, replace, add, remove converters
    - Crossover: Combine parent chains
    - Selection: Tournament selection of fittest
    - Elitism: Preserve best performers
    """

    # Available converters
    AVAILABLE_CONVERTERS = [
        "leetspeak", "unicode_substitution", "homoglyph",
        "character_space", "morse_code", "base64", "rot13",
        "html_entity", "xml_escape", "json_escape"
    ]

    def __init__(self, population_size: int = 20, generations: int = 3):
        """
        Initialize optimizer.

        Args:
            population_size: Number of chains per generation
            generations: Number of generations to evolve
        """
        self.population_size = population_size
        self.generations = generations
        self.logger = logging.getLogger(__name__)

    async def generate_chains(
        self,
        context: dict[str, Any],
        count: int = 5
    ) -> list[ConverterChain]:
        """
        Generate chains via evolutionary optimization.

        Args:
            context: Attack context with initial population hint
            count: Number of best chains to return

        Returns:
            List of evolved chains
        """
        # Initialize population from context seed chains if available
        seed_chains = context.get("seed_chains", [])
        population = self._initialize_population(seed_chains)

        self.logger.info(
            f"Starting evolution with {len(population)} initial chains",
            extra={"generations": self.generations}
        )

        # Evolve for specified generations
        for gen in range(self.generations):
            # Score population (in real scenario, would run attacks)
            fitness_scores = self._evaluate_fitness(population, context)

            # Select best performers (tournament selection)
            parents = self._select_parents(population, fitness_scores, k=len(population)//2)

            # Create next generation via crossover and mutation
            offspring = []
            while len(offspring) < self.population_size:
                if random.random() < 0.7:  # Crossover
                    p1, p2 = random.sample(parents, 2)
                    child = self._crossover(p1, p2)
                else:  # Mutation
                    parent = random.choice(parents)
                    child = self._mutate(parent)

                offspring.append(child)

            # Elitism: preserve best 2
            elite = sorted(
                zip(population, fitness_scores),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            population = [chain for chain, _ in elite] + offspring[:self.population_size - 2]

            self.logger.debug(
                f"Generation {gen + 1}: top fitness = {max(fitness_scores):.3f}"
            )

        # Return top chains
        final_fitness = self._evaluate_fitness(population, context)
        ranked = sorted(
            zip(population, final_fitness),
            key=lambda x: x[1],
            reverse=True
        )

        result_chains = [chain for chain, _ in ranked[:count]]

        self.logger.info(
            f"Evolution complete: returning {len(result_chains)} best chains"
        )

        return result_chains

    def _initialize_population(self, seed_chains: list[ConverterChain]) -> list[ConverterChain]:
        """Initialize population with seeds or random chains."""
        population = seed_chains.copy() if seed_chains else []

        # Fill to population size with random chains
        while len(population) < self.population_size:
            chain_len = random.randint(2, 3)
            converters = random.sample(self.AVAILABLE_CONVERTERS, min(chain_len, len(self.AVAILABLE_CONVERTERS)))
            chain = ConverterChain.from_converter_names(converter_names=converters)
            population.append(chain)

        return population[:self.population_size]

    def _evaluate_fitness(
        self,
        population: list[ConverterChain],
        context: dict[str, Any]
    ) -> list[float]:
        """
        Evaluate fitness of each chain.

        In real scenario, would execute chains and measure success.
        For now, uses heuristics and historical data.

        Args:
            population: Chains to evaluate
            context: Attack context with defense patterns

        Returns:
            Fitness scores (0.0-1.0) for each chain
        """
        scores = []
        defense_patterns = set(context.get("defense_patterns", []))

        for chain in population:
            # Base score from coverage of defenses
            covered_defenses = len(set(chain.defense_patterns) & defense_patterns)
            defense_score = min(1.0, covered_defenses / max(len(defense_patterns), 1))

            # Bonus for diversity in converters
            unique_converters = len(set(chain.converter_names))
            diversity_bonus = 0.2 * (unique_converters / len(chain.converter_names))

            # Penalty for chain length (longer = more overhead)
            length_penalty = 0.1 * (len(chain.converter_names) - 2)

            # Historical success data
            historical_score = chain.avg_score / 100.0 if chain.avg_score > 0 else 0.3

            # Combine: 40% defense + 30% history + 20% diversity + 10% length
            fitness = (
                0.4 * defense_score +
                0.3 * historical_score +
                0.2 * diversity_bonus +
                0.1 * (1.0 - min(length_penalty, 1.0))
            )

            scores.append(fitness)

        return scores

    def _select_parents(
        self,
        population: list[ConverterChain],
        fitness_scores: list[float],
        k: int = 5
    ) -> list[ConverterChain]:
        """
        Tournament selection: select best k chains.

        Args:
            population: All chains
            fitness_scores: Fitness of each chain
            k: Number to select

        Returns:
            Selected parent chains
        """
        ranked = sorted(
            zip(population, fitness_scores),
            key=lambda x: x[1],
            reverse=True
        )
        return [chain for chain, _ in ranked[:k]]

    def _crossover(self, parent1: ConverterChain, parent2: ConverterChain) -> ConverterChain:
        """
        Crossover: combine two parent chains.

        Takes first N converters from parent1, rest from parent2.

        Args:
            parent1: First parent chain
            parent2: Second parent chain

        Returns:
            Child chain
        """
        min_len = min(len(parent1.converter_names), len(parent2.converter_names))
        # Handle case where chains are too small to split
        if min_len < 2:
            # Just return a copy of parent1 if can't crossover
            child_converters = parent1.converter_names[:]
        else:
            split = random.randint(1, min_len - 1)
            child_converters = (
                parent1.converter_names[:split] +
                parent2.converter_names[split:]
            )

        # Remove duplicates while preserving order
        seen = set()
        deduped = []
        for c in child_converters:
            if c not in seen:
                deduped.append(c)
                seen.add(c)

        return ConverterChain.from_converter_names(
            converter_names=deduped,
            defense_patterns=list(set(parent1.defense_patterns) | set(parent2.defense_patterns))
        )

    def _mutate(self, chain: ConverterChain) -> ConverterChain:
        """
        Mutation: randomly modify chain.

        Operations: swap (33%), replace (33%), add (17%), remove (17%)

        Args:
            chain: Chain to mutate

        Returns:
            Mutated chain
        """
        converters = list(chain.converter_names)
        mutation_type = random.choice(["swap", "replace", "add", "remove"])

        if mutation_type == "swap" and len(converters) >= 2:
            i, j = random.sample(range(len(converters)), 2)
            converters[i], converters[j] = converters[j], converters[i]

        elif mutation_type == "replace":
            idx = random.randint(0, len(converters) - 1)
            new_converter = random.choice(self.AVAILABLE_CONVERTERS)
            converters[idx] = new_converter

        elif mutation_type == "add" and len(converters) < 4:
            new_converter = random.choice(self.AVAILABLE_CONVERTERS)
            converters.insert(random.randint(0, len(converters)), new_converter)

        elif mutation_type == "remove" and len(converters) > 1:
            converters.pop(random.randint(0, len(converters) - 1))

        # Remove duplicates
        seen = set()
        deduped = []
        for c in converters:
            if c not in seen:
                deduped.append(c)
                seen.add(c)

        return ConverterChain.from_converter_names(
            converter_names=deduped,
            defense_patterns=chain.defense_patterns
        )
