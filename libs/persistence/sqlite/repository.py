"""Campaign repository for SQLite operations.

Provides CRUD operations and stage management for campaigns.
Maps campaign stages to S3 scan results.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .connection import get_connection, init_database, DEFAULT_DB_PATH
from .models import Campaign, CampaignStatus, Stage


class CampaignRepository:
    """Repository for campaign CRUD and stage management.

    Handles the mapping between campaigns and their S3 scan results.
    Stage flags are set when scans complete successfully.

    Args:
        db_path: Path to SQLite database
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or DEFAULT_DB_PATH
        init_database(self._db_path)

    # --- Create Operations ---

    def create_campaign(
        self,
        name: str,
        target_url: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        campaign_id: Optional[str] = None,
    ) -> Campaign:
        """Create a new campaign.

        Args:
            name: Human-readable campaign name
            target_url: Target URL being audited
            description: Optional description
            tags: Optional tags for searching
            campaign_id: Optional ID (auto-generated if not provided)

        Returns:
            Created campaign

        Raises:
            ValueError: If campaign_id already exists
        """
        campaign = Campaign(
            campaign_id=campaign_id or str(uuid.uuid4()),
            name=name,
            target_url=target_url,
            description=description,
            tags=tags or [],
        )
        return self._insert(campaign)

    def _insert(self, campaign: Campaign) -> Campaign:
        """Insert campaign into database."""
        now = datetime.utcnow().isoformat()
        campaign.created_at = now
        campaign.updated_at = now

        with get_connection(self._db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO campaigns (
                        campaign_id, name, target_url, status,
                        created_at, updated_at,
                        recon_complete, garak_complete, exploit_complete,
                        recon_scan_id, garak_scan_id, exploit_scan_id,
                        description, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        campaign.campaign_id,
                        campaign.name,
                        campaign.target_url,
                        campaign.status.value,
                        campaign.created_at,
                        campaign.updated_at,
                        int(campaign.recon_complete),
                        int(campaign.garak_complete),
                        int(campaign.exploit_complete),
                        campaign.recon_scan_id,
                        campaign.garak_scan_id,
                        campaign.exploit_scan_id,
                        campaign.description,
                        json.dumps(campaign.tags),
                    ),
                )
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    raise ValueError(
                        f"Campaign {campaign.campaign_id} already exists"
                    ) from e
                raise

        return campaign

    # --- Read Operations ---

    def get(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID."""
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM campaigns WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()

        return self._row_to_campaign(row) if row else None

    def get_by_target(self, target_url: str) -> List[Campaign]:
        """Get all campaigns for a target URL."""
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM campaigns WHERE target_url = ? ORDER BY created_at DESC",
                (target_url,),
            ).fetchall()

        return [self._row_to_campaign(row) for row in rows]

    def list_all(
        self,
        status: Optional[CampaignStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Campaign]:
        """List campaigns with optional status filter."""
        query = "SELECT * FROM campaigns"
        params: List = []

        if status:
            query += " WHERE status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with get_connection(self._db_path) as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_campaign(row) for row in rows]

    def search(self, query: str, limit: int = 50) -> List[Campaign]:
        """Search campaigns by name, target, or tags."""
        pattern = f"%{query}%"
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM campaigns
                WHERE name LIKE ? OR target_url LIKE ?
                   OR tags LIKE ? OR campaign_id LIKE ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (pattern, pattern, pattern, pattern, limit),
            ).fetchall()

        return [self._row_to_campaign(row) for row in rows]

    # --- Stage Management ---

    def set_stage_complete(
        self,
        campaign_id: str,
        stage: Stage,
        scan_id: str,
    ) -> Campaign:
        """Mark a stage as complete and link to S3 scan.

        This is the key operation that maps campaign stages to S3 data.

        Args:
            campaign_id: Campaign to update
            stage: Stage that completed
            scan_id: S3 scan ID (will be stored in scans/{stage}/{scan_id}.json)

        Returns:
            Updated campaign

        Raises:
            ValueError: If campaign not found
        """
        campaign = self.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Set the flag and scan ID for this stage
        if stage == Stage.RECON:
            campaign.recon_complete = True
            campaign.recon_scan_id = scan_id
        elif stage == Stage.GARAK:
            campaign.garak_complete = True
            campaign.garak_scan_id = scan_id
        elif stage == Stage.EXPLOIT:
            campaign.exploit_complete = True
            campaign.exploit_scan_id = scan_id

        # Update overall status
        campaign.status = self._compute_status(campaign)

        return self._update(campaign)

    def set_stage_in_progress(
        self,
        campaign_id: str,
        stage: Stage,
    ) -> Campaign:
        """Mark campaign as having a stage in progress.

        Args:
            campaign_id: Campaign to update
            stage: Stage starting

        Returns:
            Updated campaign
        """
        campaign = self.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        campaign.status = CampaignStatus.IN_PROGRESS
        return self._update(campaign)

    def set_failed(self, campaign_id: str, reason: Optional[str] = None) -> Campaign:
        """Mark campaign as failed.

        Args:
            campaign_id: Campaign to update
            reason: Optional failure reason (stored in description)

        Returns:
            Updated campaign
        """
        campaign = self.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        campaign.status = CampaignStatus.FAILED
        if reason:
            campaign.description = f"Failed: {reason}"

        return self._update(campaign)

    def _compute_status(self, campaign: Campaign) -> CampaignStatus:
        """Compute overall status from stage flags."""
        if campaign.recon_complete and campaign.garak_complete and campaign.exploit_complete:
            return CampaignStatus.COMPLETE
        if campaign.recon_complete or campaign.garak_complete or campaign.exploit_complete:
            return CampaignStatus.IN_PROGRESS
        return CampaignStatus.CREATED

    # --- Update Operations ---

    def _update(self, campaign: Campaign) -> Campaign:
        """Update campaign in database."""
        campaign.updated_at = datetime.utcnow().isoformat()

        with get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE campaigns SET
                    name = ?, target_url = ?, status = ?, updated_at = ?,
                    recon_complete = ?, garak_complete = ?, exploit_complete = ?,
                    recon_scan_id = ?, garak_scan_id = ?, exploit_scan_id = ?,
                    description = ?, tags = ?
                WHERE campaign_id = ?
                """,
                (
                    campaign.name,
                    campaign.target_url,
                    campaign.status.value,
                    campaign.updated_at,
                    int(campaign.recon_complete),
                    int(campaign.garak_complete),
                    int(campaign.exploit_complete),
                    campaign.recon_scan_id,
                    campaign.garak_scan_id,
                    campaign.exploit_scan_id,
                    campaign.description,
                    json.dumps(campaign.tags),
                    campaign.campaign_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Campaign {campaign.campaign_id} not found")

        return campaign

    def update_name(self, campaign_id: str, name: str) -> Campaign:
        """Update campaign name."""
        campaign = self.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        campaign.name = name
        return self._update(campaign)

    def add_tags(self, campaign_id: str, tags: List[str]) -> Campaign:
        """Add tags to campaign."""
        campaign = self.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        campaign.tags = list(set(campaign.tags + tags))
        return self._update(campaign)

    # --- Delete Operations ---

    def delete(self, campaign_id: str) -> bool:
        """Delete a campaign.

        Note: This only removes the local index entry.
        S3 scan data is NOT deleted.

        Returns:
            True if deleted, False if not found
        """
        with get_connection(self._db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM campaigns WHERE campaign_id = ?",
                (campaign_id,),
            )
            return cursor.rowcount > 0

    # --- S3 Mapping Helpers ---

    def get_s3_keys(self, campaign_id: str) -> dict:
        """Get all S3 keys for a campaign's completed stages.

        Returns:
            Dict mapping stage name to S3 key
        """
        campaign = self.get(campaign_id)
        if not campaign:
            return {}

        keys = {}
        for stage in Stage:
            key = campaign.get_s3_key(stage)
            if key and campaign.is_stage_complete(stage):
                keys[stage.value] = key

        return keys

    # --- Row Mapping ---

    def _row_to_campaign(self, row) -> Campaign:
        """Convert database row to Campaign."""
        return Campaign(
            campaign_id=row["campaign_id"],
            name=row["name"],
            target_url=row["target_url"],
            status=CampaignStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            recon_complete=bool(row["recon_complete"]),
            garak_complete=bool(row["garak_complete"]),
            exploit_complete=bool(row["exploit_complete"]),
            recon_scan_id=row["recon_scan_id"],
            garak_scan_id=row["garak_scan_id"],
            exploit_scan_id=row["exploit_scan_id"],
            description=row["description"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
        )
