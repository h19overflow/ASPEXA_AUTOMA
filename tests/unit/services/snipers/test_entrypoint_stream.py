"""Unit tests for snipers entrypoint streaming functions.

Tests execute_full_attack_streaming() and execute_adaptive_attack_streaming()
functions with mocked dependencies.
"""
import pytest
import logging
from unittest.mock import AsyncMock, patch, MagicMock
import sys

# Mock all PyRIT modules to avoid import errors during test collection
mock_pyrit = MagicMock()
mock_pyrit.prompt_target = MagicMock()
mock_pyrit.orchestrator = MagicMock()
mock_pyrit.prompt_converter = MagicMock()
mock_pyrit.score = MagicMock()
mock_pyrit.common = MagicMock()
mock_pyrit.models = MagicMock()
mock_pyrit.memory = MagicMock()

sys.modules['pyrit'] = mock_pyrit
sys.modules['pyrit.prompt_target'] = mock_pyrit.prompt_target
sys.modules['pyrit.orchestrator'] = mock_pyrit.orchestrator
sys.modules['pyrit.prompt_converter'] = mock_pyrit.prompt_converter
sys.modules['pyrit.score'] = mock_pyrit.score
sys.modules['pyrit.common'] = mock_pyrit.common
sys.modules['pyrit.models'] = mock_pyrit.models
sys.modules['pyrit.memory'] = mock_pyrit.memory

# Create necessary mock classes
mock_pyrit.prompt_target.PromptTarget = MagicMock()
mock_pyrit.prompt_target.PromptChatTarget = MagicMock()
mock_pyrit.prompt_target.OpenAIChatTarget = MagicMock()
mock_pyrit.orchestrator.RedTeamingOrchestrator = MagicMock()
mock_pyrit.orchestrator.PromptSendingOrchestrator = MagicMock()
mock_pyrit.prompt_converter.PromptConverter = MagicMock()
mock_pyrit.score.SelfAskTrueFalseScorer = MagicMock()
mock_pyrit.common.initialize_pyrit = MagicMock()
mock_pyrit.common.IN_MEMORY = "in_memory"
mock_pyrit.common.DUCK_DB = "duck_db"
mock_pyrit.models.PromptRequestPiece = MagicMock()
mock_pyrit.models.PromptRequestResponse = MagicMock()
mock_pyrit.memory.CentralMemory = MagicMock()

from services.snipers.entrypoint import (
    execute_full_attack_streaming,
    execute_adaptive_attack_streaming,
)

logger = logging.getLogger(__name__)


