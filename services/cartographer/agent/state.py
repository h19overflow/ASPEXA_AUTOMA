"""State definition for the Cartographer agent (LangGraph)."""
from typing import Annotated, List, Dict, Any, TypedDict
import operator
from langchain_core.messages import BaseMessage


class ReconState(TypedDict):
    """State object that passes through the LangGraph."""
    audit_id: str
    target_url: str
    auth_headers: Dict[str, str]
    messages: Annotated[List[BaseMessage], operator.add]
    observations: Dict[str, List[str]]  # Replaces global _observations
    scope: Dict[str, Any]  # From IF-01
    iterations: int
