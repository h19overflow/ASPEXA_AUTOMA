"""
Manual Attack Orchestrator

Executes user-provided payloads with optional converters.
"""
import logging
from typing import List, AsyncGenerator, Optional

from pyrit.orchestrator import PromptSendingOrchestrator
from pyrit.prompt_target import PromptTarget
from pyrit.prompt_converter import PromptConverter

from services.snipers.models import AttackEvent
from services.snipers.scoring import CompositeAttackScorer
from services.snipers.core import get_scoring_target
from services.snipers.tools.pyrit_bridge import ConverterFactory

logger = logging.getLogger(__name__)


class ManualAttackOrchestrator:
    """
    Orchestrates manual attacks with user-provided payloads.
    """

    def __init__(
        self,
        objective_target: PromptTarget,
        converter_factory: Optional[ConverterFactory] = None,
    ):
        """
        Initialize manual orchestrator.

        Args:
            objective_target: Target to attack
            converter_factory: Factory for creating converters
        """
        self._objective_target = objective_target
        self._converter_factory = converter_factory or ConverterFactory()
        self._scoring_target = get_scoring_target()

    async def run_attack(
        self,
        payload: str,
        converter_names: Optional[List[str]] = None,
    ) -> AsyncGenerator[AttackEvent, None]:
        """
        Execute manual attack with custom payload.

        Args:
            payload: User-provided attack payload
            converter_names: Optional converters to apply

        Yields:
            AttackEvent objects for SSE streaming
        """
        if not payload:
            yield AttackEvent(
                type="error",
                data={"message": "Payload is required for manual attack"}
            )
            return

        converters = self._get_converters(converter_names or [])

        yield AttackEvent(
            type="started",
            data={
                "mode": "manual",
                "payload_preview": payload[:200],
                "converters": converter_names or [],
            }
        )

        yield AttackEvent(
            type="plan",
            data={
                "mode": "manual",
                "payload_preview": payload[:200],
                "converters": converter_names or [],
            }
        )

        # Create orchestrator with converters
        orchestrator = PromptSendingOrchestrator(
            objective_target=self._objective_target,
            prompt_converters=converters if converters else None,
        )

        try:
            yield AttackEvent(
                type="turn",
                data={"event": "sending", "payload": payload[:300]}
            )

            await orchestrator.send_prompts_async(prompt_list=[payload])

            # Get response from memory
            response = ""
            memory = orchestrator.get_memory()
            if memory:
                entries = memory.get_conversation()
                if entries:
                    response = str(entries[-1])

            # Score response
            scorer = CompositeAttackScorer(self._scoring_target)
            score_result = await scorer.score_async(response)

            yield AttackEvent(
                type="response",
                data={
                    "response": response[:500],
                    "success": score_result.get('success', False),
                    "scores": score_result.get('scores', {}),
                }
            )

            yield AttackEvent(
                type="score",
                data={
                    "success": score_result.get('success', False),
                    "payload": payload[:200],
                    "response": response[:300],
                    "best_score": score_result.get('best_score', 0.0),
                }
            )

        except Exception as e:
            logger.error(f"Manual attack failed: {e}", exc_info=True)
            yield AttackEvent(
                type="error",
                data={"message": str(e)}
            )

        yield AttackEvent(type="complete", data={"mode": "manual"})

    def _get_converters(self, names: List[str]) -> List[PromptConverter]:
        """Get converter instances from names."""
        converters = []
        for name in names:
            converter = self._converter_factory.get_converter(name)
            if converter:
                converters.append(converter)
            else:
                logger.warning(f"Converter not found: {name}")
        return converters
