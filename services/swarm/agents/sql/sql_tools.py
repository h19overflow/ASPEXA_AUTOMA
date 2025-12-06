"""
SQL Agent LangChain tools.

Purpose: Define tools for SQL/data surface analysis
Dependencies: langchain.tools
Used by: sql_agent.py
"""
import json
from typing import Any, Dict

from langchain.tools import tool

from .sql_probes import get_probes


@tool
def analyze_sql_infrastructure(infrastructure: Dict[str, Any]) -> str:
    """Analyze target infrastructure for SQL attack vectors.

    Args:
        infrastructure: Dict with database, model_family, etc.

    Returns:
        Analysis summary with recommended focus areas
    """
    db = infrastructure.get("database", "unknown")
    model = infrastructure.get("model_family", "unknown")

    findings = []
    if any(sql in db.lower() for sql in ["postgres", "mysql", "sqlite", "mssql"]):
        findings.append(f"SQL database detected ({db}) - prioritize SQL injection probes")
    if any(nosql in db.lower() for nosql in ["mongo", "redis", "dynamo"]):
        findings.append(f"NoSQL database detected ({db}) - prioritize JSON injection probes")
    if any(llm in model.lower() for llm in ["gpt", "claude", "gemini"]):
        findings.append(f"Advanced LLM ({model}) - test prompt injection resistance")

    return " | ".join(findings) if findings else "Standard target profile - use default probes"


@tool
def get_sql_probe_list(approach: str = "standard") -> str:
    """Get available probes for SQL/data surface scanning.

    Args:
        approach: Scan intensity ('quick', 'standard', 'thorough')

    Returns:
        JSON list of available probes
    """
    probes = get_probes(approach)
    return json.dumps({"probes": probes, "approach": approach})


# Export all tools for agent consumption
SQL_TOOLS = [analyze_sql_infrastructure, get_sql_probe_list]
