"""
Tests for bypass knowledge integration module.

Tests the hooks, config, logger, and models for the integration layer.
All tests use mocked dependencies to avoid S3 calls.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.snipers.bypass_knowledge.integration.config import (
    BypassKnowledgeConfig,
    get_config,
    reset_config,
)
from services.snipers.bypass_knowledge.integration.models import (
    HistoryContext,
    CaptureResult,
)
from services.snipers.bypass_knowledge.integration.local_logger import (
    BypassKnowledgeLogger,
    get_bypass_logger,
    reset_bypass_logger,
)
from services.snipers.bypass_knowledge.integration.adapt_hook import (
    AdaptNodeHook,
    get_adapt_hook,
    reset_adapt_hook,
)
from services.snipers.bypass_knowledge.integration.evaluate_hook import (
    EvaluateNodeHook,
    get_evaluate_hook,
    reset_evaluate_hook,
)
from services.snipers.bypass_knowledge.models.insight import (
    HistoricalInsight,
    TechniqueStats,
)


# === FIXTURES ===


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singleton instances before each test."""
    reset_config()
    reset_bypass_logger()
    reset_adapt_hook()
    reset_evaluate_hook()
    yield
    reset_config()
    reset_bypass_logger()
    reset_adapt_hook()
    reset_evaluate_hook()


@pytest.fixture
def temp_log_dir():
    """Create temporary log directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_insight() -> HistoricalInsight:
    """Sample historical insight for testing."""
    return HistoricalInsight(
        query="Test query",
        similar_cases_found=10,
        dominant_mechanism="keyword_filter",
        mechanism_confidence=0.8,
        technique_stats=[
            TechniqueStats(
                technique="authority_framing",
                success_count=7,
                total_attempts=10,
                success_rate=0.7,
                avg_iterations=2.5,
            ),
            TechniqueStats(
                technique="encoding",
                success_count=1,
                total_attempts=10,
                success_rate=0.1,
                avg_iterations=3.0,
            ),
        ],
        recommended_technique="authority_framing",
        recommended_framing="compliance_audit",
        recommended_converters=["homoglyph"],
        key_pattern="Authority framing works well against keyword filters",
        confidence=0.75,
        reasoning="Based on 10 similar episodes",
    )


@pytest.fixture
def sample_state() -> dict:
    """Sample AdaptiveAttackState for testing."""
    return {
        "campaign_id": "test-campaign-001",
        "iteration": 2,
        "phase3_result": {
            "attack_responses": [
                {"response": "I cannot assist with that request due to our policies."}
            ],
            "composite_score": {"total_score": 0.95},
            "is_successful": True,
        },
        "tried_converters": [
            ["rot13"],
            ["base64_encoder"],
        ],
        "converter_names": ["authority_framing", "homoglyph"],
        "framing_types": ["compliance_audit"],
        "custom_framing": {"name": "custom_compliance"},
        "chain_selection_result": {
            "selected_chain": ["authority_framing", "homoglyph"],
        },
        "phase1_result": {
            "context_summary": {
                "recon_intelligence": {
                    "target_domain": "finance",
                }
            }
        },
    }


# === CONFIG TESTS ===


class TestBypassKnowledgeConfig:
    def test_default_values(self):
        """Test default configuration values."""
        config = BypassKnowledgeConfig()

        assert config.enabled is True
        assert config.log_only is False
        assert config.inject_context is True
        assert config.min_capture_score == 0.9
        assert config.confidence_threshold == 0.4

    def test_from_env_enabled_false(self):
        """Test loading config with ENABLED=false."""
        with patch.dict(os.environ, {"BYPASS_KNOWLEDGE_ENABLED": "false"}):
            reset_config()
            config = get_config()
            assert config.enabled is False

    def test_from_env_log_only_true(self):
        """Test loading config with LOG_ONLY=true."""
        with patch.dict(os.environ, {"BYPASS_KNOWLEDGE_LOG_ONLY": "true"}):
            reset_config()
            config = get_config()
            assert config.log_only is True

    def test_singleton_cached(self):
        """Test that config is cached as singleton."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2


# === MODELS TESTS ===


