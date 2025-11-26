"""Reconnaissance endpoint schemas."""
from pydantic import BaseModel
from typing import Dict, List, Optional


class ReconStartRequest(BaseModel):
    """Request to start reconnaissance."""
    audit_id: str
    target_url: str
    auth_headers: Dict[str, str] = {}
    depth: str = "standard"
    max_turns: int = 10
    forbidden_keywords: List[str] = []
    special_instructions: Optional[str] = None
