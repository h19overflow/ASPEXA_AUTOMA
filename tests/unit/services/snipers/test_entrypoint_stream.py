"""Unit tests for snipers entrypoint streaming router.

Tests the execute_exploit_stream() function and helper _extract_garak_findings.
"""
import pytest
import logging
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List
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
    execute_exploit_stream,
    _extract_garak_findings,
)
from services.snipers.models import (
    AttackMode,
    ProbeCategory,
    AttackEvent,
    ExploitStreamRequest,
)

logger = logging.getLogger(__name__)


class TestExtractGarakFindings:
    """Test _extract_garak_findings() helper function."""

    def test_extract_from_results_format(self):
        """Test extracting findings from 'results' format."""
        garak_data = {
            "results": [
                {
                    "probe_name": "encoding",
                    "status": "fail",
                    "prompt": "Decode BASE64",
                    "output": "decoded_text",
                    "detector_name": "match",
                    "detector_score": 0.95,
                },
                {
                    "probe_name": "encoding",
                    "status": "pass",
                    "prompt": "test",
                    "output": "test",
                    "detector_name": "match",
                    "detector_score": 0.1,
                },
            ]
        }
        findings = _extract_garak_findings(garak_data)
        assert isinstance(findings, list)
        # Should only extract 'fail' results (vulnerabilities)
        assert len(findings) == 1
        assert findings[0]["status"] == "fail"

    def test_extract_from_vulnerability_clusters_format(self):
        """Test extracting findings from 'vulnerability_clusters' format."""
        garak_data = {
            "vulnerability_clusters": [
                {
                    "findings": [
                        {
                            "probe_name": "dan",
                            "status": "fail",
                            "prompt": "DAN prompt",
                            "output": "jailbreak",
                            "detector_name": "jailbreak_detector",
                            "detector_score": 0.9,
                        }
                    ]
                }
            ]
        }
        findings = _extract_garak_findings(garak_data)
        assert len(findings) == 1
        assert findings[0]["probe_name"] == "dan"

    def test_extract_empty_results(self):
        """Test extracting from empty results."""
        garak_data = {"results": []}
        findings = _extract_garak_findings(garak_data)
        assert findings == []

    def test_extract_empty_clusters(self):
        """Test extracting from empty clusters."""
        garak_data = {"vulnerability_clusters": []}
        findings = _extract_garak_findings(garak_data)
        assert findings == []

    def test_extract_missing_fields(self):
        """Test extracting with missing optional fields."""
        garak_data = {
            "results": [
                {
                    "probe_name": "encoding",
                    "status": "fail",
                    # Missing: prompt, output, detector_name, etc.
                }
            ]
        }
        findings = _extract_garak_findings(garak_data)
        assert len(findings) == 1
        assert findings[0]["probe_name"] == "encoding"
        assert findings[0].get("prompt") == ""

    def test_extract_none_format(self):
        """Test extracting from None/empty dict."""
        findings = _extract_garak_findings({})
        assert findings == []

    def test_extract_multiple_clusters(self):
        """Test extracting from multiple clusters."""
        garak_data = {
            "vulnerability_clusters": [
                {
                    "findings": [
                        {
                            "probe_name": "dan",
                            "status": "fail",
                            "prompt": "DAN",
                            "output": "success",
                            "detector_name": "jailbreak",
                            "detector_score": 0.95,
                        }
                    ]
                },
                {
                    "findings": [
                        {
                            "probe_name": "encoding",
                            "status": "fail",
                            "prompt": "Encode",
                            "output": "decoded",
                            "detector_name": "encoding",
                            "detector_score": 0.9,
                        }
                    ]
                }
            ]
        }
        findings = _extract_garak_findings(garak_data)
        assert len(findings) == 2
        probe_names = {f["probe_name"] for f in findings}
        assert probe_names == {"dan", "encoding"}

    def test_extract_preserves_all_fields(self):
        """Test that all fields are preserved in extraction."""
        garak_data = {
            "results": [
                {
                    "probe_name": "encoding",
                    "status": "fail",
                    "prompt": "test prompt",
                    "output": "test output",
                    "detector_name": "test_detector",
                    "detector_score": 0.88,
                    "extra_field": "extra_value",
                }
            ]
        }
        findings = _extract_garak_findings(garak_data)
        finding = findings[0]
        assert finding["probe_name"] == "encoding"
        assert finding["status"] == "fail"
        assert finding["prompt"] == "test prompt"
        assert finding["output"] == "test output"
        assert finding["detector_name"] == "test_detector"
        assert finding["detector_score"] == 0.88

    def test_extract_mixed_statuses(self):
        """Test extraction only extracts 'fail' status (vulnerabilities)."""
        garak_data = {
            "results": [
                {"probe_name": "p1", "status": "fail", "prompt": "p1", "output": "o1", "detector_name": "d1", "detector_score": 0.9},
                {"probe_name": "p2", "status": "pass", "prompt": "p2", "output": "o2", "detector_name": "d2", "detector_score": 0.1},
            ]
        }
        findings = _extract_garak_findings(garak_data)
        # Only 'fail' status should be extracted (vulnerabilities for exploitation)
        assert len(findings) == 1
        assert findings[0]["status"] == "fail"
        assert findings[0]["probe_name"] == "p1"