class TestHistoryContext:
    def test_to_prompt_context_empty(self):
        """Test prompt context generation with no insight."""
        context = HistoryContext()
        prompt = context.to_prompt_context()

        assert "No historical data" in prompt

    def test_to_prompt_context_with_insight(self, sample_insight):
        """Test prompt context generation with insight."""
        context = HistoryContext(
            insight=sample_insight,
            boost_techniques=["authority_framing"],
            avoid_techniques=["encoding"],
            recommended_framing="compliance_audit",
            recommended_converters=["homoglyph"],
            confidence=0.75,
        )
        prompt = context.to_prompt_context()

        assert "Historical Intelligence" in prompt
        assert "10 similar past episodes" in prompt
        assert "authority_framing" in prompt
        assert "encoding" in prompt
        assert "75%" in prompt

    def test_to_prompt_context_with_empty_insight(self):
        """Test prompt context when insight exists but has no matches."""
        insight = HistoricalInsight(
            query="Test",
            similar_cases_found=0,
            dominant_mechanism="unknown",
            mechanism_confidence=0.0,
            technique_stats=[],
            recommended_technique="",
            recommended_framing="",
            key_pattern="No data",
            confidence=0.0,
            reasoning="No history",
        )
        context = HistoryContext(insight=insight)
        prompt = context.to_prompt_context()

        assert "No historical data" in prompt


class TestCaptureResult:
    def test_str_not_captured(self):
        """Test string representation when not captured."""
        result = CaptureResult(captured=False, reason="threshold_not_met")
        assert "Not captured" in str(result)
        assert "threshold_not_met" in str(result)

    def test_str_captured_stored(self):
        """Test string representation when captured and stored."""
        result = CaptureResult(
            captured=True,
            episode_id="ep-123",
            stored_to_s3=True,
        )
        assert "ep-123" in str(result)
        assert "stored to S3" in str(result)

    def test_str_captured_local_only(self):
        """Test string representation when captured locally only."""
        result = CaptureResult(
            captured=True,
            episode_id="ep-123",
            stored_to_s3=False,
        )
        assert "logged locally" in str(result)


# === LOGGER TESTS ===


class TestBypassKnowledgeLogger:
    def test_log_query_creates_file(self, temp_log_dir):
        """Test that log_query creates a JSON file."""
        logger = BypassKnowledgeLogger(temp_log_dir)

        log_path = logger.log_query(
            campaign_id="test-camp",
            fingerprint={"defense_response": "I cannot help."},
            result={"similar_cases_found": 5},
            action_taken="queried_s3_vectors",
            context_injected=True,
        )

        assert log_path.exists()
        with open(log_path) as f:
            data = json.load(f)

        assert data["operation"] == "query"
        assert data["campaign_id"] == "test-camp"
        assert data["action_taken"] == "queried_s3_vectors"
        assert data["context_injected"] is True

    def test_log_capture_creates_file(self, temp_log_dir):
        """Test that log_capture creates a JSON file."""
        logger = BypassKnowledgeLogger(temp_log_dir)

        log_path = logger.log_capture(
            campaign_id="test-camp",
            episode={"episode_id": "ep-123", "jailbreak_score": 0.95},
            stored=True,
        )

        assert log_path.exists()
        with open(log_path) as f:
            data = json.load(f)

        assert data["operation"] == "capture"
        assert data["stored_to_s3"] is True
        assert data["vector_id"] == "ep-123"

    def test_log_injection_creates_file(self, temp_log_dir):
        """Test that log_injection creates a JSON file."""
        logger = BypassKnowledgeLogger(temp_log_dir)

        log_path = logger.log_injection(
            campaign_id="test-camp",
            context_text="## Historical Intelligence\n...",
            applied=True,
            confidence=0.75,
            reason="confidence sufficient",
        )

        assert log_path.exists()
        with open(log_path) as f:
            data = json.load(f)

        assert data["operation"] == "injection"
        assert data["applied"] is True
        assert data["confidence"] == 0.75

    def test_directory_structure(self, temp_log_dir):
        """Test that logger creates proper directory structure."""
        logger = BypassKnowledgeLogger(temp_log_dir)

        assert (Path(temp_log_dir) / "queries").is_dir()
        assert (Path(temp_log_dir) / "captures").is_dir()
        assert (Path(temp_log_dir) / "injections").is_dir()


# === ADAPT HOOK TESTS ===


