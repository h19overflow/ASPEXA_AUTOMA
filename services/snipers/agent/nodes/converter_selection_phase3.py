"""
Phase 3: Converter Selection Node with Chain Discovery.

Uses multi-strategy chain discovery:
1. Query pattern database for historical chains
2. Evolutionary optimization for novel defense combinations
3. Combinatorial fallback for exhaustive search
"""

import logging
from typing import Any, Optional
from services.snipers.agent.state import ExploitAgentState
from services.snipers.chain_discovery.models import ConverterChain
from services.snipers.chain_discovery.pattern_database import PatternDatabaseAdapter
from services.snipers.chain_discovery.chain_generator import (
    HeuristicChainGenerator,
    CombinatorialChainGenerator
)
from services.snipers.chain_discovery.evolutionary_optimizer import EvolutionaryChainOptimizer

logger = logging.getLogger(__name__)


class ConverterSelectionNodePhase3:
    """
    Select converter chains using intelligent discovery strategies.

    Orchestrates pattern database queries, evolutionary optimization,
    and combinatorial generation based on defense patterns.
    """

    def __init__(self, s3_client: Any):
        """
        Initialize selector with chain discovery dependencies.

        Args:
            s3_client: S3 interface for pattern database
        """
        self.pattern_db = PatternDatabaseAdapter(s3_client)
        self.heuristic_gen = HeuristicChainGenerator()
        self.evolutionary_opt = EvolutionaryChainOptimizer()
        self.combinatorial_gen = CombinatorialChainGenerator(self.heuristic_gen)
        self.logger = logging.getLogger(__name__)

    async def select_converters(self, state: ExploitAgentState) -> dict[str, Any]:
        """
        Select converter chain using multi-strategy approach.

        Strategy priority:
        1. Query pattern DB for similar defense patterns
        2. Use evolutionary optimizer for novel combinations
        3. Fallback to combinatorial generation

        Args:
            state: Current exploit agent state

        Returns:
            State updates with selected_converters
        """
        try:
            campaign_id = state.get("campaign_id")
            extracted_patterns = state.get("pattern_analysis", {})
            defense_mechanisms = extracted_patterns.get("defense_mechanisms", []) if extracted_patterns else []

            self.logger.info(
                "Selecting converter chain (Phase 3)",
                extra={
                    "campaign_id": campaign_id,
                    "defenses": defense_mechanisms,
                    "retry_count": state.get("retry_count", 0)
                }
            )

            # Strategy 1: Query pattern database
            if defense_mechanisms:
                historical_chains = await self.pattern_db.query_chains(
                    defense_patterns=defense_mechanisms,
                    campaign_id=campaign_id,
                    limit=5
                )

                if historical_chains:
                    selected_chain = historical_chains[0]
                    self.logger.info(
                        "Selected chain from pattern database",
                        extra={
                            "campaign_id": campaign_id,
                            "chain_id": selected_chain.chain_id,
                            "avg_score": selected_chain.avg_score
                        }
                    )
                    return {"selected_converters": selected_chain}

            # Strategy 2: Evolutionary optimization
            self.logger.info("No historical chains found, using evolutionary optimizer")
            context = {
                "defense_patterns": defense_mechanisms,
                "extracted_patterns": extracted_patterns,
                "retry_count": state.get("retry_count", 0)
            }

            evolved_chains = await self.evolutionary_opt.generate_chains(
                context=context,
                count=3
            )

            if evolved_chains:
                selected_chain = evolved_chains[0]
                self.logger.info(
                    "Selected chain from evolutionary optimizer",
                    extra={"campaign_id": campaign_id, "chain_id": selected_chain.chain_id}
                )
                return {"selected_converters": selected_chain}

            # Strategy 3: Combinatorial fallback
            self.logger.info("Using combinatorial chain generation as fallback")
            combinatorial_chains = await self.combinatorial_gen.generate_chains(
                context=context,
                count=1
            )

            if not combinatorial_chains:
                # Strategy 4: Use simple heuristic chains
                heuristic_chains = await self.heuristic_gen.generate_chains(
                    context=context,
                    count=1
                )
                if heuristic_chains:
                    selected_chain = heuristic_chains[0]
                else:
                    raise Exception("All chain generation strategies failed")
            else:
                selected_chain = combinatorial_chains[0]

            self.logger.info(
                "Selected chain from combinatorial generation",
                extra={"campaign_id": campaign_id, "chain_id": selected_chain.chain_id}
            )

            return {"selected_converters": selected_chain}

        except Exception as e:
            self.logger.error(
                "Converter selection failed",
                extra={"campaign_id": state.get("campaign_id"), "error": str(e)}
            )
            raise


# Module-level async wrapper for LangGraph integration
async def select_converters_node(state: ExploitAgentState) -> dict[str, Any]:
    """
    LangGraph-compatible node wrapper.

    In actual entrypoint, inject selector instance via partial():
    from functools import partial
    graph.add_node(
        "converter_selection",
        partial(select_converters_node, selector=selector_instance)
    )
    """
    raise NotImplementedError(
        "Use functools.partial to inject ConverterSelectionNodePhase3 instance"
    )
