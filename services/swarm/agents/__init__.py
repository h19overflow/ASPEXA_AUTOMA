"""
Agent system for security scanning.

Purpose: Deterministic probe pool selection for Swarm scans
Role: Select probes from DEFAULT_PROBES table based on agent type and approach
Dependencies: services.swarm.core
"""

from .base import get_agent_probe_pool

__all__ = [
    "get_agent_probe_pool",
]
