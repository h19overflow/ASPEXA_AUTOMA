"""
Protocol adapters for external frameworks.

Provides framework-specific adapters that wrap centralized clients.
"""
from .garak_generator import GarakHttpGenerator
from .pyrit_targets import HttpTargetAdapter, WebSocketTargetAdapter

__all__ = [
    "GarakHttpGenerator",
    "HttpTargetAdapter",
    "WebSocketTargetAdapter",
]
