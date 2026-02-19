"""Loop state and initial checkpoint creation."""

import logging
from typing import Any

from libs.persistence import CheckpointConfig
from services.snipers.infrastructure.persistence.s3_adapter import create_checkpoint

logger = logging.getLogger(__name__)


class LoopState:
    """Mutable state for the attack loop."""

    def __init__(self, converters: list[str], framings: list[str]) -> None:
        self.converters = converters
        self.framings = framings
        self.custom_framing: dict | None = None
        self.recon_custom_framing: dict | None = None
        self.payload_guidance: str | None = None
        self.adaptation_reasoning: str = ""
        self.chain_context = None
        self.tried_framings: list[str] = []
        self.tried_converters: list[list[str]] = []
        self.iteration_history: list[dict[str, Any]] = []
        self.best_score: float = 0.0
        self.best_iteration: int = 0
        self.phase1_result = None
        self.phase2_result = None
        self.phase3_result = None


async def create_initial_checkpoint(
    campaign_id: str, scan_id: str, target_url: str,
    max_iterations: int, payload_count: int,
    success_scorers: list[str], success_threshold: float,
) -> None:
    """Create the initial S3 checkpoint for a new attack run."""
    try:
        await create_checkpoint(
            campaign_id=campaign_id, scan_id=scan_id, target_url=target_url,
            config=CheckpointConfig(
                max_iterations=max_iterations, payload_count=payload_count,
                success_scorers=success_scorers, success_threshold=success_threshold,
            ),
        )
    except Exception as e:
        logger.warning(f"Failed to create initial checkpoint: {e}")
