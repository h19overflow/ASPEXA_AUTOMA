"""
Phase 3: Learning & Adaptation Node.

Updates pattern database with successful chains and failures.
Analyzes failure causes and prepares state for retry or escalation.
"""

import logging
from typing import Any
from services.snipers.agent.state import ExploitAgentState
from services.snipers.chain_discovery.models import ConverterChain, ChainMetadata
from services.snipers.chain_discovery.pattern_database import PatternDatabaseAdapter
from services.snipers.scoring.models import SeverityLevel

logger = logging.getLogger(__name__)


class LearningAdaptationNode:
    """
    Learn from attack outcomes and update pattern database.

    Responsibilities:
    - Save successful chains to pattern database
    - Record failure causes for analysis
    - Update effectiveness tracking
    - Prepare adaptation strategy for retry
    """

    def __init__(self, s3_client: Any):
        """
        Initialize learning node.

        Args:
            s3_client: S3 interface for pattern persistence
        """
        self.pattern_db = PatternDatabaseAdapter(s3_client)
        self.logger = logging.getLogger(__name__)

    async def update_patterns(self, state: ExploitAgentState) -> dict[str, Any]:
        """
        Learn from attack results and update patterns.

        Args:
            state: Current exploit agent state

        Returns:
            State updates with learned_chain and failure_analysis
        """
        try:
            campaign_id = state.get("campaign_id", "unknown")
            composite_score = state.get("composite_score")
            selected_converters = state.get("selected_converters")

            self.logger.info(
                "Learning from attack results",
                extra={
                    "campaign_id": campaign_id,
                    "success": composite_score.is_successful if composite_score else False
                }
            )

            result_updates = {}

            # If successful, save chain to database
            if composite_score and composite_score.is_successful and selected_converters:
                try:
                    metadata = ChainMetadata(
                        campaign_id=campaign_id,
                        target_type="http",
                        vulnerability_type=state.get("probe_name", "unknown"),
                        composite_score=composite_score.total_score
                    )

                    # Update chain with success metrics
                    updated_chain = self._update_chain_metrics(
                        selected_converters,
                        composite_score.total_score
                    )

                    await self.pattern_db.save_chain(updated_chain, metadata)

                    self.logger.info(
                        "Saved successful chain to pattern database",
                        extra={
                            "campaign_id": campaign_id,
                            "chain_id": selected_converters.chain_id,
                            "score": composite_score.total_score
                        }
                    )

                    result_updates["learned_chain"] = updated_chain

                except Exception as e:
                    self.logger.error(f"Failed to save chain: {e}")

            # Analyze failure causes if unsuccessful
            if composite_score and not composite_score.is_successful:
                failure_analysis = self._analyze_failure(state, composite_score)
                result_updates["failure_analysis"] = failure_analysis

                self.logger.info(
                    "Analyzed failure cause",
                    extra={
                        "campaign_id": campaign_id,
                        "cause": failure_analysis.get("primary_cause", "unknown")
                    }
                )

            # Prepare adaptation strategy for retry
            if not (composite_score and composite_score.is_successful):
                retry_strategy = self._plan_retry_adaptation(state, composite_score)
                result_updates["adaptation_strategy"] = retry_strategy

            return result_updates

        except Exception as e:
            self.logger.error(
                "Learning node failed",
                extra={"campaign_id": state.get("campaign_id"), "error": str(e)}
            )
            raise

    def _update_chain_metrics(
        self,
        chain: ConverterChain,
        score: float
    ) -> ConverterChain:
        """
        Update chain with success metrics.

        Args:
            chain: Original chain
            score: Composite score achieved

        Returns:
            Updated chain with incremented success count and avg score
        """
        new_success_count = chain.success_count + 1
        new_avg_score = (
            (chain.avg_score * chain.success_count + score) / new_success_count
        )

        return ConverterChain(
            chain_id=chain.chain_id,
            converter_names=chain.converter_names,
            converter_params=chain.converter_params,
            success_count=new_success_count,
            defense_patterns=chain.defense_patterns,
            created_at=chain.created_at,
            last_used_at=chain.last_used_at,
            avg_score=new_avg_score
        )

    def _analyze_failure(
        self,
        state: ExploitAgentState,
        composite_score: Any
    ) -> dict[str, Any]:
        """
        Analyze why attack failed.

        Args:
            state: Current state
            composite_score: Score result

        Returns:
            Failure analysis dict
        """
        analysis = {
            "primary_cause": "unknown",
            "scorer_results": {},
            "recommendations": []
        }

        # Extract scorer results
        if hasattr(composite_score, "scorer_results"):
            for scorer_name, result in composite_score.scorer_results.items():
                analysis["scorer_results"][scorer_name] = {
                    "severity": result.severity.value if hasattr(result, "severity") else "unknown",
                    "confidence": result.confidence if hasattr(result, "confidence") else 0.0
                }

        # Determine primary cause
        if hasattr(composite_score, "overall_severity"):
            if composite_score.overall_severity == SeverityLevel.NONE:
                analysis["primary_cause"] = "no_impact"
                analysis["recommendations"].append("Try different converter chain")
            elif composite_score.overall_severity == SeverityLevel.LOW:
                analysis["primary_cause"] = "low_impact"
                analysis["recommendations"].append("Increase payload specificity")
            else:
                analysis["primary_cause"] = "detection_or_block"
                analysis["recommendations"].append("Try obfuscation converters")

        # Add pattern-based recommendations
        pattern_analysis = state.get("pattern_analysis", {})
        defenses = pattern_analysis.get("defense_mechanisms", []) if pattern_analysis else []
        if "keyword_filter" in defenses:
            analysis["recommendations"].append("Add unicode_substitution converter")
        if "rate_limit" in defenses:
            analysis["recommendations"].append("Reduce payload frequency")

        return analysis

    def _plan_retry_adaptation(
        self,
        state: ExploitAgentState,
        composite_score: Any
    ) -> dict[str, Any]:
        """
        Plan adaptation strategy for retry.

        Args:
            state: Current state
            composite_score: Score result

        Returns:
            Adaptation strategy dict
        """
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)

        strategy = {
            "can_retry": retry_count < max_retries,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "adaptation_actions": []
        }

        if not strategy["can_retry"]:
            strategy["adaptation_actions"].append("Escalate: max retries reached")
            return strategy

        # Suggest adaptations based on failure analysis
        if composite_score and not composite_score.is_successful:
            severity = composite_score.overall_severity.value if hasattr(composite_score, "overall_severity") else "unknown"

            if severity == "none":
                strategy["adaptation_actions"].append("Try different framing strategy")
                strategy["adaptation_actions"].append("Regenerate payload with different context")
            elif severity == "low":
                strategy["adaptation_actions"].append("Increase payload sophistication")
                strategy["adaptation_actions"].append("Try alternative converter chain")
            else:
                strategy["adaptation_actions"].append("Use combinatorial chain discovery")
                strategy["adaptation_actions"].append("Apply evolutionary optimization")

        return strategy


# Module-level async wrapper
async def learning_node(state: ExploitAgentState) -> dict[str, Any]:
    """
    LangGraph-compatible node wrapper.

    Inject node instance via partial():
    from functools import partial
    graph.add_node(
        "learning",
        partial(learning_node, node=node_instance)
    )
    """
    raise NotImplementedError(
        "Use functools.partial to inject LearningAdaptationNode instance"
    )
