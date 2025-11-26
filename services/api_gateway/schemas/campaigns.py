"""Campaign management schemas."""
from pydantic import BaseModel
from typing import List, Optional


class CampaignCreateRequest(BaseModel):
    """Request to create a new campaign."""
    name: str
    target_url: str
    description: Optional[str] = None
    tags: List[str] = []
    campaign_id: Optional[str] = None


class CampaignUpdateRequest(BaseModel):
    """Request to update campaign metadata."""
    name: Optional[str] = None
    tags: Optional[List[str]] = None


class StageCompleteRequest(BaseModel):
    """Request to mark a stage complete."""
    stage: str
    scan_id: str
