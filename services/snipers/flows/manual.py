"""
Purpose: Manual attack flow - custom payload with converters
Role: Direct payload execution using PyRIT PromptSendingOrchestrator
Dependencies: pyrit.orchestrator, snipers.orchestrators
"""
import logging
from typing import AsyncGenerator

from services.snipers.models import AttackEvent, ExploitStreamRequest
from services.snipers.orchestrators import ManualAttackOrchestrator
from services.snipers.core import init_pyrit
from libs.connectivity.adapters import ChatHTTPTarget

logger = logging.getLogger(__name__)


async def run_manual_attack(
    request: ExploitStreamRequest,
) -> AsyncGenerator[AttackEvent, None]:
    """
    Execute manual attack with user-provided payload.

    Uses PyRIT for consistent converter handling and scoring.

    Args:
        request: Exploit request with payload and converters

    Yields:
        AttackEvent objects for SSE streaming
    """
    if not request.custom_payload:
        yield AttackEvent(
            type="error",
            data={"message": "Custom payload required for manual mode"},
        )
        return

    try:
        # Initialize PyRIT
        init_pyrit()

        # Create target adapter
        target = ChatHTTPTarget(
            endpoint_url=request.target_url,
            prompt_template='{"message": "{PROMPT}"}',
            response_path="response",
        )

        # Create orchestrator
        orchestrator = ManualAttackOrchestrator(objective_target=target)

        # Run attack and stream events
        async for event in orchestrator.run_attack(
            payload=request.custom_payload,
            converter_names=request.converters,
        ):
            yield event

    except Exception as e:
        logger.error(f"Manual attack flow failed: {e}", exc_info=True)
        yield AttackEvent(
            type="error",
            data={"message": f"Manual attack failed: {str(e)}"},
        )
        yield AttackEvent(type="complete", data={"mode": "manual"})
