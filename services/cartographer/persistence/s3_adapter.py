"""S3 persistence adapter for Cartographer service.

Wraps the core persistence layer for recon result storage.
Handles S3 upload and campaign stage tracking.
"""
import logging
from typing import Optional

from libs.persistence import save_scan, ScanType, CampaignRepository, Stage

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
