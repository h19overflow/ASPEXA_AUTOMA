"""Execution layer for Manual Sniping service.

Provides attack orchestration and execution.
"""
from .executor import AttackExecutor

__all__ = ["AttackExecutor"]
