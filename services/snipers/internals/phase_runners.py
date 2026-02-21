"""Phase execution runners for the adaptive attack loop."""

import logging
from typing import Any

from services.snipers.core.phases import (
    AttackExecution,
    Conversion,
    PayloadArticulation,
)
from services.snipers.internals.phase_events import (
    build_phase1_events,
    build_phase2_events,
    build_phase3_events,
)
from services.snipers.models import Phase1Result, Phase3Result

logger = logging.getLogger(__name__)


async def run_phase1(
    campaign_id: str,
    payload_count: int,
    current_framings: list[str],
    custom_framing: dict | None,
    recon_custom_framing: dict | None,
    payload_guidance: str | None,
    chain_context: Any,
    iteration: int,
    tried_framings: list[str],
    avoid_terms: list[str] | None = None,
    emphasize_terms: list[str] | None = None,
) -> tuple[Phase1Result, list[dict[str, Any]]]:
    """Execute Phase 1 (Payload Articulation). Returns result and events."""
    phase1 = PayloadArticulation()
    result = await phase1.execute(
        campaign_id=campaign_id,
        payload_count=payload_count,
        framing_types=current_framings,
        custom_framing=custom_framing,
        recon_custom_framing=recon_custom_framing,
        payload_guidance=payload_guidance,
        chain_discovery_context=(
            chain_context.model_dump() if chain_context else None
        ),
        avoid_terms=avoid_terms,
        emphasize_terms=emphasize_terms,
    )
    if result.framing_type and result.framing_type not in tried_framings:
        tried_framings.append(result.framing_type)

    return result, build_phase1_events(result, iteration)


async def run_phase2(
    payloads: list[str],
    current_converters: list[str],
    iteration: int,
    tried_converters: list[list[str]],
) -> tuple[Any, list[dict[str, Any]]]:
    """Execute Phase 2 (Payload Conversion). Returns result and events."""
    phase2 = Conversion()
    result = await phase2.execute(
        payloads=payloads,
        chain=None,
        converter_names=current_converters,
    )
    if result.converter_names and result.converter_names not in tried_converters:
        tried_converters.append(result.converter_names)

    return result, build_phase2_events(result, iteration)


async def run_phase3(
    campaign_id: str,
    target_url: str,
    payloads: list,
    iteration: int,
) -> tuple[Phase3Result, list[dict[str, Any]]]:
    """Execute Phase 3 (Attack Execution). Returns result and events."""
    phase3 = AttackExecution(target_url=target_url)
    result = await phase3.execute(
        campaign_id=campaign_id,
        payloads=payloads,
        chain=None,
        max_concurrent=3,
    )
    return result, build_phase3_events(result, target_url, iteration)