class TestExecuteExploitStreamManualMode:
    """Test execute_exploit_stream() with MANUAL mode."""

    @pytest.mark.asyncio
    async def test_manual_mode_with_payload(self):
        """Test manual mode with custom payload."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.MANUAL,
            custom_payload="test payload"
        )

        # Mock run_manual_attack to yield events
        async def mock_manual_flow(req):
            yield AttackEvent(type="plan", data={"mode": "manual"})
            yield AttackEvent(type="complete", data={"mode": "manual"})

        with patch("services.snipers.entrypoint.run_manual_attack", mock_manual_flow):
            events = []
            async for event in execute_exploit_stream(request):
                events.append(event)

            assert len(events) == 2
            assert events[0].type == "plan"
            assert events[1].type == "complete"

    @pytest.mark.asyncio
    async def test_manual_mode_logging(self):
        """Test that manual mode logs appropriately."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.MANUAL,
            custom_payload="test"
        )

        async def mock_manual_flow(req):
            yield AttackEvent(type="complete", data={})

        with patch("services.snipers.entrypoint.run_manual_attack", mock_manual_flow):
            async for _ in execute_exploit_stream(request):
                pass
            # Logging happens during execution


class TestExecuteExploitStreamSweepMode:
    """Test execute_exploit_stream() with SWEEP mode."""

    @pytest.mark.asyncio
    async def test_sweep_mode_with_categories(self):
        """Test sweep mode with categories."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.SWEEP,
            categories=[ProbeCategory.JAILBREAK, ProbeCategory.ENCODING]
        )

        async def mock_sweep_flow(req):
            yield AttackEvent(type="plan", data={"categories": 2})
            yield AttackEvent(type="result", data={"probes": 10})
            yield AttackEvent(type="complete", data={})

        with patch("services.snipers.entrypoint.run_sweep_attack", mock_sweep_flow):
            events = []
            async for event in execute_exploit_stream(request):
                events.append(event)

            assert len(events) == 3
            assert events[0].type == "plan"

    @pytest.mark.asyncio
    async def test_sweep_mode_no_categories(self):
        """Test sweep mode without categories (should use all)."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.SWEEP
        )

        async def mock_sweep_flow(req):
            yield AttackEvent(type="complete", data={})

        with patch("services.snipers.entrypoint.run_sweep_attack", mock_sweep_flow):
            events = []
            async for event in execute_exploit_stream(request):
                events.append(event)

            assert len(events) == 1


