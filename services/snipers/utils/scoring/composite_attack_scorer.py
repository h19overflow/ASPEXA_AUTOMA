"""
Composite Attack Scorer

Combines multiple scorers for comprehensive evaluation.
Returns success if ANY scorer indicates success.
"""
import logging
from typing import List, Optional

from pyrit.prompt_target import PromptChatTarget

from .jailbreak_scorer import JailbreakScorer
from .prompt_leak_scorer import PromptLeakScorer

logger = logging.getLogger(__name__)


class CompositeAttackScorer:
    """
    Combines multiple scorers and returns aggregate result.

    Used when attack could succeed in multiple ways.
    """

    def __init__(
        self,
        chat_target: PromptChatTarget,
        scorer_types: Optional[List[str]] = None
    ):
        """
        Initialize with scorer types.

        Args:
            chat_target: LLM for scoring
            scorer_types: List of scorer types to use
                Options: 'jailbreak', 'prompt_leak'
                Default: ['jailbreak', 'prompt_leak']
        """
        self._scorers = []
        self._chat_target = chat_target
        types = scorer_types or ['jailbreak', 'prompt_leak']

        for stype in types:
            if stype == 'jailbreak':
                self._scorers.append(('jailbreak', JailbreakScorer(chat_target)))
            elif stype == 'prompt_leak':
                self._scorers.append(('prompt_leak', PromptLeakScorer(chat_target)))
            else:
                logger.warning(f"Unknown scorer type: {stype}")

        logger.info(f"CompositeAttackScorer initialized with {len(self._scorers)} scorers")

    async def score_async(self, response: str) -> dict:
        """
        Score response with all configured scorers.

        Args:
            response: Target's response to evaluate

        Returns:
            Dict with:
                - success: True if ANY scorer indicates success
                - scores: Dict of individual scorer results
                - best_score: Highest score achieved
                - rationale: Combined rationale
        """
        results = {}
        best_score = 0.0
        success = False
        rationales = []

        for name, scorer in self._scorers:
            try:
                result = await scorer.score_async(response)
                results[name] = result

                if result.get('success'):
                    success = True

                score = result.get('score', 0.0)
                if score > best_score:
                    best_score = score

                if result.get('rationale'):
                    rationales.append(f"{name}: {result['rationale']}")

            except Exception as e:
                logger.error(f"Scorer {name} failed: {e}")
                results[name] = {
                    "success": False,
                    "score": 0.0,
                    "rationale": f"Error: {str(e)}",
                }

        return {
            "success": success,
            "best_score": best_score,
            "scores": results,
            "rationale": " | ".join(rationales) if rationales else "No rationale",
        }

    def get_scorer_types(self) -> List[str]:
        """Get list of configured scorer types."""
        return [name for name, _ in self._scorers]
