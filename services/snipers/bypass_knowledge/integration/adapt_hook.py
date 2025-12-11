"""
Adapt node hook for querying historical bypass knowledge.

Purpose: Non-invasive hook for adapt_node to leverage historical data
Role: Query similar episodes and provide context for strategy generation
Dependencies: QueryProcessor, DefenseFingerprint, BypassKnowledgeLogger

Data Extraction from State:
    - defense_response: phase3_result.attack_responses[0].response
    - failed_techniques: flatten(tried_converters)
    - domain: recon_intelligence.target_domain
"""

import logging
from typing import Any

from services.snipers.bypass_knowledge.integration.config import (
    BypassKnowledgeConfig,
    get_config,
)
from services.snipers.bypass_knowledge.integration.local_logger import (
    BypassKnowledgeLogger,
    get_bypass_logger,
)
from services.snipers.bypass_knowledge.integration.models import HistoryContext
from services.snipers.bypass_knowledge.models.fingerprint import DefenseFingerprint
from services.snipers.bypass_knowledge.models.insight import HistoricalInsight

logger = logging.getLogger(__name__)


class AdaptNodeHook:
    """
    Non-invasive hook for adapt_node to query historical bypass knowledge.

    Queries similar episodes before strategy generation and provides
    context for boosting successful techniques. All operations are
    logged locally for review.
    """

    def __init__(
        self,
        config: BypassKnowledgeConfig | None = None,
        local_logger: BypassKnowledgeLogger | None = None,
    ) -> None:
        """
        Initialize adapt node hook.

        Args:
            config: Configuration (defaults to env-based config)
            local_logger: Logger for JSON output (defaults to singleton)
        """
        self._config = config or get_config()
        self._logger = local_logger or get_bypass_logger()
        self._processor = None  # Lazy init

    def _get_processor(self):
        """Lazy initialize query processor."""
        if self._processor is None and not self._config.log_only:
            try:
                from services.snipers.bypass_knowledge.query import get_query_processor

                self._processor = get_query_processor()
            except Exception as e:
                logger.warning(f"Failed to initialize QueryProcessor: {e}")
                self._processor = None
        return self._processor

    async def query_history(self, state: dict[str, Any]) -> HistoryContext:
        """
        Query historical episodes for similar defenses.

        ALWAYS logs locally regardless of config.
        Only queries S3 Vectors if not in log_only mode.

        Args:
            state: AdaptiveAttackState as dict

        Returns:
            HistoryContext with recommendations (empty if disabled/failed)
        """
        if not self._config.enabled:
            logger.debug("Bypass knowledge disabled, returning empty context")
            return HistoryContext()

        campaign_id = state.get("campaign_id", "unknown")

        try:
            # Extract fingerprint from state
            fingerprint = self._extract_fingerprint(state)

            # Query (or skip if log-only mode)
            if self._config.log_only:
                insight = self._create_empty_insight(fingerprint)
                action_taken = "log_only_mode"
            else:
                processor = self._get_processor()
                if processor:
                    insight = await processor.query_by_fingerprint(fingerprint)
                    action_taken = "queried_s3_vectors"
                else:
                    insight = self._create_empty_insight(fingerprint)
                    action_taken = "processor_unavailable"

            # Build history context with computed recommendations
            history_context = self._build_history_context(
                insight=insight,
                failed_techniques=fingerprint.failed_techniques,
            )

            # Determine if we should inject into prompts
            should_inject = (
                self._config.inject_context
                and history_context.confidence >= self._config.confidence_threshold
            )
            history_context.should_inject = should_inject

            # Generate prompt context preview for logging
            prompt_context = history_context.to_prompt_context() if should_inject else ""

            # ALWAYS log locally for review
            self._logger.log_query(
                campaign_id=campaign_id,
                fingerprint=fingerprint.model_dump(),
                result=insight.model_dump() if insight else {},
                action_taken=action_taken,
                context_injected=should_inject,
                prompt_context_preview=prompt_context,
            )

            # Log injection decision separately for easy filtering
            if insight and insight.similar_cases_found > 0:
                reason = "confidence sufficient" if should_inject else f"confidence {history_context.confidence:.2f} < threshold {self._config.confidence_threshold}"
                self._logger.log_injection(
                    campaign_id=campaign_id,
                    context_text=prompt_context if should_inject else history_context.to_prompt_context(),
                    applied=should_inject,
                    confidence=history_context.confidence,
                    reason=reason,
                )

            logger.info(
                f"[BypassKnowledge] Query: {insight.similar_cases_found if insight else 0} similar episodes, "
                f"confidence={history_context.confidence:.2f}, inject={should_inject}"
            )

            return history_context

        except Exception as e:
            logger.warning(f"[BypassKnowledge] Query failed: {e}")
            # Log the failure
            self._logger.log_query(
                campaign_id=campaign_id,
                fingerprint={},
                result={},
                action_taken=f"error: {str(e)[:100]}",
                context_injected=False,
            )
            return HistoryContext()

    def _extract_fingerprint(self, state: dict[str, Any]) -> DefenseFingerprint:
        """
        Extract defense fingerprint from state fields.

        Data paths (from PHASE_7 spec):
            - defense_response: phase3_result.attack_responses[0].response
            - failed_techniques: tried_converters (flattened)
            - domain: recon_intelligence.target_domain

        Args:
            state: AdaptiveAttackState as dict

        Returns:
            DefenseFingerprint for similarity search
        """
        # Extract defense_response from phase3_result
        defense_response = ""
        phase3 = state.get("phase3_result")
        if phase3:
            # Handle both dict and object access patterns
            if isinstance(phase3, dict):
                responses = phase3.get("attack_responses", [])
                if responses:
                    first_resp = responses[0]
                    defense_response = first_resp.get("response", "") if isinstance(first_resp, dict) else getattr(first_resp, "response", "")
            elif hasattr(phase3, "attack_responses") and phase3.attack_responses:
                defense_response = phase3.attack_responses[0].response or ""

        # Extract failed_techniques from tried_converters
        tried_converters = state.get("tried_converters", [])
        failed_techniques = self._flatten_converter_chains(tried_converters)

        # Extract domain from recon_intelligence
        domain = "general"
        recon = state.get("recon_intelligence")
        if recon:
            if isinstance(recon, dict):
                domain = recon.get("target_domain", "general")
            elif hasattr(recon, "target_domain"):
                domain = recon.target_domain or "general"

        # Also try phase1_result.context_summary.recon_intelligence
        if domain == "general":
            phase1 = state.get("phase1_result")
            if phase1:
                context_summary = getattr(phase1, "context_summary", None) or (phase1.get("context_summary") if isinstance(phase1, dict) else None)
                if context_summary and isinstance(context_summary, dict):
                    recon_intel = context_summary.get("recon_intelligence", {})
                    if recon_intel:
                        domain = recon_intel.get("target_domain", "general")

        return DefenseFingerprint(
            defense_response=defense_response[:1000],  # Truncate for embedding
            failed_techniques=failed_techniques,
            domain=domain,
        )

    def _flatten_converter_chains(self, tried_converters: list[list[str]]) -> list[str]:
        """
        Flatten converter chains to unique technique names.

        Args:
            tried_converters: List of converter chains (e.g., [["rot13"], ["base64", "homoglyph"]])

        Returns:
            Unique technique names (e.g., ["rot13", "base64", "homoglyph"])
        """
        techniques = set()
        for chain in tried_converters:
            if isinstance(chain, list):
                for converter in chain:
                    if isinstance(converter, str):
                        # Extract base technique from converter name
                        # e.g., "base64_encoder" -> "base64"
                        base = converter.split("_")[0] if "_" in converter else converter
                        techniques.add(base)
        return list(techniques)

    def _build_history_context(
        self,
        insight: HistoricalInsight | None,
        failed_techniques: list[str],
    ) -> HistoryContext:
        """
        Build history context with computed recommendations.

        Args:
            insight: Historical insight from query (or None)
            failed_techniques: Already tried techniques to exclude from boost list

        Returns:
            HistoryContext with boost/avoid lists populated
        """
        if not insight:
            return HistoryContext()

        # Even with 0 similar cases, include the insight for logging visibility
        if insight.similar_cases_found == 0:
            return HistoryContext(
                insight=insight,
                confidence=0.0,
                should_inject=False,
            )

        # Compute boost and avoid lists from technique stats
        boost = []
        avoid = []

        for stat in insight.technique_stats:
            # Boost high success rate techniques not already tried
            if stat.success_rate >= 0.5 and stat.technique not in failed_techniques:
                boost.append(stat.technique)
            # Avoid low success rate techniques
            elif stat.success_rate < self._config.low_success_threshold:
                avoid.append(stat.technique)

        return HistoryContext(
            insight=insight,
            boost_techniques=boost[:3],  # Top 3 to boost
            avoid_techniques=avoid[:3],  # Top 3 to avoid
            recommended_framing=insight.recommended_framing,
            recommended_converters=insight.recommended_converters,
            confidence=insight.confidence,
            should_inject=False,  # Set by caller based on threshold
        )

    def _create_empty_insight(self, fingerprint: DefenseFingerprint) -> HistoricalInsight:
        """Create empty insight for logging in log-only mode."""
        return HistoricalInsight(
            query=fingerprint.to_embedding_text()[:200],
            similar_cases_found=0,
            dominant_mechanism="unknown",
            mechanism_confidence=0.0,
            technique_stats=[],
            recommended_technique="",
            recommended_framing="",
            key_pattern="Log-only mode: no S3 query performed",
            confidence=0.0,
            reasoning="Log-only mode active",
        )

    def should_apply_boost(self, context: HistoryContext) -> bool:
        """
        Check if historical context is confident enough to apply.

        Args:
            context: History context from query_history()

        Returns:
            True if confidence meets threshold
        """
        return context.confidence >= self._config.confidence_threshold


# === SINGLETON ===
_hook: AdaptNodeHook | None = None


def get_adapt_hook() -> AdaptNodeHook:
    """
    Get or create singleton adapt node hook.

    Returns:
        AdaptNodeHook instance configured from environment
    """
    global _hook
    if _hook is None:
        _hook = AdaptNodeHook()
    return _hook


def reset_adapt_hook() -> None:
    """Clear singleton hook (useful for testing)."""
    global _hook
    _hook = None