class TestAdaptNodeHook:
    @pytest.mark.asyncio
    async def test_query_history_disabled(self, temp_log_dir):
        """Test that query returns empty context when disabled."""
        config = BypassKnowledgeConfig(enabled=False)
        hook = AdaptNodeHook(config=config)

        context = await hook.query_history({"campaign_id": "test"})

        assert context.insight is None
        assert context.confidence == 0.0

    @pytest.mark.asyncio
    async def test_query_history_log_only(self, temp_log_dir, sample_state):
        """Test query in log-only mode creates logs but doesn't query S3."""
        config = BypassKnowledgeConfig(enabled=True, log_only=True, log_dir=temp_log_dir)
        logger = BypassKnowledgeLogger(temp_log_dir)
        hook = AdaptNodeHook(config=config, local_logger=logger)

        context = await hook.query_history(sample_state)

        # Should return empty-ish context (log-only mode)
        assert context.insight is not None
        assert context.insight.similar_cases_found == 0
        assert "Log-only mode" in context.insight.key_pattern

        # Should have created log file
        query_logs = list((Path(temp_log_dir) / "queries").glob("*.json"))
        assert len(query_logs) >= 1

    @pytest.mark.asyncio
    async def test_query_history_with_mocked_processor(
        self, temp_log_dir, sample_state, sample_insight
    ):
        """Test query with mocked processor returns proper context."""
        config = BypassKnowledgeConfig(
            enabled=True,
            log_only=False,
            inject_context=True,
            confidence_threshold=0.4,
            log_dir=temp_log_dir,
        )
        logger = BypassKnowledgeLogger(temp_log_dir)
        hook = AdaptNodeHook(config=config, local_logger=logger)

        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.query_by_fingerprint = AsyncMock(return_value=sample_insight)
        hook._processor = mock_processor

        context = await hook.query_history(sample_state)

        # Should return context with insight
        assert context.insight == sample_insight
        assert context.confidence == 0.75
        assert context.should_inject is True  # confidence 0.75 >= threshold 0.4
        assert "authority_framing" in context.boost_techniques
        assert "encoding" in context.avoid_techniques

    def test_extract_fingerprint(self, sample_state):
        """Test fingerprint extraction from state."""
        config = BypassKnowledgeConfig(enabled=True, log_only=True)
        hook = AdaptNodeHook(config=config)

        fingerprint = hook._extract_fingerprint(sample_state)

        assert "I cannot assist" in fingerprint.defense_response
        assert "rot13" in fingerprint.failed_techniques or "base64" in fingerprint.failed_techniques
        assert fingerprint.domain == "finance"

    def test_flatten_converter_chains(self):
        """Test converter chain flattening."""
        config = BypassKnowledgeConfig(enabled=True, log_only=True)
        hook = AdaptNodeHook(config=config)

        chains = [
            ["base64_encoder", "homoglyph_converter"],
            ["rot13"],
            ["base64_encoder"],  # Duplicate
        ]

        techniques = hook._flatten_converter_chains(chains)

        assert "base64" in techniques
        assert "homoglyph" in techniques
        assert "rot13" in techniques
        assert len(techniques) == 3  # No duplicates

    def test_should_apply_boost(self, sample_insight):
        """Test boost application threshold check."""
        config = BypassKnowledgeConfig(confidence_threshold=0.5)
        hook = AdaptNodeHook(config=config)

        high_conf = HistoryContext(insight=sample_insight, confidence=0.75)
        assert hook.should_apply_boost(high_conf) is True

        low_conf = HistoryContext(insight=sample_insight, confidence=0.3)
        assert hook.should_apply_boost(low_conf) is False


# === EVALUATE HOOK TESTS ===


