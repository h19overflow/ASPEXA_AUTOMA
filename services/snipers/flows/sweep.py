"""
Purpose: Sweep attack flow - execute attacks across vulnerability categories
Role: Category-based exploitation using PyRIT PromptSendingOrchestrator
Dependencies: pyrit.orchestrator, snipers.orchestrators
"""
import logging
from typing import AsyncGenerator

from services.snipers.models import AttackEvent, ExploitStreamRequest, ProbeCategory
from services.snipers.orchestrators import SweepAttackOrchestrator
from services.snipers.core import init_pyrit
from libs.connectivity.adapters import ChatHTTPTarget

logger = logging.getLogger(__name__)


async def run_sweep_attack(
    request: ExploitStreamRequest,
) -> AsyncGenerator[AttackEvent, None]:
    """
    Execute sweep attack using PyRIT-based orchestrator.

    Replaces Garak scanner with intelligent PyRIT attacks.

    Args:
        request: Exploit request with categories and options

    Yields:
        AttackEvent objects for SSE streaming
    """
    categories = request.categories or list(ProbeCategory)

    if not categories:
        yield AttackEvent(
            type="error",
            data={"message": "No categories selected for sweep mode"},
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
        orchestrator = SweepAttackOrchestrator(
            objective_target=target,
            objectives_per_category=request.probes_per_category or 5,
        )

        # Run sweep and stream events
        async for event in orchestrator.run_sweep(categories=categories):
            yield event

    except Exception as e:
        logger.error(f"Sweep attack flow failed: {e}", exc_info=True)
        yield AttackEvent(
            type="error",
            data={"message": f"Sweep attack failed: {str(e)}"},
        )
        yield AttackEvent(type="complete", data={"mode": "sweep"})
