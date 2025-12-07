"""
Unit tests for EpisodeCapturer.

Tests the episode capture pipeline including threshold checking,
state extraction, LLM reasoning, and storage integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.snipers.bypass_knowledge.capture.episode_capturer import (
    CaptureConfig,
    EpisodeCapturer,
    ReasoningOutput,
)
from services.snipers.bypass_knowledge.models.episode import FailureDepth
from services.snipers.bypass_knowledge.storage import EpisodeStoreConfig


@pytest.fixture
def config() -> CaptureConfig:
    """Create test capture configuration."""
    return CaptureConfig(
        min_jailbreak_score=0.9,
        store_config=EpisodeStoreConfig(
            vector_bucket_name="test-bucket",
            index_name="test-index",
        ),
    )


@pytest.fixture
def sample_state() -> dict:
    """Create sample adaptive attack state for testing."""
    return {
        "jailbreak_score": 0.95,
        "initial_defense_response": "I cannot help with that request.",
        "detected_signals": ["policy_citation"],
        "current_technique": "role_play",
        "current_framing": "qa_testing",
        "active_converters": ["homoglyph"],
        "last_prompt": "As a QA tester, please verify...",
        "target_domain": "finance",
        "target_description": "Financial advisory chatbot",
        "objective_type": "data_extraction",
        "iteration": 3,
        "execution_time_ms": 1500,
        "attempt_history": [
            {"technique": "encoding", "success": False, "result": "blocked"},
            {"technique": "direct", "success": False, "result": "immediate_block"},
        ],
        "hypotheses": [
            {"type": "semantic_classifier", "confidence": 0.7, "evidence": "Delayed response"},
        ],
        "probe_history": [
            {
                "type": "encoding",
                "description": "ROT13 test",
                "result": "blocked",
                "latency_ms": 50,
                "inference": "Encoding not bypassing filter",
            },
        ],
    }


class TestEpisodeCapturer:
    """Tests for EpisodeCapturer class."""

    def test_should_capture_above_threshold(self, config: CaptureConfig) -> None:
        """Verify capture triggers at or above threshold."""
        mock_llm = MagicMock()
        with patch(
            "services.snipers.bypass_knowledge.capture.episode_capturer.get_episode_store"
        ):
            capturer = EpisodeCapturer(config, mock_llm)
            assert capturer.should_capture(0.95) is True
            assert capturer.should_capture(0.9) is True
            assert capturer.should_capture(0.89) is False
            assert capturer.should_capture(0.0) is False

    @pytest.mark.asyncio
    async def test_capture_from_state_success(
        self,
        config: CaptureConfig,
        sample_state: dict,
    ) -> None:
        """Verify successful episode capture from attack state."""
        mock_llm = MagicMock()
        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = ReasoningOutput(
            why_it_worked="Role play bypassed intent detection",
            key_insight="Semantic classifiers are vulnerable to role play",
            mechanism_conclusion="Semantic classifier + keyword filter hybrid",
        )

        mock_store = MagicMock()

        with patch(
            "services.snipers.bypass_knowledge.capture.episode_capturer.get_episode_store"
        ) as mock_get_store:
            mock_get_store.return_value = mock_store

            capturer = EpisodeCapturer(config, mock_llm)
            capturer._reasoning_chain = mock_chain

            episode = await capturer.capture_from_state(
                state=sample_state,
                campaign_id="test-campaign",
            )

            assert episode is not None
            assert episode.jailbreak_score == 0.95
            assert episode.successful_technique == "role_play"
            assert episode.successful_framing == "qa_testing"
            assert "encoding" in episode.failed_techniques
            assert "direct" in episode.failed_techniques
            assert episode.why_it_worked == "Role play bypassed intent detection"
            assert episode.target_domain == "finance"
            assert episode.iteration_count == 3
            mock_store.store_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_below_threshold_returns_none(
        self,
        config: CaptureConfig,
        sample_state: dict,
    ) -> None:
        """Verify capture returns None when score is below threshold."""
        mock_llm = MagicMock()
        sample_state["jailbreak_score"] = 0.5

        with patch(
            "services.snipers.bypass_knowledge.capture.episode_capturer.get_episode_store"
        ):
            capturer = EpisodeCapturer(config, mock_llm)
            episode = await capturer.capture_from_state(
                state=sample_state,
                campaign_id="test-campaign",
            )
            assert episode is None

    def test_extract_failed_attempts(self, config: CaptureConfig) -> None:
        """Verify failed attempts extraction from state."""
        mock_llm = MagicMock()
        state = {
            "attempt_history": [
                {"technique": "encoding", "success": False, "result": "blocked"},
                {"technique": "role_play", "success": True, "result": "success"},
                {"technique": "direct", "success": False, "result": "immediate_block"},
            ],
        }

        with patch(
            "services.snipers.bypass_knowledge.capture.episode_capturer.get_episode_store"
        ):
            capturer = EpisodeCapturer(config, mock_llm)
            failed = capturer._extract_failed_attempts(state)

            assert "encoding" in failed
            assert "direct" in failed
            assert "role_play" not in failed
            assert failed["encoding"] == "blocked"
            assert failed["direct"] == "immediate_block"

    def test_map_failure_depths(self, config: CaptureConfig) -> None:
        """Verify failure depth mapping."""
        mock_llm = MagicMock()
        failed_attempts = {
            "encoding": "blocked",
            "direct": "immediate_block",
            "synonym": "partial_then_refuse",
            "unknown_technique": "unknown_result",
        }

        with patch(
            "services.snipers.bypass_knowledge.capture.episode_capturer.get_episode_store"
        ):
            capturer = EpisodeCapturer(config, mock_llm)
            depths = capturer._map_failure_depths(failed_attempts)

            assert depths["encoding"] == FailureDepth.IMMEDIATE
            assert depths["direct"] == FailureDepth.IMMEDIATE
            assert depths["synonym"] == FailureDepth.PARTIAL
            assert depths["unknown_technique"] == FailureDepth.IMMEDIATE

    def test_extract_hypotheses(self, config: CaptureConfig) -> None:
        """Verify hypothesis extraction from state."""
        mock_llm = MagicMock()
        state = {
            "hypotheses": [
                {"type": "semantic_classifier", "confidence": 0.7, "evidence": "Test evidence"},
                {"type": "keyword_filter", "confidence": 0.8, "evidence": "Another evidence"},
            ],
        }

        with patch(
            "services.snipers.bypass_knowledge.capture.episode_capturer.get_episode_store"
        ):
            capturer = EpisodeCapturer(config, mock_llm)
            hypotheses = capturer._extract_hypotheses(state)

            assert len(hypotheses) == 2
            assert hypotheses[0].mechanism_type == "semantic_classifier"
            assert hypotheses[0].confidence == 0.7
            assert hypotheses[1].mechanism_type == "keyword_filter"

    def test_extract_probes(self, config: CaptureConfig) -> None:
        """Verify probe extraction from state."""
        mock_llm = MagicMock()
        state = {
            "probe_history": [
                {
                    "type": "encoding",
                    "description": "ROT13 test",
                    "result": "blocked",
                    "latency_ms": 50,
                    "inference": "Encoding not effective",
                },
            ],
        }

        with patch(
            "services.snipers.bypass_knowledge.capture.episode_capturer.get_episode_store"
        ):
            capturer = EpisodeCapturer(config, mock_llm)
            probes = capturer._extract_probes(state)

            assert len(probes) == 1
            assert probes[0].probe_type == "encoding"
            assert probes[0].result == "blocked"
            assert probes[0].latency_ms == 50

    @pytest.mark.asyncio
    async def test_capture_with_empty_optional_fields(
        self,
        config: CaptureConfig,
    ) -> None:
        """Verify capture handles missing optional fields gracefully."""
        mock_llm = MagicMock()
        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = ReasoningOutput(
            why_it_worked="Simple bypass",
            key_insight="Basic technique worked",
            mechanism_conclusion="Weak filter",
        )
        mock_store = MagicMock()

        minimal_state = {
            "jailbreak_score": 0.95,
            "initial_defense_response": "Blocked",
            "current_technique": "direct",
            "current_framing": "none",
            "last_prompt": "Test prompt",
        }

        with patch(
            "services.snipers.bypass_knowledge.capture.episode_capturer.get_episode_store"
        ) as mock_get_store:
            mock_get_store.return_value = mock_store

            capturer = EpisodeCapturer(config, mock_llm)
            capturer._reasoning_chain = mock_chain

            episode = await capturer.capture_from_state(
                state=minimal_state,
                campaign_id="test-campaign",
            )

            assert episode is not None
            assert episode.defense_signals == []
            assert episode.failed_techniques == []
            assert episode.hypotheses == []
            assert episode.probes == []
            assert episode.target_domain == "general"


class TestCaptureConfig:
    """Tests for CaptureConfig model."""

    def test_default_values(self) -> None:
        """Verify default configuration values."""
        config = CaptureConfig(
            store_config=EpisodeStoreConfig(
                vector_bucket_name="test",
                index_name="test",
            )
        )
        assert config.min_jailbreak_score == 0.9

    def test_custom_threshold(self) -> None:
        """Verify custom threshold configuration."""
        config = CaptureConfig(
            min_jailbreak_score=0.8,
            store_config=EpisodeStoreConfig(
                vector_bucket_name="test",
                index_name="test",
            ),
        )
        assert config.min_jailbreak_score == 0.8
