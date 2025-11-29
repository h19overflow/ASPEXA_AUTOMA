"""
Chain discovery system for converter optimization.

Discovers and learns effective converter chains through:
- Pattern database (historical chains)
- Evolutionary optimization (GA-based mutation)
- LLM-guided selection (reasoning over defense patterns)
"""

from services.snipers.chain_discovery.models import (
    ConverterChain,
    ChainMetadata,
)

__all__ = ["ConverterChain", "ChainMetadata"]
