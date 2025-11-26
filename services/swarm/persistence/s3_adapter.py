"""S3 persistence adapter for Swarm scanning service.

Handles loading recon data and saving garak results.
"""
import logging
from typing import Any, Dict, Optional

from libs.persistence import (
    save_scan,
    load_scan,
    ScanType,
    ArtifactUploadError,
    ArtifactNotFoundError,
)
from libs.persistence.sqlite import CampaignRepository, Stage

logger = logging.getLogger(__name__)


async def load_recon_for_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    """Load recon result from S3 for a campaign.

    Args:
        campaign_id: Campaign identifier

    Returns:
        Recon intelligence dict, or None if not found

    Raises:
        ValueError: If campaign exists but has no recon data
    """
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    if not campaign:
        logger.warning(f"Campaign {campaign_id} not found in SQLite")
        return None

    if not campaign.recon_scan_id:
        logger.warning(f"Campaign {campaign_id} has no recon_scan_id")
        return None

    try:
        recon_data = await load_scan(
            ScanType.RECON,
            campaign.recon_scan_id,
            validate=False
        )
        logger.info(f"Loaded recon from S3: {campaign.recon_scan_id}")
        return recon_data
    except ArtifactNotFoundError:
        logger.error(f"Recon scan {campaign.recon_scan_id} not found in S3")
        return None


async def persist_garak_result(
    campaign_id: str,
    scan_id: str,
    garak_report: dict,
    target_url: Optional[str] = None,
) -> None:
    """Save garak result to S3 and update campaign stage.

    Args:
        campaign_id: Campaign identifier
        scan_id: Unique scan identifier for S3 storage
        garak_report: Complete garak report from generate_comprehensive_report()
        target_url: Target URL for auto-campaign creation

    Raises:
        ArtifactUploadError: If S3 upload fails
    """
    await save_scan(ScanType.GARAK, scan_id, garak_report)
    logger.info(f"Saved garak to S3: scans/garak/{scan_id}.json")

    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    if not campaign and target_url:
        campaign = repo.create_campaign(
            name=f"Auto: {campaign_id}",
            target_url=target_url,
            campaign_id=campaign_id,
        )
        logger.info(f"Auto-created campaign: {campaign_id}")

    if campaign:
        repo.set_stage_complete(campaign_id, Stage.GARAK, scan_id)
        logger.info(f"Campaign {campaign_id}: GARAK stage complete")


async def persist_with_fallback(
    campaign_id: str,
    scan_id: str,
    garak_report: dict,
    local_save_func,
    target_url: Optional[str] = None,
) -> bool:
    """Persist to S3 with local fallback on failure.

    Args:
        campaign_id: Campaign identifier
        scan_id: Unique scan identifier
        garak_report: Garak report data
        local_save_func: Fallback function for local storage
        target_url: Target URL for auto-campaign creation

    Returns:
        True if S3 save succeeded, False if fell back to local
    """
    try:
        await persist_garak_result(campaign_id, scan_id, garak_report, target_url)
        return True
    except ArtifactUploadError as e:
        logger.warning(f"S3 upload failed, using local fallback: {e}")
        local_save_func(garak_report)
        return False
    except Exception as e:
        logger.error(f"Persistence error: {e}")
        local_save_func(garak_report)
        return False