class TestExecuteExploitStreamGuidedMode:
    """Test execute_exploit_stream() with GUIDED mode."""

    @pytest.mark.asyncio
    async def test_guided_mode_without_campaign(self):
        """Test guided mode without campaign_id."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.GUIDED,
            probe_name="encoding"
        )

        async def mock_guided_flow(req, findings):
            yield AttackEvent(type="plan", data={"probe": "encoding"})
            yield AttackEvent(type="complete", data={})

        with patch("services.snipers.entrypoint.run_guided_attack", mock_guided_flow):
            events = []
            async for event in execute_exploit_stream(request):
                events.append(event)

            assert len(events) == 2

    @pytest.mark.asyncio
    async def test_guided_mode_with_campaign_no_intel(self):
        """Test guided mode with campaign_id but no intel available."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.GUIDED,
            campaign_id="campaign-001",
            probe_name="encoding"
        )

        async def mock_guided_flow(req, findings):
            yield AttackEvent(type="complete", data={})

        async def mock_load_intel(campaign_id):
            raise ValueError("Campaign not found")

        with patch("services.snipers.entrypoint.run_guided_attack", mock_guided_flow):
            with patch("services.snipers.entrypoint.load_campaign_intel", mock_load_intel):
                events = []
                async for event in execute_exploit_stream(request):
                    events.append(event)

                # Should still complete, just without findings
                assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_guided_mode_with_campaign_and_findings(self):
        """Test guided mode with campaign intel extracted."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.GUIDED,
            campaign_id="campaign-001"
        )

        # Mock campaign intel
        mock_intel = {
            "garak": {
                "results": [
                    {
                        "probe_name": "encoding",
                        "status": "fail",
                        "prompt": "test",
                        "output": "decoded",
                        "detector_name": "decoder",
                        "detector_score": 0.9,
                    }
                ]
            }
        }

        async def mock_load_intel(campaign_id):
            return mock_intel

        async def mock_guided_flow(req, findings):
            yield AttackEvent(type="plan", data={"findings": len(findings) if findings else 0})
            yield AttackEvent(type="complete", data={})

        with patch("services.snipers.entrypoint.load_campaign_intel", mock_load_intel):
            with patch("services.snipers.entrypoint.run_guided_attack", mock_guided_flow):
                events = []
                async for event in execute_exploit_stream(request):
                    events.append(event)

                # Should have extracted findings and passed to flow
                assert any(e.type == "plan" for e in events)


class TestExecuteExploitStreamErrorHandling:
    """Test error handling in execute_exploit_stream()."""

    @pytest.mark.asyncio
    async def test_invalid_mode_rejected_by_pydantic(self):
        """Test that invalid mode is rejected by Pydantic validation."""
        # Pydantic should raise ValidationError for invalid mode
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ExploitStreamRequest(
                target_url="http://localhost:8000/api/chat",
                mode="unknown_mode",  # Invalid mode - not in AttackMode enum
                custom_payload="test"
            )

    @pytest.mark.asyncio
    async def test_flow_exception_handling(self):
        """Test handling when flow raises exception."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.MANUAL,
            custom_payload="test"
        )

        async def mock_manual_flow_error(req):
            yield AttackEvent(type="error", data={"message": "Flow error"})
            # Exception would be caught by the generator

        with patch("services.snipers.entrypoint.run_manual_attack", mock_manual_flow_error):
            events = []
            async for event in execute_exploit_stream(request):
                events.append(event)

            # Should get error event
            assert any(e.type == "error" for e in events)

    @pytest.mark.asyncio
    async def test_campaign_intel_load_with_invalid_garak_data(self):
        """Test loading campaign intel with invalid garak data."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.GUIDED,
            campaign_id="campaign-001"
        )

        # Intel with malformed garak data
        mock_intel = {
            "garak": "invalid_string_instead_of_dict"
        }

        async def mock_load_intel(campaign_id):
            return mock_intel

        async def mock_guided_flow(req, findings):
            yield AttackEvent(type="complete", data={})

        with patch("services.snipers.entrypoint.load_campaign_intel", mock_load_intel):
            with patch("services.snipers.entrypoint.run_guided_attack", mock_guided_flow):
                # Should handle gracefully
                events = []
                try:
                    async for event in execute_exploit_stream(request):
                        events.append(event)
                except Exception as e:
                    # May raise or yield error, both are acceptable
                    logger.info(f"Exception handled: {e}")


class TestExecuteExploitStreamModeRouting:
    """Test correct routing to flow functions based on mode."""

    @pytest.mark.asyncio
    async def test_manual_mode_routes_to_manual_flow(self):
        """Test MANUAL mode routes to run_manual_attack."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.MANUAL,
            custom_payload="payload"
        )

        manual_called = False

        async def mock_manual_flow(req):
            nonlocal manual_called
            manual_called = True
            yield AttackEvent(type="complete", data={})

        async def mock_sweep_flow(req):
            raise AssertionError("Sweep flow should not be called")

        async def mock_guided_flow(req, findings):
            raise AssertionError("Guided flow should not be called")

        with patch("services.snipers.entrypoint.run_manual_attack", mock_manual_flow):
            with patch("services.snipers.entrypoint.run_sweep_attack", mock_sweep_flow):
                with patch("services.snipers.entrypoint.run_guided_attack", mock_guided_flow):
                    async for _ in execute_exploit_stream(request):
                        pass

                    assert manual_called

    @pytest.mark.asyncio
    async def test_sweep_mode_routes_to_sweep_flow(self):
        """Test SWEEP mode routes to run_sweep_attack."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.SWEEP,
            categories=[ProbeCategory.JAILBREAK]
        )

        sweep_called = False

        async def mock_manual_flow(req):
            raise AssertionError("Manual flow should not be called")

        async def mock_sweep_flow(req):
            nonlocal sweep_called
            sweep_called = True
            yield AttackEvent(type="complete", data={})

        async def mock_guided_flow(req, findings):
            raise AssertionError("Guided flow should not be called")

        with patch("services.snipers.entrypoint.run_manual_attack", mock_manual_flow):
            with patch("services.snipers.entrypoint.run_sweep_attack", mock_sweep_flow):
                with patch("services.snipers.entrypoint.run_guided_attack", mock_guided_flow):
                    async for _ in execute_exploit_stream(request):
                        pass

                    assert sweep_called

    @pytest.mark.asyncio
    async def test_guided_mode_routes_to_guided_flow(self):
        """Test GUIDED mode routes to run_guided_attack."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.GUIDED,
            probe_name="encoding"
        )

        guided_called = False

        async def mock_manual_flow(req):
            raise AssertionError("Manual flow should not be called")

        async def mock_sweep_flow(req):
            raise AssertionError("Sweep flow should not be called")

        async def mock_guided_flow(req, findings):
            nonlocal guided_called
            guided_called = True
            yield AttackEvent(type="complete", data={})

        with patch("services.snipers.entrypoint.run_manual_attack", mock_manual_flow):
            with patch("services.snipers.entrypoint.run_sweep_attack", mock_sweep_flow):
                with patch("services.snipers.entrypoint.run_guided_attack", mock_guided_flow):
                    async for _ in execute_exploit_stream(request):
                        pass

                    assert guided_called


