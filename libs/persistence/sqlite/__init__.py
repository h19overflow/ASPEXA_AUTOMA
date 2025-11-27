"""SQLite persistence layer for local campaign tracking.

Provides fast local queries for campaigns while scan data lives in S3.
Campaign IDs map to S3 keys, with stage flags tracking progress.

Usage:
    from libs.persistence.sqlite import CampaignRepository, Campaign

    repo = CampaignRepository()
    campaign = repo.create_campaign("My Audit", "http://target.com/chat")
    repo.set_stage_complete(campaign.campaign_id, Stage.RECON, "scan-001")

Cleanup:
    from libs.persistence.sqlite import reset_database, get_database_stats

    stats = get_database_stats()
    reset_database()  # Delete all records
"""
from .models import Campaign, CampaignStatus, Stage, ScanMapping
from .repository import CampaignRepository
from .connection import get_connection, init_database
from .cleanup import (
    delete_all_campaigns,
    reset_database,
    drop_database,
    get_database_stats,
)

__all__ = [
    "Campaign",
    "CampaignStatus",
    "Stage",
    "ScanMapping",
    "CampaignRepository",
    "get_connection",
    "init_database",
    # Cleanup utilities
    "delete_all_campaigns",
    "reset_database",
    "drop_database",
    "get_database_stats",
]
