"""
Adaptive Attack Module.

LangGraph-based adaptive attack loop that learns from failures
and automatically adjusts attack parameters.

Components:
- state: AdaptiveAttackState TypedDict and helpers
- nodes/: Individual node implementations (articulate, convert, execute, evaluate, adapt)
- graph: StateGraph definition and runner

Usage:
    from services.snipers.adaptive_attack import run_adaptive_attack

    result = await run_adaptive_attack(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        max_iterations=5,
    )

    print(f"Success: {result['is_successful']}")
    print(f"Iterations: {result['iteration'] + 1}")
"""

from services.snipers.adaptive_attack.state import (
    AdaptiveAttackState,
    create_initial_state,
    FRAMING_TYPES,
    CONVERTER_CHAINS,
    ALL_SCORERS,
    ScorerType,
)
from services.snipers.adaptive_attack.graph import (
    build_adaptive_attack_graph,
    get_adaptive_attack_graph,
    run_adaptive_attack,
    run_adaptive_attack_streaming,
)

__all__ = [
    # State
    "AdaptiveAttackState",
    "create_initial_state",
    "FRAMING_TYPES",
    "CONVERTER_CHAINS",
    "ALL_SCORERS",
    "ScorerType",
    # Graph
    "build_adaptive_attack_graph",
    "get_adaptive_attack_graph",
    "run_adaptive_attack",
    "run_adaptive_attack_streaming",
]
