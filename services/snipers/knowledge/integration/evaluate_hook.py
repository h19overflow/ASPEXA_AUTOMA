"""
Evaluate node hook for capturing successful bypass episodes.

Purpose: Non-invasive hook for evaluate_node to capture episodes after success
Role: Extract and store bypass episodes when attack succeeds
Dependencies: EpisodeCapturer, BypassKnowledgeLogger

Capture Trigger (from PHASE_5 spec):
    - phase3_result.is_successful == True
    - phase3_result.composite_score.total_score >= min_capture_score
"""

import logging
from typing import Any

from services.snipers.knowledge.integration.config import (
    BypassKnowledgeConfig,
    get_config,
)
from services.snipers.knowledge.integration.local_logger import (
    BypassKnowledgeLogger,
    get_bypass_logger,
)
from services.snipers.knowledge.integration.models import CaptureResult

logger = logging.getLogger(__name__)


class EvaluateNodeHook:
    """
    Non-invasive hook for evaluate_node to capture successful episodes.

    Captures bypass episodes when attack succeeds and score meets threshold.
    All operations are logged locally for review.
    """

    def __init__(
        self,
        config: BypassKnowledgeConfig | None = None,
        local_logger: BypassKnowledgeLogger | None = None,
    ) -> None:
        """
        Initialize evaluate node hook.

        Args:
            config: Configuration (defaults to env-based config)
            local_logger: Logger for JSON output (defaults to singleton)
        """
        self._config = config or get_config()
        self._logger = local_logger or get_bypass_logger()
        self._capturer = None  # Lazy init

    def _get_capturer(self):
        """Lazy initialize episode capturer."""
        if self._capturer is None and not self._config.log_only:
            try:
                from services.snipers.knowledge.capture import get_episode_capturer

                self._capturer = get_episode_capturer()
            except Exception as e:
                logger.warning(f"Failed to initialize EpisodeCapturer: {e}")
                self._capturer = None
        return self._capturer

    async def maybe_capture(self, state: dict[str, Any]) -> CaptureResult:
        """
        Capture episode if success criteria met.

        ALWAYS logs locally regardless of config.
        Only stores to S3 Vectors if not in log_only mode.

        Args:
            state: AdaptiveAttackState as dict

        Returns:
            CaptureResult indicating what happened
        """
        if not self._config.enabled:
            logger.debug("Bypass knowledge disabled, skipping capture")
            return CaptureResult(captured=False, reason="bypass_knowledge_disabled")

        campaign_id = state.get("campaign_id", "unknown")

        # Check if we should capture based on success criteria
        should_capture, reason = self._should_capture(state)

        if not should_capture:
            # Log the skip decision for visibility
            self._logger.log_capture(
                campaign_id=campaign_id,
                episode={},
                stored=False,
                reason=reason,
            )
            logger.debug(f"[BypassKnowledge] Capture skipped: {reason}")
            return CaptureResult(captured=False, reason=reason)

        try:
            # Build episode (or preview if log-only mode)
            if self._config.log_only:
                episode_dict = self._build_episode_preview(state)
                stored = False
                episode_id = episode_dict.get("episode_id", "preview")
            else:
                capturer = self._get_capturer()
                if capturer:
                    episode = await capturer.capture_from_state(state, campaign_id)
                    if episode:
                        episode_dict = episode.model_dump()
                        episode_id = episode.episode_id
                        stored = True
                    else:
                        episode_dict = {}
                        episode_id = None
                        stored = False
                        reason = "capturer_returned_none"
                else:
                    episode_dict = self._build_episode_preview(state)
                    episode_id = episode_dict.get("episode_id", "preview")
                    stored = False
                    reason = "capturer_unavailable"

            # ALWAYS log locally for review
            log_path = self._logger.log_capture(
                campaign_id=campaign_id,
                episode=episode_dict,
                stored=stored,
                reason=reason if not stored else "",
            )

            logger.info(
                f"[BypassKnowledge] Capture: episode={episode_id}, stored={stored}"
            )

            return CaptureResult(
                captured=True,
                reason="" if stored else reason,
                episode_id=episode_id,
                log_path=str(log_path),
                stored_to_s3=stored,
            )

        except Exception as e:
            logger.warning(f"[BypassKnowledge] Capture failed: {e}")
            # Log the failure
            self._logger.log_capture(
                campaign_id=campaign_id,
                episode={},
                stored=False,
                reason=f"error: {str(e)[:100]}",
            )
            return CaptureResult(captured=False, reason=f"error: {str(e)[:100]}")

    def _should_capture(self, state: dict[str, Any]) -> tuple[bool, str]:
        """
        Check if state meets capture criteria.

        Criteria (from PHASE_5 spec):
            - is_successful == True
            - composite_score.total_score >= min_capture_score

        Args:
            state: AdaptiveAttackState as dict

        Returns:
            Tuple of (should_capture, reason)
        """
        # Check is_successful
        is_successful = state.get("is_successful", False)
        if not is_successful:
            return False, "not_successful"

        # Check score threshold
        phase3 = state.get("phase3_result")
        if not phase3:
            return False, "no_phase3_result"

        # Handle both dict and object access
        if isinstance(phase3, dict):
            composite = phase3.get("composite_score", {})
            score = composite.get("total_score", 0) if isinstance(composite, dict) else 0
        elif hasattr(phase3, "composite_score") and phase3.composite_score:
            score = phase3.composite_score.total_score
        else:
            score = 0

        if score < self._config.min_capture_score:
            return False, f"score_{score:.2f}_below_threshold_{self._config.min_capture_score}"

        return True, ""

    def _build_episode_preview(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Build preview episode dict for log-only mode.

        Extracts key fields without full LLM reasoning generation.

        Args:
            state: AdaptiveAttackState as dict

        Returns:
            Episode-like dict for logging purposes
        """
        import uuid
        from datetime import datetime, timezone

        campaign_id = state.get("campaign_id", "unknown")
        episode_id = f"preview-{uuid.uuid4().hex[:8]}"

        # Extract defense_response
        defense_response = ""
        phase3 = state.get("phase3_result")
        if phase3:
            if isinstance(phase3, dict):
                responses = phase3.get("attack_responses", [])
                if responses:
                    first = responses[0]
                    defense_response = first.get("response", "") if isinstance(first, dict) else getattr(first, "response", "")
            elif hasattr(phase3, "attack_responses") and phase3.attack_responses:
                defense_response = phase3.attack_responses[0].response or ""

        # Extract successful technique (from chain_selection_result or converter_names)
        successful_technique = "unknown"
        chain_result = state.get("chain_selection_result")
        if chain_result:
            if isinstance(chain_result, dict):
                chain = chain_result.get("selected_chain", [])
            elif hasattr(chain_result, "selected_chain"):
                chain = chain_result.selected_chain
            else:
                chain = []
            successful_technique = chain[0] if chain else "unknown"
        elif state.get("converter_names"):
            converters = state["converter_names"]
            successful_technique = converters[0] if converters else "unknown"

        # Extract successful framing
        successful_framing = "unknown"
        custom_framing = state.get("custom_framing")
        if custom_framing:
            if isinstance(custom_framing, dict):
                successful_framing = custom_framing.get("name", "custom")
            elif hasattr(custom_framing, "name"):
                successful_framing = custom_framing.name
        elif state.get("framing_types"):
            framings = state["framing_types"]
            successful_framing = framings[0] if framings else "unknown"

        # Extract score
        score = 0.0
        if phase3:
            if isinstance(phase3, dict):
                composite = phase3.get("composite_score", {})
                score = composite.get("total_score", 0) if isinstance(composite, dict) else 0
            elif hasattr(phase3, "composite_score") and phase3.composite_score:
                score = phase3.composite_score.total_score

        # Extract domain
        domain = "general"
        phase1 = state.get("phase1_result")
        if phase1:
            context_summary = getattr(phase1, "context_summary", None) or (phase1.get("context_summary") if isinstance(phase1, dict) else None)
            if context_summary and isinstance(context_summary, dict):
                recon_intel = context_summary.get("recon_intelligence", {})
                if recon_intel:
                    domain = recon_intel.get("target_domain", "general")

        # Extract tried converters as failed techniques
        tried_converters = state.get("tried_converters", [])
        failed_techniques = []
        for chain in tried_converters[:-1]:  # All except last (successful) chain
            if isinstance(chain, list):
                failed_techniques.extend(chain)

        return {
            "episode_id": episode_id,
            "campaign_id": campaign_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "defense_response": defense_response[:500],
            "successful_technique": successful_technique,
            "successful_framing": successful_framing,
            "successful_converters": state.get("converter_names", []),
            "jailbreak_score": score,
            "target_domain": domain,
            "iteration_count": state.get("iteration", 0) + 1,
            "failed_techniques": failed_techniques,
            "mechanism_conclusion": "[preview - no LLM analysis]",
            "why_it_worked": "[preview - no LLM analysis]",
            "key_insight": "[preview - requires full capture for LLM reasoning]",
            "_preview": True,
        }


# === SINGLETON ===
_hook: EvaluateNodeHook | None = None


def get_evaluate_hook() -> EvaluateNodeHook:
    """
    Get or create singleton evaluate node hook.

    Returns:
        EvaluateNodeHook instance configured from environment
    """
    global _hook
    if _hook is None:
        _hook = EvaluateNodeHook()
    return _hook


def reset_evaluate_hook() -> None:
    """Clear singleton hook (useful for testing)."""
    global _hook
    _hook = None