class TestFullAttackStreaming:
    """Test execute_full_attack_streaming() function."""

    @pytest.mark.asyncio
    async def test_full_attack_streaming_yields_events(self):
        """Test that streaming yields events correctly."""
        with patch(
            "services.snipers.entrypoint.PayloadArticulation"
        ) as mock_phase1_class, patch(
            "services.snipers.entrypoint.Conversion"
        ) as mock_phase2_class, patch(
            "services.snipers.entrypoint.AttackExecution"
        ) as mock_phase3_class:
            # Setup Phase 1 mock
            mock_phase1 = AsyncMock()
            mock_phase1_class.return_value = mock_phase1

            mock_result1 = MagicMock()
            mock_result1.campaign_id = "test-campaign"
            mock_result1.selected_chain = MagicMock(
                chain_id="chain-1",
                converter_names=["converter1"],
                defense_patterns=["pattern1"],
            )
            mock_result1.articulated_payloads = ["payload1"]
            mock_result1.framing_types_used = ["qa_testing"]
            mock_result1.framing_type = "qa_testing"
            mock_result1.context_summary = {}
            mock_result1.garak_objective = "test"
            mock_result1.defense_patterns = ["pattern1"]
            mock_result1.tools_detected = []

            mock_phase1.execute = AsyncMock(return_value=mock_result1)

            # Setup Phase 2 mock
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2

            mock_payload = MagicMock()
            mock_payload.original = "payload1"
            mock_payload.converted = "converted1"
            mock_payload.chain_id = "chain-1"
            mock_payload.converters_applied = ["converter1"]
            mock_payload.errors = None

            mock_result2 = MagicMock()
            mock_result2.chain_id = "chain-1"
            mock_result2.converter_names = ["converter1"]
            mock_result2.payloads = [mock_payload]
            mock_result2.success_count = 1
            mock_result2.error_count = 0

            mock_phase2.execute = AsyncMock(return_value=mock_result2)

            # Setup Phase 3 mock
            mock_phase3 = AsyncMock()
            mock_phase3_class.return_value = mock_phase3

            mock_attack_resp = MagicMock()
            mock_attack_resp.payload_index = 0
            mock_attack_resp.payload = "converted1"
            mock_attack_resp.response = "response"
            mock_attack_resp.status_code = 200
            mock_attack_resp.latency_ms = 100.0
            mock_attack_resp.error = None

            mock_scorer = MagicMock()
            mock_scorer.severity.value = "high"
            mock_scorer.confidence = 0.85
            mock_scorer.reasoning = "Jailbreak"

            mock_composite = MagicMock()
            mock_composite.overall_severity.value = "high"
            mock_composite.total_score = 0.85
            mock_composite.is_successful = True
            mock_composite.scorer_results = {"jailbreak": mock_scorer}

            mock_result3 = MagicMock()
            mock_result3.campaign_id = "test-campaign"
            mock_result3.target_url = "http://localhost"
            mock_result3.attack_responses = [mock_attack_resp]
            mock_result3.composite_score = mock_composite
            mock_result3.is_successful = True
            mock_result3.overall_severity = "high"
            mock_result3.total_score = 0.85
            mock_result3.learned_chain = None
            mock_result3.failure_analysis = None
            mock_result3.adaptation_strategy = None

            mock_phase3.execute = AsyncMock(return_value=mock_result3)

            # Collect events
            events = []
            async for event in execute_full_attack_streaming(
                campaign_id="test-campaign",
                target_url="http://localhost",
                payload_count=1,
            ):
                events.append(event)

            # Verify we got events
            assert len(events) > 0
            # Verify first and last event types
            assert events[0]["type"] == "attack_started"
            assert events[-1]["type"] == "attack_complete"

    @pytest.mark.asyncio
    async def test_full_attack_streaming_with_framing_types(self):
        """Test streaming with specific framing types."""
        with patch(
            "services.snipers.entrypoint.PayloadArticulation"
        ) as mock_phase1_class, patch(
            "services.snipers.entrypoint.Conversion"
        ) as mock_phase2_class, patch(
            "services.snipers.entrypoint.AttackExecution"
        ) as mock_phase3_class:
            # Setup minimal mocks
            mock_phase1 = AsyncMock()
            mock_phase1_class.return_value = mock_phase1

            mock_result1 = MagicMock()
            mock_result1.campaign_id = "test"
            mock_result1.selected_chain = None
            mock_result1.articulated_payloads = ["p"]
            mock_result1.framing_types_used = ["compliance_audit"]
            mock_result1.framing_type = "compliance_audit"
            mock_result1.context_summary = {}
            mock_result1.garak_objective = "test"
            mock_result1.defense_patterns = []
            mock_result1.tools_detected = []

            mock_phase1.execute = AsyncMock(return_value=mock_result1)

            # Setup phase 2 and 3 to skip for brevity
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2
            mock_phase2.execute = AsyncMock(
                side_effect=Exception("Phase 2 not needed for this test")
            )

            mock_phase3 = AsyncMock()
            mock_phase3_class.return_value = mock_phase3
            mock_phase3.execute = AsyncMock(
                side_effect=Exception("Phase 3 not needed for this test")
            )

            # Verify framing types are passed
            events = []
            try:
                async for event in execute_full_attack_streaming(
                    campaign_id="test",
                    target_url="http://localhost",
                    payload_count=1,
                    framing_types=["compliance_audit", "debugging"],
                ):
                    events.append(event)
            except:
                pass

            # Verify phase1 was called with framing types
            call_args = mock_phase1.execute.call_args
            assert call_args[1]["framing_types"] == ["compliance_audit", "debugging"]


