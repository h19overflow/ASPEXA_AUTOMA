"""
Effectiveness tracking and learning system.

Purpose: Records attack outcomes to learn which framing/format combinations
work best for specific domains and tools. Persists to S3.
"""

import json
import logging
from typing import Protocol

from services.snipers.tools.prompt_articulation.models.effectiveness_record import (
    EffectivenessRecord,
    EffectivenessSummary,
)
from services.snipers.tools.prompt_articulation.models.framing_strategy import FramingType

logger = logging.getLogger(__name__)


class PersistenceProvider(Protocol):
    """Interface for effectiveness data persistence."""

    async def save_records(self, campaign_id: str, records: list[dict]) -> None:
        """Save effectiveness records."""
        ...

    async def load_records(self, campaign_id: str) -> list[dict]:
        """Load effectiveness records."""
        ...


class EffectivenessTracker:
    """Tracks and analyzes payload effectiveness over time.

    Learns from attack outcomes to improve strategy selection.
    Provides success rate queries for FramingLibrary optimization.
    """

    def __init__(
        self,
        campaign_id: str,
        persistence: PersistenceProvider | None = None,
    ):
        """Initialize tracker for campaign.

        Args:
            campaign_id: Campaign identifier for data isolation
            persistence: S3 adapter for saving/loading records
        """
        self.campaign_id = campaign_id
        self.persistence = persistence
        self.records: list[EffectivenessRecord] = []
        self._summaries: dict[tuple[FramingType, str], EffectivenessSummary] = {}

    async def load_history(self) -> None:
        """Load historical records from persistence."""
        if not self.persistence:
            logger.debug("No persistence provider, skipping load")
            return

        try:
            raw_records = await self.persistence.load_records(self.campaign_id)
            self.records = [EffectivenessRecord.model_validate(r) for r in raw_records]
            self._rebuild_summaries()
            logger.info(
                "Loaded effectiveness history",
                extra={
                    "campaign_id": self.campaign_id,
                    "record_count": len(self.records),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to load history: {e}")
            self.records = []

    def record_attempt(
        self,
        framing_type: FramingType,
        format_control: str,
        domain: str,
        success: bool,
        score: float,
        payload_preview: str,
        tool_name: str | None = None,
        defense_triggered: bool = False,
    ) -> None:
        """Record single attack attempt outcome.

        Args:
            framing_type: Framing strategy used
            format_control: Output control phrase used
            domain: Target domain
            success: Whether objective was achieved
            score: Scorer-assigned effectiveness (0.0-1.0)
            payload_preview: First 200 chars of payload
            tool_name: Tool targeted if applicable
            defense_triggered: Whether defense mechanism fired
        """
        record = EffectivenessRecord(
            framing_type=framing_type,
            format_control=format_control,
            domain=domain,
            success=success,
            score=score,
            payload_preview=payload_preview[:200],
            tool_name=tool_name,
            defense_triggered=defense_triggered,
        )

        self.records.append(record)
        self._update_summary(record)

        logger.info(
            "Recorded attack attempt",
            extra={
                "framing_type": framing_type,
                "domain": domain,
                "success": success,
                "score": score,
            },
        )

    def get_success_rate(self, framing_type: FramingType, domain: str) -> float:
        """Get success rate for framing/domain combination.

        Used by FramingLibrary for strategy selection.

        Returns:
            Success rate 0.0-1.0, or 0.0 if no data
        """
        key = (framing_type, domain)
        if key not in self._summaries:
            return 0.0
        return self._summaries[key].success_rate

    def get_summary(
        self, framing_type: FramingType, domain: str
    ) -> EffectivenessSummary | None:
        """Get detailed summary for framing/domain."""
        return self._summaries.get((framing_type, domain))

    async def save(self) -> None:
        """Persist records to storage."""
        if not self.persistence:
            logger.debug("No persistence provider, skipping save")
            return

        raw_records = [r.model_dump() for r in self.records]
        await self.persistence.save_records(self.campaign_id, raw_records)
        logger.info(
            "Saved effectiveness records",
            extra={"campaign_id": self.campaign_id, "record_count": len(raw_records)},
        )

    def _update_summary(self, record: EffectivenessRecord) -> None:
        """Update summary statistics with new record."""
        key = (record.framing_type, record.domain)

        if key not in self._summaries:
            self._summaries[key] = EffectivenessSummary(
                framing_type=record.framing_type,
                domain=record.domain,
            )

        summary = self._summaries[key]
        summary.total_attempts += 1
        if record.success:
            summary.successful_attempts += 1

        # Update rolling average score
        n = summary.total_attempts
        summary.average_score = (summary.average_score * (n - 1) + record.score) / n

    def _rebuild_summaries(self) -> None:
        """Rebuild all summaries from records."""
        self._summaries.clear()
        for record in self.records:
            self._update_summary(record)

    def get_summary_json(self) -> str:
        """Export summaries as JSON for debugging."""
        summaries_dict = {
            f"{k[0]}_{k[1]}": {
                "total_attempts": v.total_attempts,
                "successful_attempts": v.successful_attempts,
                "success_rate": v.success_rate,
                "average_score": v.average_score,
            }
            for k, v in self._summaries.items()
        }
        return json.dumps(summaries_dict, indent=2)
