"""Scanning endpoint schemas."""
from pydantic import BaseModel, model_validator
from typing import Any, Dict, List, Optional


class ScanStartRequest(BaseModel):
    """Request to start vulnerability scanning.

    Provide EITHER campaign_id (auto-loads recon from S3)
    OR blueprint_context (manual recon data).
    """
    campaign_id: Optional[str] = None
    blueprint_context: Optional[Dict[str, Any]] = None
    agent_types: Optional[List[str]] = None
    allowed_attack_vectors: List[str] = []
    blocked_attack_vectors: List[str] = []
    aggressiveness: str = "moderate"

    @model_validator(mode="after")
    def check_input_provided(self):
        if not self.campaign_id and not self.blueprint_context:
            raise ValueError("Must provide either campaign_id or blueprint_context")
        return self
