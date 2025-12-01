"""
Snipers Attack Routers.

Provides composable endpoints for the three-phase attack flow:
- Phase 1: Payload Articulation
- Phase 2: Conversion
- Phase 3: Attack Execution
- Full Attack: Single-shot execution of all phases
- Adaptive Attack: LangGraph loop with auto-adaptation
"""

from services.api_gateway.routers.snipers.phase1 import router as phase1_router
from services.api_gateway.routers.snipers.phase2 import router as phase2_router
from services.api_gateway.routers.snipers.phase3 import router as phase3_router
from services.api_gateway.routers.snipers.attack import router as attack_router

__all__ = [
    "phase1_router",
    "phase2_router",
    "phase3_router",
    "attack_router",
]
