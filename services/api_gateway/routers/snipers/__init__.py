"""
Snipers Attack Routers.

Endpoints:
- /phase2/converters: List available payload converters
- /attack/full/stream: One-shot full attack (all 3 phases, SSE)
- /attack/adaptive/*: Adaptive attack with pause/resume and checkpoints
"""

from services.api_gateway.routers.snipers.phase2 import router as phase2_router
from services.api_gateway.routers.snipers.one_shot import router as one_shot_router
from services.api_gateway.routers.snipers.adaptive import router as adaptive_router

__all__ = [
    "phase2_router",
    "one_shot_router",
    "adaptive_router",
]
