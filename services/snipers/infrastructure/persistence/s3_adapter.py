"""S3 persistence adapter for Snipers exploitation service.

Handles loading recon + garak intelligence and saving exploit results.
Also handles checkpoint persistence for adaptive attack pause/resume.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from libs.persistence import (
    save_scan,
    load_scan,
    list_scans,
    scan_exists,
    ScanType,
    ArtifactUploadError,
    ArtifactNotFoundError,
    S3PersistenceAdapter,
    CheckpointStatus,
    CheckpointConfig,
    CheckpointIteration,
    CheckpointResumeState,
    CheckpointResult,
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
        Also includes fields for ExploitResultViewer compatibility:
        - status: VULNERABLE/SAFE
        - breach_detected: bool
        - kill_chain: conversation steps
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

    # Determine breach status
    breach_detected = successful > 0
    status = "VULNERABLE" if breach_detected else "SAFE"

    # Build kill chain from attack results (payload -> response pairs)
    kill_chain = []
    for result in attack_results:
        if isinstance(result, dict):
            # Add attacker payload
            payload = result.get("payload", "")
            if payload:
                kill_chain.append({
                    "role": "attacker",
                    "content": payload,
                })
            # Add target response
            response = result.get("response", "")
            if response:
                kill_chain.append({
                    "role": "target",
                    "content": response,
                })

    # Get converters used
    converters_used = []
    if state.get("converter_selection"):
        converters_used = state.get("converter_selection", {}).get("selected_converters", [])

    return {
        # Core identification
        "audit_id": audit_id,
        "target_url": target_url,
        "timestamp": datetime.utcnow().isoformat() + "Z",

        # ExploitResultViewer compatibility fields
        "status": status,
        "breach_detected": breach_detected,
        "kill_chain": kill_chain,
        "artifact_type": "kill_chain" if kill_chain else "metrics",

        # Detailed probe results
        "probes_attacked": [{
            "probe_name": state.get("probe_name", "unknown"),
            "pattern_analysis": state.get("pattern_analysis"),
            "converters_used": converters_used,
            "attempts": attack_results,
            "success_count": successful,
            "fail_count": failed,
        }],

        # Summary statistics
        "total_attacks": len(attack_results),
        "successful_attacks": successful,
        "failed_attacks": failed,
        "recon_intelligence_used": state.get("recon_intelligence") is not None,
        "execution_time_seconds": round(execution_time, 2),

        # Adaptive attack fields (if present)
        "iteration_count": state.get("iteration_count"),
        "best_score": state.get("best_score"),
        "best_iteration": state.get("best_iteration"),
        "adaptation_reasoning": state.get("adaptation_reasoning"),
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


# ============================================================================
# Checkpoint Persistence (Adaptive Attack Pause/Resume)
# ============================================================================


def _build_checkpoint_id(campaign_id: str, scan_id: str) -> str:
    """Build checkpoint ID from campaign and scan IDs.

    Format: {campaign_id}/{scan_id} for hierarchical S3 storage.
    """
    return f"{campaign_id}/{scan_id}"


async def create_checkpoint(
    campaign_id: str,
    scan_id: str,
    target_url: str,
    config: CheckpointConfig,
) -> CheckpointResult:
    """Create initial checkpoint when adaptive attack starts.

    Args:
        campaign_id: Campaign identifier
        scan_id: Unique scan/attack identifier
        target_url: Target URL being attacked
        config: Attack configuration parameters

    Returns:
        Created CheckpointResult

    Raises:
        ArtifactUploadError: If S3 upload fails
    """
    now = datetime.now(timezone.utc).isoformat()
    checkpoint = CheckpointResult(
        scan_id=scan_id,
        campaign_id=campaign_id,
        target_url=target_url,
        status=CheckpointStatus.RUNNING,
        created_at=now,
        updated_at=now,
        config=config,
        current_iteration=0,
        best_score=0.0,
        best_iteration=0,
        is_successful=False,
        iteration_history=[],
        resume_state=CheckpointResumeState(),
    )

    checkpoint_id = _build_checkpoint_id(campaign_id, scan_id)
    await save_scan(ScanType.CHECKPOINT, checkpoint_id, checkpoint.model_dump())
    logger.info(f"Created checkpoint: scans/checkpoint/{checkpoint_id}.json")

    return checkpoint


async def update_checkpoint(
    campaign_id: str,
    scan_id: str,
    iteration: CheckpointIteration,
    resume_state: CheckpointResumeState,
    best_score: float,
    best_iteration: int,
    is_successful: bool = False,
    status: CheckpointStatus = CheckpointStatus.RUNNING,
) -> CheckpointResult:
    """Update checkpoint after an iteration completes.

    Args:
        campaign_id: Campaign identifier
        scan_id: Scan identifier
        iteration: Completed iteration data
        resume_state: Updated resume state
        best_score: Best score so far
        best_iteration: Iteration with best score
        is_successful: Whether attack succeeded
        status: Checkpoint status

    Returns:
        Updated CheckpointResult

    Raises:
        ArtifactNotFoundError: If checkpoint doesn't exist
        ArtifactUploadError: If S3 upload fails
    """
    checkpoint_id = _build_checkpoint_id(campaign_id, scan_id)

    # Load existing checkpoint
    existing = await load_scan(ScanType.CHECKPOINT, checkpoint_id, validate=False)
    checkpoint = CheckpointResult.model_validate(existing)

    # Update fields
    checkpoint.updated_at = datetime.now(timezone.utc).isoformat()
    checkpoint.current_iteration = iteration.iteration
    checkpoint.best_score = best_score
    checkpoint.best_iteration = best_iteration
    checkpoint.is_successful = is_successful
    checkpoint.status = status
    checkpoint.iteration_history.append(iteration)
    checkpoint.resume_state = resume_state

    # Save updated checkpoint
    await save_scan(ScanType.CHECKPOINT, checkpoint_id, checkpoint.model_dump())
    logger.info(f"Updated checkpoint: iteration {iteration.iteration}, score {iteration.score:.2f}")

    return checkpoint


async def set_checkpoint_status(
    campaign_id: str,
    scan_id: str,
    status: CheckpointStatus,
) -> CheckpointResult:
    """Update only the status of a checkpoint.

    Args:
        campaign_id: Campaign identifier
        scan_id: Scan identifier
        status: New status

    Returns:
        Updated CheckpointResult
    """
    checkpoint_id = _build_checkpoint_id(campaign_id, scan_id)

    existing = await load_scan(ScanType.CHECKPOINT, checkpoint_id, validate=False)
    checkpoint = CheckpointResult.model_validate(existing)

    checkpoint.status = status
    checkpoint.updated_at = datetime.now(timezone.utc).isoformat()

    await save_scan(ScanType.CHECKPOINT, checkpoint_id, checkpoint.model_dump())
    logger.info(f"Checkpoint {scan_id} status -> {status.value}")

    return checkpoint


async def load_checkpoint(
    campaign_id: str,
    scan_id: str,
) -> Optional[CheckpointResult]:
    """Load checkpoint from S3.

    Args:
        campaign_id: Campaign identifier
        scan_id: Scan identifier

    Returns:
        CheckpointResult if found, None otherwise
    """
    checkpoint_id = _build_checkpoint_id(campaign_id, scan_id)
    try:
        data = await load_scan(ScanType.CHECKPOINT, checkpoint_id, validate=False)
        return CheckpointResult.model_validate(data)
    except ArtifactNotFoundError:
        return None


async def get_latest_checkpoint(campaign_id: str) -> Optional[CheckpointResult]:
    """Get the most recent checkpoint for a campaign.

    Args:
        campaign_id: Campaign identifier

    Returns:
        Most recent CheckpointResult or None
    """
    try:
        # List all checkpoints for this campaign
        all_checkpoints = await list_scans(ScanType.CHECKPOINT)

        # Filter by campaign_id (checkpoint IDs are formatted as campaign_id/scan_id)
        campaign_checkpoints = [
            cp for cp in all_checkpoints
            if cp.scan_id.startswith(f"{campaign_id}/")
        ]

        if not campaign_checkpoints:
            return None

        # Sort by timestamp (newest first) and get the first one
        campaign_checkpoints.sort(key=lambda x: x.timestamp, reverse=True)
        latest = campaign_checkpoints[0]

        # Load the full checkpoint
        return await load_checkpoint(campaign_id, latest.scan_id.split("/")[-1])

    except Exception as e:
        logger.warning(f"Failed to get latest checkpoint for {campaign_id}: {e}")
        return None


async def list_campaign_checkpoints(campaign_id: str) -> List[Dict[str, Any]]:
    """List all checkpoints for a campaign.

    Args:
        campaign_id: Campaign identifier

    Returns:
        List of checkpoint summaries
    """
    try:
        all_checkpoints = await list_scans(ScanType.CHECKPOINT)

        summaries = []
        for cp in all_checkpoints:
            if cp.scan_id.startswith(f"{campaign_id}/"):
                scan_id = cp.scan_id.split("/")[-1]
                # Load full checkpoint for details
                checkpoint = await load_checkpoint(campaign_id, scan_id)
                if checkpoint:
                    summaries.append({
                        "scan_id": scan_id,
                        "status": checkpoint.status.value,
                        "current_iteration": checkpoint.current_iteration,
                        "best_score": checkpoint.best_score,
                        "is_successful": checkpoint.is_successful,
                        "created_at": checkpoint.created_at,
                        "updated_at": checkpoint.updated_at,
                    })

        return sorted(summaries, key=lambda x: x["created_at"], reverse=True)

    except Exception as e:
        logger.warning(f"Failed to list checkpoints for {campaign_id}: {e}")
        return []


async def checkpoint_exists(campaign_id: str, scan_id: str) -> bool:
    """Check if a checkpoint exists.

    Args:
        campaign_id: Campaign identifier
        scan_id: Scan identifier

    Returns:
        True if checkpoint exists
    """
    checkpoint_id = _build_checkpoint_id(campaign_id, scan_id)
    return await scan_exists(ScanType.CHECKPOINT, checkpoint_id)


if __name__ == "__main__":
    import asyncio
    import json
    result = asyncio.run(load_campaign_intel("fresh1"))
    with open("output.json", "w") as f:
        json.dump(result, f)