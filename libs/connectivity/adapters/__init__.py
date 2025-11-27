"""
Protocol adapters for external frameworks.

Provides framework-specific adapters that wrap centralized clients.
"""
from .garak_generator import GarakHttpGenerator

__all__ = ["GarakHttpGenerator"]
