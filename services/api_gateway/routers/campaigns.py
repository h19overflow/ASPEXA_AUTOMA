"""Campaigns router - CRUD and stage management for campaigns."""
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List, Optional

from libs.persistence import CampaignRepository, CampaignStatus, Stage
from services.api_gateway.schemas import (
    CampaignCreateRequest,
    CampaignUpdateRequest,
    StageCompleteRequest,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _campaign_to_dict(campaign) -> Dict[str, Any]:
    """Convert Campaign dataclass to dict."""
    return {
        "campaign_id": campaign.campaign_id,
        "name": campaign.name,
        "target_url": campaign.target_url,
        "status": campaign.status.value,
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
        "recon_complete": campaign.recon_complete,
        "garak_complete": campaign.garak_complete,
        "exploit_complete": campaign.exploit_complete,
        "recon_scan_id": campaign.recon_scan_id,
        "garak_scan_id": campaign.garak_scan_id,
        "exploit_scan_id": campaign.exploit_scan_id,
        "description": campaign.description,
        "tags": campaign.tags,
        "progress": campaign.progress_summary,
    }


@router.post("")
def create_campaign(request: CampaignCreateRequest) -> Dict[str, Any]:
    """Create a new campaign."""
    repo = CampaignRepository()
    try:
        campaign = repo.create_campaign(
            name=request.name,
            target_url=request.target_url,
            description=request.description,
            tags=request.tags,
            campaign_id=request.campaign_id,
        )
        return _campaign_to_dict(campaign)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("")
def list_campaigns(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List all campaigns with optional status filter."""
    repo = CampaignRepository()
    status_filter = CampaignStatus(status) if status else None
    campaigns = repo.list_all(status=status_filter, limit=limit, offset=offset)
    return [_campaign_to_dict(c) for c in campaigns]


@router.get("/search")
def search_campaigns(q: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Search campaigns by name, target, or tags."""
    repo = CampaignRepository()
    campaigns = repo.search(q, limit=limit)
    return [_campaign_to_dict(c) for c in campaigns]


@router.get("/{campaign_id}")
def get_campaign(campaign_id: str) -> Dict[str, Any]:
    """Get a campaign by ID."""
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)
    if not campaign:
        raise HTTPException(404, f"Campaign {campaign_id} not found")
    return _campaign_to_dict(campaign)


@router.get("/{campaign_id}/s3-keys")
def get_campaign_s3_keys(campaign_id: str) -> Dict[str, str]:
    """Get S3 keys for all completed stages."""
    repo = CampaignRepository()
    keys = repo.get_s3_keys(campaign_id)
    if not keys:
        campaign = repo.get(campaign_id)
        if not campaign:
            raise HTTPException(404, f"Campaign {campaign_id} not found")
    return keys


@router.patch("/{campaign_id}")
def update_campaign(campaign_id: str, request: CampaignUpdateRequest) -> Dict[str, Any]:
    """Update campaign name or tags."""
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)
    if not campaign:
        raise HTTPException(404, f"Campaign {campaign_id} not found")

    if request.name:
        campaign = repo.update_name(campaign_id, request.name)
    if request.tags:
        campaign = repo.add_tags(campaign_id, request.tags)

    return _campaign_to_dict(campaign)


@router.post("/{campaign_id}/stage")
def complete_stage(campaign_id: str, request: StageCompleteRequest) -> Dict[str, Any]:
    """Mark a stage as complete and link to S3 scan."""
    repo = CampaignRepository()
    try:
        stage = Stage(request.stage)
    except ValueError:
        raise HTTPException(400, f"Invalid stage: {request.stage}. Use: recon, garak, exploit")

    try:
        campaign = repo.set_stage_complete(campaign_id, stage, request.scan_id)
        return _campaign_to_dict(campaign)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{campaign_id}/fail")
def mark_failed(campaign_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Mark campaign as failed."""
    repo = CampaignRepository()
    try:
        campaign = repo.set_failed(campaign_id, reason)
        return _campaign_to_dict(campaign)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: str) -> Dict[str, str]:
    """Delete a campaign (does not delete S3 data)."""
    repo = CampaignRepository()
    deleted = repo.delete(campaign_id)
    if not deleted:
        raise HTTPException(404, f"Campaign {campaign_id} not found")
    return {"status": "deleted", "campaign_id": campaign_id}
