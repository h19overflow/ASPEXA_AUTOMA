"""
Purpose: Base agent functionality for scanning agents
Role: Deterministic probe pool selection from DEFAULT_PROBES table
Dependencies: services.swarm.core
"""

import logging
from typing import List

from services.swarm.core.config import AgentType, DEFAULT_PROBES, ScanApproach

logger = logging.getLogger(__name__)


def get_agent_probe_pool(agent_type: str, approach: str = "standard") -> List[str]:
    """Get the probe pool for an agent type.

    Args:
        agent_type: One of agent_sql, agent_auth, agent_jailbreak
        approach: Scan approach (quick, standard, thorough)

    Returns:
        List of probe names available to this agent
    """
    agent_enum = AgentType(agent_type) if agent_type in [e.value for e in AgentType] else AgentType.SQL
    approach_enum = ScanApproach(approach) if approach in [e.value for e in ScanApproach] else ScanApproach.STANDARD
    probes_by_approach = DEFAULT_PROBES.get(agent_enum, {})
    probes = probes_by_approach.get(approach_enum, [])
    return list(probes)
