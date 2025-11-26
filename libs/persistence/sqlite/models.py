"""SQLite data models for campaign tracking.

Defines campaign structure, stages, and S3 scan mappings.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class Stage(str, Enum):
    """Campaign execution stages."""
    RECON = "recon"
    GARAK = "garak"
    EXPLOIT = "exploit"


class CampaignStatus(str, Enum):
    """Overall campaign status."""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ScanMapping:
    """Maps a stage to its S3 scan result.

    Links campaign stage completion to actual scan data in S3.
    """
    stage: Stage
    scan_id: str
    s3_key: str
    completed_at: str

    @property
    def s3_uri(self) -> str:
        """Full S3 URI for this scan."""
        return f"s3://{{bucket}}/{self.s3_key}"


@dataclass
class Campaign:
    """Campaign tracking record with stage flags.

    Attributes:
        campaign_id: Unique identifier (UUID)
        name: Human-readable name
        target_url: Target being audited
        status: Overall campaign status
        created_at: Creation timestamp
        updated_at: Last update timestamp

        Stage flags (True when complete):
        recon_complete: Reconnaissance done
        garak_complete: Jailbreak scanning done
        exploit_complete: Exploit execution done

        S3 mappings:
        recon_scan_id: S3 scan ID for recon
        garak_scan_id: S3 scan ID for garak
        exploit_scan_id: S3 scan ID for exploit
    """
    campaign_id: str
    name: str
    target_url: str
    status: CampaignStatus = CampaignStatus.CREATED
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Stage completion flags
    recon_complete: bool = False
    garak_complete: bool = False
    exploit_complete: bool = False

    # S3 scan ID mappings (None = not yet run)
    recon_scan_id: Optional[str] = None
    garak_scan_id: Optional[str] = None
    exploit_scan_id: Optional[str] = None

    # Optional metadata
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def is_stage_complete(self, stage: Stage) -> bool:
        """Check if a stage is complete."""
        flag_map = {
            Stage.RECON: self.recon_complete,
            Stage.GARAK: self.garak_complete,
            Stage.EXPLOIT: self.exploit_complete,
        }
        return flag_map[stage]

    def get_scan_id(self, stage: Stage) -> Optional[str]:
        """Get the S3 scan ID for a stage."""
        id_map = {
            Stage.RECON: self.recon_scan_id,
            Stage.GARAK: self.garak_scan_id,
            Stage.EXPLOIT: self.exploit_scan_id,
        }
        return id_map[stage]

    def get_s3_key(self, stage: Stage) -> Optional[str]:
        """Get the full S3 key for a stage's scan result."""
        scan_id = self.get_scan_id(stage)
        if not scan_id:
            return None
        return f"scans/{stage.value}/{scan_id}.json"

    def get_all_mappings(self) -> List[ScanMapping]:
        """Get all completed stage-to-S3 mappings."""
        mappings = []
        for stage in Stage:
            scan_id = self.get_scan_id(stage)
            if scan_id and self.is_stage_complete(stage):
                mappings.append(ScanMapping(
                    stage=stage,
                    scan_id=scan_id,
                    s3_key=self.get_s3_key(stage),
                    completed_at=self.updated_at,
                ))
        return mappings

    @property
    def progress_summary(self) -> str:
        """Human-readable progress summary."""
        stages = []
        if self.recon_complete:
            stages.append("Recon")
        if self.garak_complete:
            stages.append("Garak")
        if self.exploit_complete:
            stages.append("Exploit")

        if not stages:
            return "Not started"
        return f"{len(stages)}/3 complete: {', '.join(stages)}"
