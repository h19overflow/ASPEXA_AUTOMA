"""
Purpose: Guided attack flow - uses Garak findings for intelligent attack selection
Role: Pattern-learning exploitation using PyRIT RedTeamingOrchestrator
Dependencies: pyrit.orchestrator, snipers.orchestrators
"""
import logging
from typing import AsyncGenerator, List, Optional, Dict, Any

from services.snipers.models import AttackEvent, ExploitStreamRequest
from services.snipers.orchestrators import GuidedAttackOrchestrator
from services.snipers.core import init_pyrit
from libs.connectivity.adapters import ChatHTTPTarget

logger = logging.getLogger(__name__)


async def run_guided_attack(
    request: ExploitStreamRequest,
    garak_findings: Optional[List[Dict[str, Any]]] = None,
) -> AsyncGenerator[AttackEvent, None]:
    """
    Execute guided attack using PyRIT RedTeamingOrchestrator.

    Leverages Garak findings to build intelligent multi-turn attacks.

    Args:
        request: Exploit request with target and options
        garak_findings: Optional vulnerability findings from Garak

    Yields:
        AttackEvent objects for SSE streaming
    """
    if not garak_findings and not request.probe_name:
        yield AttackEvent(
            type="error",
            data={"message": "Either garak_findings or probe_name required for guided mode"},
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
        orchestrator = GuidedAttackOrchestrator(
            objective_target=target,
            max_turns=getattr(request, 'max_turns', 10),
        )

        # Run attack and stream events
        async for event in orchestrator.run_attack(
            garak_findings=garak_findings or [],
            probe_name=request.probe_name,
        ):
            yield event

    except Exception as e:
        logger.error(f"Guided attack flow failed: {e}", exc_info=True)
        yield AttackEvent(
            type="error",
            data={"message": f"Guided attack failed: {str(e)}"},
        )
        yield AttackEvent(type="complete", data={"mode": "guided"})
