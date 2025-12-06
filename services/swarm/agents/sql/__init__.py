"""
SQL Agent module for data surface vulnerability scanning.

Purpose: Export SQL agent components
Dependencies: sql_agent.py, sql_prompt.py, sql_probes.py, sql_tools.py
"""
from .sql_agent import SQLAgent
from .sql_probes import SQL_PROBES, SQL_PROBES_EXTENDED, get_probes
from .sql_prompt import SQL_SYSTEM_PROMPT
from .sql_tools import SQL_TOOLS, analyze_sql_infrastructure, get_sql_probe_list

__all__ = [
    "SQLAgent",
    "SQL_SYSTEM_PROMPT",
    "SQL_PROBES",
    "SQL_PROBES_EXTENDED",
    "get_probes",
    "SQL_TOOLS",
    "analyze_sql_infrastructure",
    "get_sql_probe_list",
]
