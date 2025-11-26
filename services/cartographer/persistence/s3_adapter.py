"""S3 persistence adapter for Cartographer service.

Wraps the core persistence layer for recon result storage.
Handles S3 upload and campaign stage tracking.
"""
import logging
from typing import Optional

from libs.persistence import save_scan, ScanType, ArtifactUploadError
from libs.persistence.sqlite import CampaignRepository, Stage

logger = logging.getLogger(__name__)


async def persist_recon_result(
    campaign_id: str,
    scan_id: str,
    blueprint: dict,
    target_url: Optional[str] = None,
) -> None:
    """Save recon result to S3 and update campaign stage.

    Args:
        campaign_id: Campaign identifier (audit_id)
        scan_id: Unique scan identifier for S3 storage
        blueprint: Recon blueprint data to persist
        target_url: Target URL for auto-campaign creation

    Raises:
        ArtifactUploadError: If S3 upload fails
    """
    await save_scan(ScanType.RECON, scan_id, blueprint)
    logger.info(f"Saved recon to S3: scans/recon/{scan_id}.json")

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
        repo.set_stage_complete(campaign_id, Stage.RECON, scan_id)
        logger.info(f"Campaign {campaign_id}: RECON stage complete")


async def persist_with_fallback(
    campaign_id: str,
    scan_id: str,
    blueprint: dict,
    local_save_func,
    target_url: Optional[str] = None,
) -> bool:
    """Persist to S3 with local fallback on failure.

    Args:
        campaign_id: Campaign identifier
        scan_id: Unique scan identifier
        blueprint: Recon blueprint data
        local_save_func: Fallback function for local storage
        target_url: Target URL for auto-campaign creation

    Returns:
        True if S3 save succeeded, False if fell back to local
    """
    try:
        await persist_recon_result(campaign_id, scan_id, blueprint, target_url)
        return True
    except ArtifactUploadError as e:
        logger.warning(f"S3 upload failed, using local fallback: {e}")
        local_save_func(blueprint)
        return False
    except Exception as e:
        logger.error(f"Persistence error: {e}")
        local_save_func(blueprint)
        return False