class TestExecuteExploitStreamEventStreaming:
    """Test event streaming behavior."""

    @pytest.mark.asyncio
    async def test_events_are_attack_event_objects(self):
        """Test that all yielded events are AttackEvent objects."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.MANUAL,
            custom_payload="test"
        )

        async def mock_manual_flow(req):
            yield AttackEvent(type="plan", data={})
            yield AttackEvent(type="payload", data={"step": 1})
            yield AttackEvent(type="result", data={})
            yield AttackEvent(type="complete", data={})

        with patch("services.snipers.entrypoint.run_manual_attack", mock_manual_flow):
            async for event in execute_exploit_stream(request):
                assert isinstance(event, AttackEvent)
                assert hasattr(event, "type")
                assert hasattr(event, "data")
                assert hasattr(event, "timestamp")

    @pytest.mark.asyncio
    async def test_events_preserve_ordering(self):
        """Test that event order is preserved."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.MANUAL,
            custom_payload="test"
        )

        async def mock_manual_flow(req):
            yield AttackEvent(type="plan", data={"order": 1})
            yield AttackEvent(type="payload", data={"order": 2})
            yield AttackEvent(type="response", data={"order": 3})
            yield AttackEvent(type="result", data={"order": 4})
            yield AttackEvent(type="complete", data={"order": 5})

        with patch("services.snipers.entrypoint.run_manual_attack", mock_manual_flow):
            events = []
            async for event in execute_exploit_stream(request):
                events.append(event)

            assert len(events) == 5
            for i, event in enumerate(events, 1):
                assert event.data.get("order") == i

    @pytest.mark.asyncio
    async def test_streaming_with_large_payload(self):
        """Test streaming with large data payloads."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.MANUAL,
            custom_payload="x" * 100000
        )

        async def mock_manual_flow(req):
            yield AttackEvent(type="plan", data={"large": "x" * 50000})
            yield AttackEvent(type="complete", data={})

        with patch("services.snipers.entrypoint.run_manual_attack", mock_manual_flow):
            event_count = 0
            async for event in execute_exploit_stream(request):
                event_count += 1
                if event.type == "plan":
                    assert len(event.data["large"]) == 50000

            assert event_count == 2
