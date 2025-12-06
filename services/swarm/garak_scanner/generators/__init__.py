"""
Generators package - target communication.

Purpose: Send prompts to targets via HTTP or WebSocket
Dependencies: garak.generators, libs.connectivity
"""
from libs.connectivity.adapters import GarakHttpGenerator as HTTPGenerator

from .rate_limiter import RateLimiter
from .websocket_generator import WebSocketGenerator, WebSocketGeneratorError

__all__ = [
    "HTTPGenerator",
    "WebSocketGenerator",
    "WebSocketGeneratorError",
    "RateLimiter",
]
