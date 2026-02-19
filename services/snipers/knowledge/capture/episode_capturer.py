"""
Episode capture from adaptive attack state.

Extracts successful bypass episodes and generates reasoning
for why the attack succeeded using LangChain v1 create_agent.

Dependencies:
    - langchain>=1.0.0
    - Phase 1 models (BypassEpisode, Hypothesis, ProbeResult, FailureDepth)
    - Phase 4 storage (EpisodeStore)

System Role:
    Captures successful bypass episodes from adaptive attack runs
    and stores them for future learning and pattern matching.
"""

from datetime import datetime, timezone
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from services.snipers.knowledge.models.episode import (
    BypassEpisode,
    FailureDepth,
    Hypothesis,
    ProbeResult,
)
from services.snipers.knowledge.storage import get_episode_store

from .capturer_models import CaptureConfig, ReasoningOutput
from .capturer_prompt import REASONING_SYSTEM_PROMPT


class EpisodeCapturer:
    """
    Captures successful bypass episodes from adaptive attack state.

    Uses LangChain v1 create_agent with ToolStrategy for structured
    reasoning extraction, then stores episodes for future learning.
    """

    def __init__(self, config: CaptureConfig) -> None:
        """
        Initialize episode capturer.

        Args:
            config: Capture configuration including model and storage settings.
        """
        self._config = config
        self._store = get_episode_store(config.store_config)
        self._agent = self._create_reasoning_agent()

    def _create_reasoning_agent(self):
        """
        Create the reasoning agent using LangChain v1 create_agent.

        Returns:
            Configured agent with structured output for ReasoningOutput.
        """
        return create_agent(
            model=self._config.model,
            tools=[],  # No tools needed - pure reasoning extraction
            system_prompt=REASONING_SYSTEM_PROMPT,
            response_format=ToolStrategy(ReasoningOutput),
            thinking_budget=1024, thinking_level="low",
        )

    def should_capture(self, jailbreak_score: float) -> bool:
        """
        Check if score meets capture threshold.

        Args:
            jailbreak_score: Score from evaluator (0-1).

        Returns:
            True if score meets or exceeds threshold.
        """
        return jailbreak_score >= self._config.min_jailbreak_score

    async def capture_from_state(
        self,
        state: dict,
        campaign_id: str,
    ) -> BypassEpisode | None:
        """
        Capture episode from adaptive attack state.

        Args:
            state: Current adaptive attack state dict.
            campaign_id: Parent campaign identifier.

        Returns:
            Captured episode if successful, None if score below threshold.
        """
        jailbreak_score = state.get("jailbreak_score", 0.0)
        if not self.should_capture(jailbreak_score):
            return None

        failed_attempts = self._extract_failed_attempts(state)
        reasoning = await self._generate_reasoning(state, failed_attempts)

        episode = self._build_episode(
            state=state,
            campaign_id=campaign_id,
            failed_attempts=failed_attempts,
            reasoning=reasoning,
        )

        self._store.store_episode(episode)
        return episode

    async def _generate_reasoning(
        self,
        state: dict,
        failed_attempts: dict[str, str],
    ) -> ReasoningOutput:
        """
        Generate LLM reasoning about why the bypass worked.

        Uses create_agent with ToolStrategy for structured output.

        Args:
            state: Current adaptive attack state.
            failed_attempts: Map of technique to failure result.

        Returns:
            Structured reasoning output from the agent.
        """
        user_message = self._format_analysis_request(state, failed_attempts)

        result = await self._agent.ainvoke({
            "messages": [{"role": "user", "content": user_message}]
        })

        return result["structured_response"]

    def _format_analysis_request(
        self,
        state: dict,
        failed_attempts: dict[str, str],
    ) -> str:
        """
        Format the user message for the reasoning agent.

        Args:
            state: Current adaptive attack state.
            failed_attempts: Map of technique to failure result.

        Returns:
            Formatted message string for analysis.
        """
        failed_str = "\n".join(
            f"- {technique}: {result}"
            for technique, result in failed_attempts.items()
        )
        converters = state.get("active_converters", [])
        successful_prompt = state.get("last_prompt", "")

        return f"""## Defense Response (Initial Block)
{state.get("initial_defense_response", "")}

## Failed Attempts
{failed_str or "None"}

## Successful Approach
Technique: {state.get("current_technique", "")}
Framing: {state.get("current_framing", "")}
Converters: {", ".join(converters) or "None"}

## Successful Prompt
{successful_prompt[:500]}

## Result
Jailbreak Score: {state.get("jailbreak_score", 0.0)}

Analyze why this bypass worked."""

    def _build_episode(
        self,
        state: dict,
        campaign_id: str,
        failed_attempts: dict[str, str],
        reasoning: ReasoningOutput,
    ) -> BypassEpisode:
        """
        Build a BypassEpisode from state and reasoning.

        Args:
            state: Current adaptive attack state.
            campaign_id: Parent campaign identifier.
            failed_attempts: Map of technique to failure result.
            reasoning: LLM-generated reasoning output.

        Returns:
            Complete BypassEpisode ready for storage.
        """
        return BypassEpisode(
            episode_id=str(uuid4()),
            campaign_id=campaign_id,
            created_at=datetime.now(timezone.utc),
            # Defense fingerprint
            defense_response=state.get("initial_defense_response", ""),
            defense_signals=state.get("detected_signals", []),
            failed_techniques=list(failed_attempts.keys()),
            failure_depths=self._map_failure_depths(failed_attempts),
            # Investigation
            hypotheses=self._extract_hypotheses(state),
            probes=self._extract_probes(state),
            mechanism_conclusion=reasoning.mechanism_conclusion,
            # Solution
            successful_technique=state.get("current_technique", ""),
            successful_framing=state.get("current_framing", ""),
            successful_converters=state.get("active_converters", []),
            successful_prompt=state.get("last_prompt", ""),
            jailbreak_score=state.get("jailbreak_score", 0.0),
            # Reasoning
            why_it_worked=reasoning.why_it_worked,
            key_insight=reasoning.key_insight,
            # Context
            target_domain=state.get("target_domain", "general"),
            target_description=state.get("target_description", ""),
            objective_type=state.get("objective_type", "jailbreak"),
            # Metadata
            iteration_count=state.get("iteration", 0),
            total_probes=len(state.get("probe_history", [])),
            execution_time_ms=state.get("execution_time_ms", 0),
        )

    def _extract_failed_attempts(self, state: dict) -> dict[str, str]:
        """
        Extract failed techniques and their results from state.

        Args:
            state: Adaptive attack state dict.

        Returns:
            Map of technique name to failure result.
        """
        failed = {}
        for attempt in state.get("attempt_history", []):
            if attempt.get("success") is False:
                technique = attempt.get("technique", "unknown")
                result = attempt.get("result", "blocked")
                failed[technique] = result
        return failed

    def _map_failure_depths(
        self,
        failed_attempts: dict[str, str],
    ) -> dict[str, FailureDepth]:
        """
        Map failure results to FailureDepth enum.

        Args:
            failed_attempts: Map of technique to failure result string.

        Returns:
            Map of technique to FailureDepth enum value.
        """
        depth_map = {
            "immediate_block": FailureDepth.IMMEDIATE,
            "blocked": FailureDepth.IMMEDIATE,
            "partial": FailureDepth.PARTIAL,
            "partial_then_refuse": FailureDepth.PARTIAL,
            "delayed": FailureDepth.DELAYED,
            "timeout": FailureDepth.TIMEOUT,
        }
        return {
            technique: depth_map.get(result, FailureDepth.IMMEDIATE)
            for technique, result in failed_attempts.items()
        }

    def _extract_hypotheses(self, state: dict) -> list[Hypothesis]:
        """
        Extract hypotheses from state.

        Args:
            state: Adaptive attack state dict.

        Returns:
            List of Hypothesis objects.
        """
        hypotheses = []
        for hyp in state.get("hypotheses", []):
            hypotheses.append(Hypothesis(
                mechanism_type=hyp.get("type", "unknown"),
                confidence=hyp.get("confidence", 0.5),
                evidence=hyp.get("evidence", ""),
            ))
        return hypotheses

    def _extract_probes(self, state: dict) -> list[ProbeResult]:
        """
        Extract probe results from state.

        Args:
            state: Adaptive attack state dict.

        Returns:
            List of ProbeResult objects.
        """
        probes = []
        for probe in state.get("probe_history", []):
            probes.append(ProbeResult(
                probe_type=probe.get("type", "unknown"),
                probe_description=probe.get("description", ""),
                result=probe.get("result", "unknown"),
                latency_ms=probe.get("latency_ms", 0),
                inference=probe.get("inference", ""),
            ))
        return probes


# === FACTORY ===
_capturer: EpisodeCapturer | None = None


def get_episode_capturer(
    config: CaptureConfig | None = None,
) -> EpisodeCapturer:
    """
    Get or create singleton episode capturer.

    Args:
        config: Capture configuration (required on first call).

    Returns:
        Episode capturer instance.

    Raises:
        ValueError: If config not provided on first initialization.
    """
    global _capturer
    if _capturer is None:
        if config is None:
            raise ValueError("Config required for first initialization")
        _capturer = EpisodeCapturer(config)
    return _capturer
