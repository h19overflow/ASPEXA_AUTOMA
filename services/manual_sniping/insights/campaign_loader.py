"""Campaign intelligence loader.

Loads and aggregates intelligence from previous campaign phases.
Dependencies: libs.persistence.s3, libs.persistence.sqlite
System role: Campaign intelligence aggregation
"""
from typing import Optional
import logging

from libs.persistence.s3 import S3PersistenceAdapter
from libs.persistence.contracts import AuditPhase
from libs.persistence.scan_models import ScanType
from libs.persistence.sqlite import CampaignRepository

from ..models.insights import (
    CampaignInsights,
    ReconInsights,
    ScanInsights,
    ExploitInsights,
    VulnerabilityPattern,
)

logger = logging.getLogger(__name__)


class CampaignIntelligenceLoader:
    """Loads campaign intelligence from S3 artifacts.

    Aggregates insights from recon, scan, and exploit phases.
    """

    def __init__(self, s3_adapter: Optional[S3PersistenceAdapter] = None):
        """Initialize intelligence loader.

        Args:
            s3_adapter: Optional S3 adapter for testing
        """
        self._s3 = s3_adapter or S3PersistenceAdapter(
            bucket_name="aspexa-automa-audit-lake"
        )
        self._campaign_repo = CampaignRepository()

    async def load_campaign_insights(
        self, campaign_id: str
    ) -> Optional[CampaignInsights]:
        """Load aggregated intelligence for a campaign.

        Args:
            campaign_id: Campaign identifier

        Returns:
            CampaignInsights if campaign found, None otherwise
        """
        # Get campaign metadata
        campaign = self._campaign_repo.get(campaign_id)
        if not campaign:
            logger.warning("Campaign %s not found", campaign_id)
            return None

        insights = CampaignInsights(
            campaign_id=campaign_id,
            campaign_name=campaign.name,
        )

        # Load recon insights if available
        if campaign.recon_scan_id:
            insights.recon = await self._load_recon_insights(
                campaign_id, campaign.recon_scan_id
            )

        # Load scan insights if available
        if campaign.garak_scan_id:
            insights.scan = await self._load_scan_insights(
                campaign_id, campaign.garak_scan_id
            )

        # Load exploit insights if available
        if campaign.exploit_scan_id:
            insights.exploit = await self._load_exploit_insights(
                campaign_id, campaign.exploit_scan_id
            )

        # Aggregate vulnerability patterns
        if insights.exploit:
            insights.patterns.extend(insights.exploit.patterns_found)

        return insights

    async def _load_recon_insights(
        self, campaign_id: str, scan_id: str
    ) -> Optional[ReconInsights]:
        """Load reconnaissance insights.

        Args:
            campaign_id: Campaign ID
            scan_id: Recon scan ID

        Returns:
            ReconInsights if available
        """
        try:
            data = await self._s3.load_scan_result(
                ScanType.RECON, scan_id, validate=False
            )
            # Extract relevant fields from recon result
            return ReconInsights(
                system_prompt_leak=data.get("system_prompt"),
                detected_tools=data.get("tools", []),
                infrastructure=data.get("infrastructure", {}),
                auth_structure=data.get("auth", {}),
            )
        except Exception as e:
            logger.warning("Failed to load recon insights: %s", e)
            return None

    async def _load_scan_insights(
        self, campaign_id: str, scan_id: str
    ) -> Optional[ScanInsights]:
        """Load vulnerability scan insights.

        Args:
            campaign_id: Campaign ID
            scan_id: Garak scan ID

        Returns:
            ScanInsights if available
        """
        try:
            data = await self._s3.load_scan_result(
                ScanType.GARAK, scan_id, validate=False
            )
            # Extract vulnerable probes and successful payloads
            vulnerable_probes = []
            successful_payloads = []
            detector_scores = {}

            for result in data.get("results", []):
                if result.get("passed", False):
                    probe = result.get("probe", "")
                    vulnerable_probes.append(probe)
                    if "payload" in result:
                        successful_payloads.append({
                            "probe": probe,
                            "payload": result["payload"],
                            "detector_score": result.get("detector_score", 0.0),
                        })
                    detector_scores[probe] = result.get("detector_score", 0.0)

            return ScanInsights(
                vulnerable_probes=vulnerable_probes,
                successful_payloads=successful_payloads,
                detector_scores=detector_scores,
            )
        except Exception as e:
            logger.warning("Failed to load scan insights: %s", e)
            return None

    async def _load_exploit_insights(
        self, campaign_id: str, scan_id: str
    ) -> Optional[ExploitInsights]:
        """Load exploitation insights.

        Args:
            campaign_id: Campaign ID
            scan_id: Exploit scan ID

        Returns:
            ExploitInsights if available
        """
        try:
            data = await self._s3.load_scan_result(
                ScanType.EXPLOIT, scan_id, validate=False
            )

            # Extract patterns and converter effectiveness
            patterns = []
            converter_effectiveness = {}

            for attempt in data.get("attempts", []):
                if attempt.get("success", False):
                    # Track converter effectiveness
                    for converter in attempt.get("converters", []):
                        if converter not in converter_effectiveness:
                            converter_effectiveness[converter] = 0
                        converter_effectiveness[converter] += 1

            # Create vulnerability patterns from successful attempts
            for idx, attempt in enumerate(data.get("attempts", [])):
                if attempt.get("success", False):
                    patterns.append(
                        VulnerabilityPattern(
                            pattern_id=f"exploit-{idx}",
                            source="snipers",
                            vulnerability_type=attempt.get("vulnerability_type", "unknown"),
                            description=attempt.get("description", "Successful exploit"),
                            successful_payloads=[attempt.get("payload", "")],
                            confidence=attempt.get("confidence", 0.5),
                            metadata=attempt.get("metadata", {}),
                        )
                    )

            return ExploitInsights(
                patterns_found=patterns,
                converter_effectiveness=converter_effectiveness,
            )
        except Exception as e:
            logger.warning("Failed to load exploit insights: %s", e)
            return None