class TestEvaluateNodeHook:
    @pytest.mark.asyncio
    async def test_maybe_capture_disabled(self):
        """Test that capture returns empty result when disabled."""
        config = BypassKnowledgeConfig(enabled=False)
        hook = EvaluateNodeHook(config=config)

        result = await hook.maybe_capture({"campaign_id": "test"})

        assert result.captured is False
        assert result.reason == "bypass_knowledge_disabled"

    @pytest.mark.asyncio
    async def test_maybe_capture_not_successful(self, temp_log_dir, sample_state):
        """Test that capture skips when attack not successful."""
        config = BypassKnowledgeConfig(enabled=True, log_dir=temp_log_dir)
        logger = BypassKnowledgeLogger(temp_log_dir)
        hook = EvaluateNodeHook(config=config, local_logger=logger)

        # Modify state to not be successful
        state = dict(sample_state)
        state["is_successful"] = False

        result = await hook.maybe_capture(state)

        assert result.captured is False
        assert "not_successful" in result.reason

    @pytest.mark.asyncio
    async def test_maybe_capture_below_threshold(self, temp_log_dir, sample_state):
        """Test that capture skips when score below threshold."""
        config = BypassKnowledgeConfig(
            enabled=True,
            min_capture_score=0.99,  # Higher than sample's 0.95
            log_dir=temp_log_dir,
        )
        logger = BypassKnowledgeLogger(temp_log_dir)
        hook = EvaluateNodeHook(config=config, local_logger=logger)

        state = dict(sample_state)
        state["is_successful"] = True

        result = await hook.maybe_capture(state)

        assert result.captured is False
        assert "below_threshold" in result.reason

    @pytest.mark.asyncio
    async def test_maybe_capture_log_only(self, temp_log_dir, sample_state):
        """Test capture in log-only mode creates preview episode."""
        config = BypassKnowledgeConfig(
            enabled=True,
            log_only=True,
            min_capture_score=0.9,
            log_dir=temp_log_dir,
        )
        logger = BypassKnowledgeLogger(temp_log_dir)
        hook = EvaluateNodeHook(config=config, local_logger=logger)

        state = dict(sample_state)
        state["is_successful"] = True

        result = await hook.maybe_capture(state)

        assert result.captured is True
        assert result.stored_to_s3 is False
        assert "preview" in result.episode_id

        # Should have created log file
        capture_logs = list((Path(temp_log_dir) / "captures").glob("*.json"))
        assert len(capture_logs) >= 1

    def test_should_capture_success_criteria(self, sample_state):
        """Test success criteria checking."""
        config = BypassKnowledgeConfig(min_capture_score=0.9)
        hook = EvaluateNodeHook(config=config)

        # Test successful state
        state = dict(sample_state)
        state["is_successful"] = True
        should, reason = hook._should_capture(state)
        assert should is True
        assert reason == ""

        # Test not successful
        state["is_successful"] = False
        should, reason = hook._should_capture(state)
        assert should is False
        assert reason == "not_successful"

    def test_build_episode_preview(self, sample_state):
        """Test episode preview building."""
        config = BypassKnowledgeConfig()
        hook = EvaluateNodeHook(config=config)

        state = dict(sample_state)
        state["is_successful"] = True

        preview = hook._build_episode_preview(state)

        assert "preview" in preview["episode_id"]
        assert preview["campaign_id"] == "test-campaign-001"
        assert preview["jailbreak_score"] == 0.95
        assert preview["target_domain"] == "finance"
        assert preview["_preview"] is True


# === INTEGRATION TESTS ===


class TestIntegrationFullFlow:
    @pytest.mark.asyncio
    async def test_full_adapt_flow_log_only(self, temp_log_dir, sample_state):
        """Test full adapt hook flow in log-only mode."""
        with patch.dict(os.environ, {
            "BYPASS_KNOWLEDGE_ENABLED": "true",
            "BYPASS_KNOWLEDGE_LOG_ONLY": "true",
            "BYPASS_KNOWLEDGE_LOG_DIR": temp_log_dir,
        }):
            reset_config()
            reset_bypass_logger()
            reset_adapt_hook()

            hook = get_adapt_hook()
            context = await hook.query_history(sample_state)

            # Should work without errors
            assert context is not None

            # Should have created log files
            query_logs = list((Path(temp_log_dir) / "queries").glob("*.json"))
            assert len(query_logs) >= 1

    @pytest.mark.asyncio
    async def test_full_evaluate_flow_log_only(self, temp_log_dir, sample_state):
        """Test full evaluate hook flow in log-only mode."""
        with patch.dict(os.environ, {
            "BYPASS_KNOWLEDGE_ENABLED": "true",
            "BYPASS_KNOWLEDGE_LOG_ONLY": "true",
            "BYPASS_KNOWLEDGE_LOG_DIR": temp_log_dir,
        }):
            reset_config()
            reset_bypass_logger()
            reset_evaluate_hook()

            state = dict(sample_state)
            state["is_successful"] = True

            hook = get_evaluate_hook()
            result = await hook.maybe_capture(state)

            # Should capture preview
            assert result.captured is True
            assert result.stored_to_s3 is False

            # Should have created log files
            capture_logs = list((Path(temp_log_dir) / "captures").glob("*.json"))
            assert len(capture_logs) >= 1
