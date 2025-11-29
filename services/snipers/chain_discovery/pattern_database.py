"""
Pattern database for storing and querying successful converter chains.

Persists to S3 at: s3://{bucket}/patterns/{campaign_id}/chains.json
Enables learning from previous attack campaigns.
"""

import json
import logging
from typing import Any, Optional
from services.snipers.chain_discovery.models import ConverterChain, ChainMetadata

logger = logging.getLogger(__name__)


class PatternDatabaseAdapter:
    """
    S3-backed storage for converter chains.

    Schema:
    - One JSON file per campaign: chains.json
    - Structure: {"chains": [ConverterChain.to_dict(), ...]}
    """

    def __init__(self, s3_client: Any):
        """
        Initialize adapter.

        Args:
            s3_client: S3 interface for persistence (S3Interface protocol)
        """
        self.s3 = s3_client
        self.logger = logging.getLogger(__name__)

    async def save_chain(
        self,
        chain: ConverterChain,
        metadata: ChainMetadata
    ) -> None:
        """
        Save or update converter chain.

        If chain exists (by chain_id), update metadata.
        Otherwise, create new entry.

        Args:
            chain: Converter chain to save
            metadata: Associated metadata

        Raises:
            Exception: If S3 operation fails
        """
        campaign_id = metadata.campaign_id
        key = f"patterns/{campaign_id}/chains.json"

        try:
            # Load existing chains
            try:
                data = await self.s3.get_object(key)
                chains_data = json.loads(data)
            except Exception:
                chains_data = {"chains": []}

            # Update or append
            existing_idx = next(
                (i for i, c in enumerate(chains_data["chains"])
                 if c["chain_id"] == chain.chain_id),
                None
            )

            chain_dict = chain.to_dict()
            chain_dict["metadata"] = metadata.model_dump()

            if existing_idx is not None:
                chains_data["chains"][existing_idx] = chain_dict
            else:
                chains_data["chains"].append(chain_dict)

            # Save back
            await self.s3.put_object(key, json.dumps(chains_data, indent=2))

            self.logger.info(
                f"Saved chain {chain.chain_id} to pattern database",
                extra={"campaign_id": campaign_id}
            )
        except Exception as e:
            self.logger.error(
                f"Failed to save chain: {e}",
                extra={"campaign_id": campaign_id, "chain_id": chain.chain_id}
            )
            raise

    async def query_chains(
        self,
        defense_patterns: list[str],
        campaign_id: Optional[str] = None,
        limit: int = 10
    ) -> list[ConverterChain]:
        """
        Query chains by defense patterns.

        Returns chains that successfully bypassed similar defenses.

        Args:
            defense_patterns: Defense mechanisms to match
            campaign_id: Optional campaign filter
            limit: Max results

        Returns:
            Matching chains, sorted by avg_score descending
        """
        try:
            # Load all chains (or from specific campaign)
            if campaign_id:
                keys = [f"patterns/{campaign_id}/chains.json"]
            else:
                keys = await self._list_all_chain_files()

            all_chains = []
            for key in keys:
                try:
                    data = await self.s3.get_object(key)
                    chains_data = json.loads(data)
                    all_chains.extend([
                        ConverterChain.from_dict(c)
                        for c in chains_data.get("chains", [])
                    ])
                except Exception as e:
                    self.logger.debug(f"Could not load chains from {key}: {e}")
                    continue

            # Filter by defense patterns (intersection)
            def pattern_match(chain: ConverterChain) -> int:
                """Count matching defense patterns."""
                return len(set(chain.defense_patterns) & set(defense_patterns))

            matched = [c for c in all_chains if pattern_match(c) > 0]

            # Sort by match count, then avg_score
            matched.sort(
                key=lambda c: (pattern_match(c), c.avg_score),
                reverse=True
            )

            self.logger.info(
                f"Found {len(matched)} chains for patterns {defense_patterns}",
                extra={"query_limit": limit, "total_patterns": len(all_chains)}
            )

            return matched[:limit]
        except Exception as e:
            self.logger.error(f"Chain query failed: {e}")
            return []

    async def get_all_chains(self) -> list[ConverterChain]:
        """
        Retrieve all chains from all campaigns.

        Returns:
            List of all stored chains
        """
        try:
            keys = await self._list_all_chain_files()
            all_chains = []

            for key in keys:
                try:
                    data = await self.s3.get_object(key)
                    chains_data = json.loads(data)
                    all_chains.extend([
                        ConverterChain.from_dict(c)
                        for c in chains_data.get("chains", [])
                    ])
                except Exception as e:
                    self.logger.debug(f"Could not load chains from {key}: {e}")
                    continue

            self.logger.info(f"Retrieved {len(all_chains)} total chains")
            return all_chains
        except Exception as e:
            self.logger.error(f"Failed to retrieve all chains: {e}")
            return []

    async def _list_all_chain_files(self) -> list[str]:
        """
        List all chain JSON files in S3.

        Returns:
            List of S3 keys for chain files
        """
        try:
            # Assumes S3Interface has list_objects method
            objects = await self.s3.list_objects(prefix="patterns/")
            return [obj for obj in objects if obj.endswith("chains.json")]
        except Exception as e:
            self.logger.error(f"Failed to list chain files: {e}")
            return []

    async def delete_chain(self, chain_id: str, campaign_id: str) -> None:
        """
        Delete a specific chain from database.

        Args:
            chain_id: ID of chain to delete
            campaign_id: Campaign containing the chain

        Raises:
            Exception: If deletion fails
        """
        key = f"patterns/{campaign_id}/chains.json"

        try:
            data = await self.s3.get_object(key)
            chains_data = json.loads(data)

            chains_data["chains"] = [
                c for c in chains_data["chains"]
                if c["chain_id"] != chain_id
            ]

            await self.s3.put_object(key, json.dumps(chains_data, indent=2))

            self.logger.info(
                f"Deleted chain {chain_id}",
                extra={"campaign_id": campaign_id}
            )
        except Exception as e:
            self.logger.error(f"Failed to delete chain: {e}")
            raise