class TestAdaptiveAttackStreaming:
    """Test execute_adaptive_attack_streaming() function."""

    @pytest.mark.asyncio
    async def test_adaptive_attack_streaming_yields_events(self):
        """Test that adaptive streaming yields events correctly."""
        with patch(
            "services.snipers.entrypoint.run_adaptive_attack_streaming"
        ) as mock_run:
            # Mock streaming events
            async def mock_stream():
                yield {
                    "type": "attack_started",
                    "message": "Starting",
                    "timestamp": "2025-01-01T00:00:00Z",
                }
                yield {
                    "type": "iteration_start",
                    "message": "Iteration 1",
                    "data": {"iteration": 1},
                    "timestamp": "2025-01-01T00:00:00Z",
                }
                yield {
                    "type": "iteration_complete",
                    "message": "Iteration complete",
                    "data": {"iteration": 1, "is_successful": True, "score": 0.95},
                    "timestamp": "2025-01-01T00:00:00Z",
                }
                yield {
                    "type": "attack_complete",
                    "message": "Complete",
                    "data": {
                        "campaign_id": "test",
                        "target_url": "http://localhost",
                        "is_successful": True,
                        "total_iterations": 1,
                        "best_score": 0.95,
                    },
                    "timestamp": "2025-01-01T00:00:00Z",
                }

            mock_run.return_value = mock_stream()

            # Collect events
            events = []
            async for event in execute_adaptive_attack_streaming(
                campaign_id="test",
                target_url="http://localhost",
                max_iterations=5,
            ):
                events.append(event)

            # Verify we got events
            assert len(events) == 4
            assert events[0]["type"] == "attack_started"
            assert events[-1]["type"] == "attack_complete"

    @pytest.mark.asyncio
    async def test_adaptive_attack_streaming_with_success_scorers(self):
        """Test streaming with success scorer filters."""
        with patch(
            "services.snipers.entrypoint.run_adaptive_attack_streaming"
        ) as mock_run:
            async def mock_stream():
                yield {"type": "attack_started", "timestamp": "2025-01-01T00:00:00Z"}
                yield {"type": "attack_complete", "timestamp": "2025-01-01T00:00:00Z"}

            mock_run.return_value = mock_stream()

            # Call with success scorers
            events = []
            async for event in execute_adaptive_attack_streaming(
                campaign_id="test",
                target_url="http://localhost",
                max_iterations=5,
                success_scorers=["jailbreak", "prompt_leak"],
                success_threshold=0.8,
            ):
                events.append(event)

            # Verify parameters were passed
            call_args = mock_run.call_args
            assert call_args[1]["success_scorers"] == ["jailbreak", "prompt_leak"]
            assert call_args[1]["success_threshold"] == 0.8

    @pytest.mark.asyncio
    async def test_adaptive_attack_streaming_with_custom_config(self):
        """Test streaming with custom configuration."""
        with patch(
            "services.snipers.entrypoint.run_adaptive_attack_streaming"
        ) as mock_run:
            async def mock_stream():
                yield {"type": "attack_started", "timestamp": "2025-01-01T00:00:00Z"}

            mock_run.return_value = mock_stream()

            # Call with custom config
            events = []
            async for event in execute_adaptive_attack_streaming(
                campaign_id="test",
                target_url="http://localhost",
                max_iterations=10,
                payload_count=3,
                framing_types=["qa_testing"],
                converter_names=["converter1"],
            ):
                events.append(event)

            # Verify all parameters were passed
            call_args = mock_run.call_args
            assert call_args[1]["max_iterations"] == 10
            assert call_args[1]["payload_count"] == 3
            assert call_args[1]["framing_types"] == ["qa_testing"]
            assert call_args[1]["converter_names"] == ["converter1"]
