"""
Trinity: The three specialized scanning agents (SQL, Auth, Jailbreak).

This module contains factory functions for creating and running the three core agents.
"""
from .base import create_scanning_agent, run_scanning_agent
from services.swarm.core.config import AgentType


# ============================================================================
# SQL AGENT - Data Surface Attacks
# ============================================================================

async def run_sql_agent(scan_input):
    """Run SQL/Data Surface scanning agent."""
    return await run_scanning_agent(AgentType.SQL.value, scan_input)


def create_sql_agent(model_name: str = "gemini-2.5-flash"):
    """Create SQL scanning agent."""
    return create_scanning_agent(AgentType.SQL.value, model_name)


# ============================================================================
# AUTH AGENT - Authorization Surface Attacks
# ============================================================================

async def run_auth_agent(scan_input):
    """Run Authorization Surface scanning agent."""
    return await run_scanning_agent(AgentType.AUTH.value, scan_input)


def create_auth_agent(model_name: str = "gemini-2.5-flash"):
    """Create Auth scanning agent."""
    return create_scanning_agent(AgentType.AUTH.value, model_name)


# ============================================================================
# JAILBREAK AGENT - System Prompt Surface Attacks
# ============================================================================

async def run_jailbreak_agent(scan_input):
    """Run Jailbreak/System Prompt Surface scanning agent."""
    return await run_scanning_agent(AgentType.JAILBREAK.value, scan_input)


def create_jailbreak_agent(model_name: str = "gemini-2.5-flash"):
    """Create Jailbreak scanning agent."""
    return create_scanning_agent(AgentType.JAILBREAK.value, model_name)
