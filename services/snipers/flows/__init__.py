"""
Snipers attack flows - streaming execution for each attack mode.

Each flow is an async generator yielding AttackEvents for SSE streaming.
"""

from services.snipers.flows.manual import run_manual_attack
from services.snipers.flows.sweep import run_sweep_attack
from services.snipers.flows.guided import run_guided_attack

__all__ = [
    "run_manual_attack",
    "run_sweep_attack",
    "run_guided_attack",
]
