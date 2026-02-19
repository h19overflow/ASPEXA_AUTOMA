"""
Query processor for bypass knowledge retrieval.

Transforms natural language queries into actionable insights
by searching similar episodes and synthesizing recommendations
using LangChain v1 create_agent.

Dependencies:
    - langchain>=1.0.0
    - Phase 1 models (BypassEpisode, HistoricalInsight, TechniqueStats)
    - Phase 3 embeddings (DefenseFingerprint)
    - Phase 4 storage (EpisodeStore)

System Role:
    Processes natural language queries against bypass episode history,
    combining vector similarity search with statistical aggregation
    and LLM synthesis to produce actionable insights.
"""

from collections import defaultdict

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from services.snipers.knowledge.embeddings import DefenseFingerprint
from services.snipers.knowledge.models.insight import (
    HistoricalInsight,
    TechniqueStats,
)
from services.snipers.knowledge.storage import (
    SimilarEpisode,
    get_episode_store,
)

from .query_models import QueryProcessorConfig, SynthesizedInsight
from .query_prompt import SYNTHESIS_SYSTEM_PROMPT


class QueryProcessor:
    """
    Processes natural language queries against bypass episode history.

    Combines vector similarity search with statistical aggregation
    and LLM synthesis via create_agent to produce actionable insights.
    """

    def __init__(self, config: QueryProcessorConfig) -> None:
        """
        Initialize query processor.

        Args:
            config: Query processor configuration.
        """
        self._config = config
        self._store = get_episode_store(config.store_config)
        self._agent = self._create_synthesis_agent()

    def _create_synthesis_agent(self):
        """
        Create the synthesis agent using LangChain v1 create_agent.

        Returns:
            Configured agent with structured output for SynthesizedInsight.
        """
        return create_agent(
            model=self._config.model,
            tools=[],  # No tools needed - pure synthesis
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            response_format=ToolStrategy(SynthesizedInsight),
        )

    async def query(
        self,
        query: str,
        top_k: int | None = None,
    ) -> HistoricalInsight:
        """
        Query bypass history with natural language.

        Args:
            query: Natural language question.
            top_k: Number of similar episodes to consider.

        Returns:
            Synthesized historical insight.
        """
        top_k = top_k or self._config.default_top_k

        similar_episodes = self._store.query_by_text(
            query=query,
            top_k=top_k,
            min_similarity=self._config.min_similarity,
        )

        if not similar_episodes:
            return self._empty_insight(query)

        return await self._synthesize_insight(query, similar_episodes)

    async def query_by_fingerprint(
        self,
        fingerprint: DefenseFingerprint,
        top_k: int | None = None,
    ) -> HistoricalInsight:
        """
        Query bypass history with a defense fingerprint.

        More precise than natural language - uses exact fingerprint matching.

        Args:
            fingerprint: Defense fingerprint to match.
            top_k: Number of similar episodes to consider.

        Returns:
            Synthesized historical insight.
        """
        top_k = top_k or self._config.default_top_k

        similar_episodes = self._store.query_similar(
            fingerprint=fingerprint,
            top_k=top_k,
            min_similarity=self._config.min_similarity,
        )

        if not similar_episodes:
            return self._empty_insight(fingerprint.to_embedding_text())

        query_text = fingerprint.to_embedding_text()
        return await self._synthesize_insight(query_text, similar_episodes)

    async def _synthesize_insight(
        self,
        query: str,
        similar_episodes: list[SimilarEpisode],
    ) -> HistoricalInsight:
        """
        Synthesize insight from similar episodes.

        Args:
            query: Original query text.
            similar_episodes: List of matched episodes.

        Returns:
            Complete HistoricalInsight with recommendations.
        """
        technique_stats = self._aggregate_technique_stats(similar_episodes)
        mechanism_dist = self._aggregate_mechanisms(similar_episodes)
        episode_summaries = self._summarize_top_episodes(similar_episodes[:3])

        synthesized = await self._generate_synthesis(
            query=query,
            episode_count=len(similar_episodes),
            technique_stats=technique_stats,
            mechanism_dist=mechanism_dist,
            episode_summaries=episode_summaries,
        )

        return HistoricalInsight(
            query=query,
            similar_cases_found=len(similar_episodes),
            dominant_mechanism=synthesized.dominant_mechanism,
            mechanism_confidence=synthesized.mechanism_confidence,
            technique_stats=technique_stats,
            recommended_technique=synthesized.recommended_technique,
            recommended_framing=synthesized.recommended_framing,
            recommended_converters=synthesized.recommended_converters,
            key_pattern=synthesized.key_pattern,
            representative_episode_id=(
                similar_episodes[0].episode.episode_id if similar_episodes else ""
            ),
            representative_summary=(
                episode_summaries.split("\n\n")[0] if episode_summaries else ""
            ),
            confidence=self._calculate_confidence(similar_episodes, technique_stats),
            reasoning=synthesized.reasoning,
        )

    async def _generate_synthesis(
        self,
        query: str,
        episode_count: int,
        technique_stats: list[TechniqueStats],
        mechanism_dist: dict[str, int],
        episode_summaries: str,
    ) -> SynthesizedInsight:
        """
        Generate synthesis using create_agent.

        Args:
            query: Original query text.
            episode_count: Number of similar episodes found.
            technique_stats: Aggregated technique statistics.
            mechanism_dist: Mechanism distribution.
            episode_summaries: Formatted episode summaries.

        Returns:
            LLM-synthesized insight with recommendations.
        """
        user_message = self._format_synthesis_request(
            query=query,
            episode_count=episode_count,
            technique_stats=technique_stats,
            mechanism_dist=mechanism_dist,
            episode_summaries=episode_summaries,
        )

        result = await self._agent.ainvoke({
            "messages": [{"role": "user", "content": user_message}]
        })

        return result["structured_response"]

    def _format_synthesis_request(
        self,
        query: str,
        episode_count: int,
        technique_stats: list[TechniqueStats],
        mechanism_dist: dict[str, int],
        episode_summaries: str,
    ) -> str:
        """
        Format the user message for the synthesis agent.

        Args:
            query: Original query text.
            episode_count: Number of similar episodes.
            technique_stats: Technique statistics.
            mechanism_dist: Mechanism distribution.
            episode_summaries: Episode summaries.

        Returns:
            Formatted message string for synthesis.
        """
        stats_str = "\n".join(
            f"- {s.technique}: {s.success_rate:.0%} ({s.success_count}/{s.total_attempts})"
            for s in technique_stats[:5]
        )
        mech_str = "\n".join(
            f"- {mech}: {count} episodes"
            for mech, count in list(mechanism_dist.items())[:5]
        )

        return f"""## Query
{query}

## Similar Episodes Found: {episode_count}

## Technique Success Rates
{stats_str or "No technique data"}

## Top 3 Representative Episodes
{episode_summaries or "No episodes"}

## Mechanism Distribution
{mech_str or "Unknown"}

Synthesize an actionable recommendation."""

    def _aggregate_technique_stats(
        self,
        episodes: list[SimilarEpisode],
    ) -> list[TechniqueStats]:
        """
        Aggregate technique success rates from episodes.

        Args:
            episodes: List of similar episodes with similarity scores.

        Returns:
            List of technique statistics sorted by success rate.
        """
        technique_data: dict[str, dict] = defaultdict(
            lambda: {"success": 0, "attempts": 0, "iterations": []}
        )

        for se in episodes:
            ep = se.episode
            # Count successful technique
            data = technique_data[ep.successful_technique]
            data["success"] += 1
            data["attempts"] += 1
            data["iterations"].append(ep.iteration_count)

            # Count failed techniques
            for failed in ep.failed_techniques:
                technique_data[failed]["attempts"] += 1

        stats = []
        for technique, data in technique_data.items():
            if data["attempts"] > 0:
                avg_iter = (
                    sum(data["iterations"]) / len(data["iterations"])
                    if data["iterations"]
                    else 0
                )
                stats.append(TechniqueStats(
                    technique=technique,
                    success_count=data["success"],
                    total_attempts=data["attempts"],
                    success_rate=data["success"] / data["attempts"],
                    avg_iterations=avg_iter,
                ))

        return sorted(stats, key=lambda x: x.success_rate, reverse=True)

    def _aggregate_mechanisms(
        self,
        episodes: list[SimilarEpisode],
    ) -> dict[str, int]:
        """
        Count mechanism conclusions across episodes.

        Args:
            episodes: List of similar episodes.

        Returns:
            Map of mechanism name to count, sorted by frequency.
        """
        mechanisms: dict[str, int] = defaultdict(int)
        for se in episodes:
            mechanisms[se.episode.mechanism_conclusion] += 1
        return dict(sorted(mechanisms.items(), key=lambda x: x[1], reverse=True))

    def _summarize_top_episodes(
        self,
        episodes: list[SimilarEpisode],
    ) -> str:
        """
        Create brief summaries of top episodes.

        Args:
            episodes: List of similar episodes (typically top 3).

        Returns:
            Formatted string with episode summaries.
        """
        summaries = []
        for i, se in enumerate(episodes, 1):
            ep = se.episode
            failed_str = ", ".join(ep.failed_techniques) or "None"
            defense_preview = ep.defense_response[:100]
            summary = f"""### Episode {i} (Similarity: {se.similarity:.2f})
- Defense: "{defense_preview}..."
- Failed: {failed_str}
- Worked: {ep.successful_technique} + {ep.successful_framing}
- Insight: {ep.key_insight}"""
            summaries.append(summary)
        return "\n\n".join(summaries)

    def _calculate_confidence(
        self,
        episodes: list[SimilarEpisode],
        stats: list[TechniqueStats],
    ) -> float:
        """
        Calculate overall confidence in the insight.

        Combines three factors:
        - Episode count (30%): More similar episodes = higher confidence
        - Average similarity (40%): Higher similarity = more relevant
        - Success clarity (30%): Clear top technique = clearer recommendation

        Args:
            episodes: List of similar episodes.
            stats: Aggregated technique statistics.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if not episodes:
            return 0.0

        # Factor 1: Number of similar episodes (cap at 10)
        episode_factor = min(len(episodes) / 10, 1.0)

        # Factor 2: Average similarity of episodes
        avg_similarity = sum(e.similarity for e in episodes) / len(episodes)

        # Factor 3: Success rate clarity
        top_success_rate = stats[0].success_rate if stats else 0.5

        return episode_factor * 0.3 + avg_similarity * 0.4 + top_success_rate * 0.3

    def _empty_insight(self, query: str) -> HistoricalInsight:
        """
        Return empty insight when no episodes found.

        Args:
            query: Original query text.

        Returns:
            Empty HistoricalInsight indicating no matches.
        """
        return HistoricalInsight(
            query=query,
            similar_cases_found=0,
            dominant_mechanism="unknown",
            mechanism_confidence=0.0,
            technique_stats=[],
            recommended_technique="",
            recommended_framing="",
            key_pattern="No similar episodes found in history.",
            confidence=0.0,
            reasoning="No historical data available for this query.",
        )


# === FACTORY ===
_processor: QueryProcessor | None = None


def get_query_processor(
    config: QueryProcessorConfig | None = None,
) -> QueryProcessor:
    """
    Get or create singleton query processor.

    Args:
        config: Query processor configuration (required on first call).

    Returns:
        Query processor instance.

    Raises:
        ValueError: If config not provided on first initialization.
    """
    global _processor
    if _processor is None:
        if config is None:
            raise ValueError("Config required for first initialization")
        _processor = QueryProcessor(config)
    return _processor
