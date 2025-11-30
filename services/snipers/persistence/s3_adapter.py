"""S3 persistence adapter for Snipers exploitation service.

Handles loading recon + garak intelligence and saving exploit results.
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from libs.persistence import (
    save_scan,
    load_scan,
    ScanType,
    ArtifactUploadError,
    ArtifactNotFoundError,
    S3PersistenceAdapter,
)
from libs.persistence.sqlite import CampaignRepository, Stage

logger = logging.getLogger(__name__)


class S3InterfaceAdapter:
    """
    Adapter to make S3PersistenceAdapter compatible with PatternDatabaseAdapter.

    PatternDatabaseAdapter expects: get_object(key), put_object(key, data), list_objects(prefix)
    S3PersistenceAdapter has different methods, so we adapt them.
    """

    def __init__(self, s3_adapter: S3PersistenceAdapter):
        """Initialize with S3PersistenceAdapter."""
        self._adapter = s3_adapter

    async def get_object(self, key: str) -> str:
        """Get object content as string."""
        import asyncio

        response = await asyncio.to_thread(
            self._adapter._client.get_object,
            Bucket=self._adapter._bucket,
            Key=key,
        )
        return response["Body"].read().decode("utf-8")

    async def put_object(self, key: str, data: str) -> None:
        """Put string content to S3."""
        import asyncio

        await asyncio.to_thread(
            self._adapter._client.put_object,
            Bucket=self._adapter._bucket,
            Key=key,
            Body=data.encode("utf-8"),
            ContentType="application/json",
        )

    async def list_objects(self, prefix: str) -> list[str]:
        """List objects with prefix."""
        import asyncio

        response = await asyncio.to_thread(
            self._adapter._client.list_objects_v2,
            Bucket=self._adapter._bucket,
            Prefix=prefix,
        )
        return [obj["Key"] for obj in response.get("Contents", [])]


async def load_campaign_intel(campaign_id: str) -> Dict[str, Any]:
    """Load recon + garak intelligence from S3 for a campaign.

    Args:
        campaign_id: Campaign identifier

    Returns:
        Dict with 'recon' and 'garak' keys containing intelligence data

    Raises:
        ValueError: If campaign not found or has no intelligence
    """
    repo = CampaignRepository()
    campaign = repo.get(campaign_id)

    if not campaign:
        raise ValueError(f"Campaign {campaign_id} not found")

    intel: Dict[str, Any] = {}

    # Load recon data
    if campaign.recon_scan_id:
        try:
            intel["recon"] = await load_scan(
                ScanType.RECON,
                campaign.recon_scan_id,
                validate=False
            )
            logger.info(f"Loaded recon: {campaign.recon_scan_id}")
        except ArtifactNotFoundError:
            logger.warning(f"Recon {campaign.recon_scan_id} not found in S3")

    # Load garak data
    if campaign.garak_scan_id:
        try:
            intel["garak"] = await load_scan(
                ScanType.GARAK,
                campaign.garak_scan_id,
                validate=False
            )
            logger.info(f"Loaded garak: {campaign.garak_scan_id}")
        except ArtifactNotFoundError:
            logger.warning(f"Garak {campaign.garak_scan_id} not found in S3")

    if not intel:
        raise ValueError(f"No intelligence data found for campaign {campaign_id}")

    return intel


async def persist_exploit_result(
    campaign_id: str,
    scan_id: str,
    exploit_result: dict,
    target_url: Optional[str] = None,
) -> None:
    """Save exploit result to S3 and mark campaign complete.

    Args:
        campaign_id: Campaign identifier
        scan_id: Unique scan identifier for S3 storage
        exploit_result: Exploit result data to persist
        target_url: Target URL for auto-campaign creation

    Raises:
        ArtifactUploadError: If S3 upload fails
    """
    await save_scan(ScanType.EXPLOIT, scan_id, exploit_result)
    logger.info(f"Saved exploit to S3: scans/exploit/{scan_id}.json")

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
        repo.set_stage_complete(campaign_id, Stage.EXPLOIT, scan_id)
        logger.info(f"Campaign {campaign_id}: EXPLOIT stage complete (campaign should be COMPLETE)")


def format_exploit_result(
    state: dict,
    audit_id: str,
    target_url: str,
    execution_time: float,
) -> dict:
    """Format ExploitAgentState into ExploitResult schema.

    Args:
        state: Final workflow state from ExploitAgent
        audit_id: Campaign/audit identifier
        target_url: Target URL
        execution_time: Total execution time in seconds

    Returns:
        Dict matching libs/persistence/scan_models.py::ExploitResult
    """
    attack_results = state.get("attack_results", [])

    # Count successes and failures
    successful = 0
    failed = 0
    for result in attack_results:
        if isinstance(result, dict):
            if result.get("success"):
                successful += 1
            else:
                failed += 1

    return {
        "audit_id": audit_id,
        "target_url": target_url,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "probes_attacked": [{
            "probe_name": state.get("probe_name", "unknown"),
            "pattern_analysis": state.get("pattern_analysis"),
            "converters_used": (
                state.get("converter_selection", {}).get("selected_converters", [])
                if state.get("converter_selection") else []
            ),
            "attempts": attack_results,
            "success_count": successful,
            "fail_count": failed,
        }],
        "total_attacks": len(attack_results),
        "successful_attacks": successful,
        "failed_attacks": failed,
        "recon_intelligence_used": state.get("recon_intelligence") is not None,
        "execution_time_seconds": round(execution_time, 2),
    }


async def persist_with_fallback(
    campaign_id: str,
    scan_id: str,
    exploit_result: dict,
    local_save_func,
    target_url: Optional[str] = None,
) -> bool:
    """Persist to S3 with local fallback on failure.

    Args:
        campaign_id: Campaign identifier
        scan_id: Unique scan identifier
        exploit_result: Exploit result data
        local_save_func: Fallback function for local storage
        target_url: Target URL for auto-campaign creation

    Returns:
        True if S3 save succeeded, False if fell back to local
    """
    try:
        await persist_exploit_result(campaign_id, scan_id, exploit_result, target_url)
        return True
    except ArtifactUploadError as e:
        logger.warning(f"S3 upload failed, using local fallback: {e}")
        local_save_func(exploit_result)
        return False
    except Exception as e:
        logger.error(f"Persistence error: {e}")
        local_save_func(exploit_result)
        return False
if __name__ == "__main__":
    import asyncio
    import json
    result = asyncio.run(load_campaign_intel("fresh1"))
    with open("output.json", "w") as f:
        json.dump(result, f)