"""
Attack Phases Module.

Provides the three-phase attack flow for payload generation, conversion, and execution.

Phase 1: Payload Articulation
Phase 2: Conversion
Phase 3: Attack Execution

Usage:
    from services.snipers.core.phases import PayloadArticulation, Conversion, AttackExecution
"""

from services.snipers.core.phases.articulation import (
    ArticulationPhase as PayloadArticulation,
)
from services.snipers.core.phases.conversion import Conversion
from services.snipers.core.phases.execution import AttackExecution

__all__ = [
    "PayloadArticulation",
    "Conversion",
    "AttackExecution",
]
