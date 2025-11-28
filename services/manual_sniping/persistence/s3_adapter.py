"""S3 persistence for Manual Sniping sessions.

Reuses libs/persistence/s3.py for storage operations.
Dependencies: libs.persistence.s3, libs.persistence.sqlite
System role: Session persistence to S3 audit lake
"""
from typing import Optional
import logging

from libs.persistence.s3 import S3PersistenceAdapter
from libs.persistence.contracts import AuditPhase
from libs.persistence.sqlite import CampaignRepository

from ..models.session import Session

logger = logging.getLogger(__name__)


class ManualSnipingS3Adapter:
    """Persists Manual Sniping sessions to S3.

    Saves sessions to the audit lake and updates campaign records.
    """

    def __init__(self, s3_adapter: Optional[S3PersistenceAdapter] = None):
        """Initialize S3 adapter.

        Args:
            s3_adapter: Optional S3 adapter for testing
        """
        self._s3 = s3_adapter or S3PersistenceAdapter(
            bucket_name="aspexa-automa-audit-lake"
        )
        self._campaign_repo = CampaignRepository()

    async def save_session(
        self,
        session: Session,
    ) -> tuple[str, str]:
        """Persist session to S3.

        Args:
            session: Session to persist

        Returns:
            Tuple of (s3_key, scan_id)

        Raises:
            Exception: If save fails
        """
        # Generate scan_id from session
        scan_id = f"manual-snipe-{session.session_id[:8]}"

        # Build artifact data
        data = session.model_dump(mode="json")
        data["type"] = "manual_sniping_session"
        data["stats"] = session.get_stats()

        # Determine audit_id (use campaign_id if linked, else session_id)
        audit_id = session.campaign_id or session.session_id

        # Save to S3
        metadata = await self._s3.save_artifact(
            audit_id=audit_id,
            phase=AuditPhase.EXPLOIT,  # Manual sniping is exploitation
            filename=f"{scan_id}.json",
            data=data,
        )

        # Update campaign if linked
        if session.campaign_id:
            try:
                campaign = self._campaign_repo.get(session.campaign_id)
                if campaign:
                    campaign.manual_snipe_scan_id = scan_id
                    self._campaign_repo.update(campaign)
                    logger.info(
                        "Updated campaign %s with manual snipe scan %s",
                        session.campaign_id,
                        scan_id,
                    )
            except Exception as e:
                logger.warning("Could not update campaign: %s", e)

        logger.info("Saved session %s to S3: %s", session.session_id, metadata.s3_key)
        return metadata.s3_key, scan_id

    async def load_session(
        self,
        audit_id: str,
        scan_id: str,
    ) -> Optional[Session]:
        """Load a previously saved session from S3.

        Args:
            audit_id: Campaign or session ID
            scan_id: Scan identifier

        Returns:
            Session if found, None otherwise
        """
        try:
            data = await self._s3.load_artifact(
                audit_id=audit_id,
                phase=AuditPhase.EXPLOIT,
                filename=f"{scan_id}.json",
            )
            return Session.model_validate(data)
        except Exception as e:
            logger.error("Failed to load session %s: %s", scan_id, e)
            return None
