"""Agent module - LangChain-based reconnaissance agent orchestration.

Purpose: Manages the reconnaissance agent graph and execution loop
Role: Orchestrates multi-turn conversations with target to extract intelligence
Dependencies: langchain.agents, langchain_google_genai
"""

from .graph import (
    build_recon_graph,
    run_reconnaissance_streaming,
    check_target_health,
)
from .state import ReconState

__all__ = [
    "build_recon_graph",
    "run_reconnaissance_streaming",
    "check_target_health",
    "ReconState",
]
