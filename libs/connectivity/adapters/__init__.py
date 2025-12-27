"""
Protocol adapters for external frameworks.

Provides framework-specific adapters that wrap centralized clients.
"""
from .garak_generator import GarakHttpGenerator
from .pyrit_targets import HttpTargetAdapter, WebSocketTargetAdapter
from .chat_http_target import ChatHTTPTarget
from .gemini_chat_target import GeminiChatTarget
from .websocket_generator import WebSocketGenerator, WebSocketGeneratorError

__all__ = [
    "GarakHttpGenerator",
    "HttpTargetAdapter",
    "WebSocketTargetAdapter",
    "ChatHTTPTarget",
    "GeminiChatTarget",
    "WebSocketGenerator",
    "WebSocketGeneratorError",
]
