"""Unit tests for persistence integration in snipers entrypoint.

Tests the S3 and campaign stage persistence for:
- execute_full_attack()
- execute_adaptive_attack()
- Helper functions: _full_result_to_state_dict, _adaptive_result_to_state_dict
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from services.snipers.entrypoint import (
    execute_full_attack,
    execute_adaptive_attack,
    _full_result_to_state_dict,
    _adaptive_result_to_state_dict,
    FullAttackResult,
)
from services.snipers.models import (
    Phase1Result,
    Phase2Result,
    Phase3Result,
    AttackResponse,
)


# ============================================================================
# FIXTURES: Result Objects
# ============================================================================

@pytest.fixture
def mock_composite_score():
    """Mock CompositeScore object."""
    score = MagicMock()
    score.scorer_results = {
        "jailbreak": MagicMock(severity=MagicMock(value="HIGH"), confidence=0.95),
        "prompt_leak": MagicMock(severity=MagicMock(value="MEDIUM"), confidence=0.75),
    }
    return score


@pytest.fixture
def mock_converter_chain():
    """Mock ConverterChain object."""
    chain = MagicMock()
    chain.converter_names = ["Base64Converter", "UrlConverter"]
    return chain


@pytest.fixture
def mock_phase1_result(mock_converter_chain):
    """Mock Phase1Result."""
    return Phase1Result(
        campaign_id="test-campaign",
        selected_chain=mock_converter_chain,
        articulated_payloads=[
            "payload1",
            "payload2",
            "payload3",
        ],
        framing_type="encoding",
        framing_types_used=["encoding", "jailbreak"],
        context_summary={
            "system_prompt": "You are helpful",
            "detected_tools": ["search_db"],
            "recon_used": True,
            "infrastructure": {"vector_db": "FAISS"},
        },
        garak_objective="Test encoding bypass",
        defense_patterns=["encoding_check"],
        tools_detected=["search_db"],
    )


@pytest.fixture
def mock_phase2_result():
    """Mock Phase2Result."""
    from services.snipers.models import ConvertedPayload

    return Phase2Result(
        chain_id="chain-123",
        converter_names=["Base64Converter", "UrlConverter"],
        payloads=[
            ConvertedPayload(
                original="payload1",
                converted="cGF5bG9hZDE=",
                chain_id="chain-123",
                converters_applied=["Base64Converter"],
            ),
            ConvertedPayload(
                original="payload2",
                converted="cGF5bG9hZDI=",
                chain_id="chain-123",
                converters_applied=["Base64Converter"],
            ),
        ],
        success_count=2,
        error_count=0,
    )


@pytest.fixture
def mock_phase3_result(mock_composite_score):
    """Mock Phase3Result."""
    return Phase3Result(
        campaign_id="test-campaign",
        target_url="http://localhost:8082/chat",
        attack_responses=[
            AttackResponse(
                payload_index=0,
                payload="payload1_converted",
                response="Success! Decoded: test",
                status_code=200,
                latency_ms=125.5,
                error=None,
            ),
            AttackResponse(
                payload_index=1,
                payload="payload2_converted",
                response="Success! Decoded: test2",
                status_code=200,
                latency_ms=135.2,
                error=None,
            ),
        ],
        composite_score=mock_composite_score,
        is_successful=True,
        overall_severity="HIGH",
        total_score=0.90,
    )


@pytest.fixture
def full_attack_result(mock_phase1_result, mock_phase2_result, mock_phase3_result):
    """Full attack result combining all three phases."""
    return FullAttackResult(
        campaign_id="test-campaign",
        target_url="http://localhost:8082/chat",
        phase1=mock_phase1_result,
        phase2=mock_phase2_result,
        phase3=mock_phase3_result,
        is_successful=True,
        overall_severity="HIGH",
        total_score=0.90,
        payloads_generated=3,
        payloads_sent=2,
    )


@pytest.fixture
def mock_adaptive_attack_state(mock_phase1_result, mock_phase3_result):
    """Mock AdaptiveAttackState (dict-based)."""
    return {
        "campaign_id": "test-campaign",
        "target_url": "http://localhost:8082/chat",
        "iteration": 2,
        "is_successful": True,
        "best_score": 0.90,
        "best_iteration": 2,
        "phase1_result": mock_phase1_result,
        "phase3_result": mock_phase3_result,
        "chain_selection_result": MagicMock(
            selected_chain=["Base64Converter", "UrlConverter"],
        ),
        "iteration_history": [
            {
                "iteration": 0,
                "is_successful": False,
                "score": 0.45,
                "framing": "encoding",
                "converters": ["Base64Converter"],
            },
            {
                "iteration": 1,
                "is_successful": True,
                "score": 0.90,
                "framing": "jailbreak",
                "converters": ["Base64Converter", "UrlConverter"],
            },
        ],
        "adaptation_reasoning": "Switched to jailbreak framing for better results",
    }


# ============================================================================
# TESTS: Helper Function _full_result_to_state_dict
# ============================================================================

class TestFullResultToStateDict:
    """Tests for _full_result_to_state_dict helper function."""

    def test_converts_full_result_to_state_dict(self, full_attack_result):
        """Should convert FullAttackResult to valid state dict."""
        state_dict = _full_result_to_state_dict(full_attack_result)

        assert isinstance(state_dict, dict)
        assert "probe_name" in state_dict
        assert "pattern_analysis" in state_dict
        assert "converter_selection" in state_dict
        assert "attack_results" in state_dict

    def test_probe_name_from_framing_type(self, full_attack_result):
        """probe_name should come from phase1.framing_type."""
        state_dict = _full_result_to_state_dict(full_attack_result)
        assert state_dict["probe_name"] == "encoding"

    def test_pattern_analysis_from_context_summary(self, full_attack_result):
        """pattern_analysis should come from phase1.context_summary."""
        state_dict = _full_result_to_state_dict(full_attack_result)
        assert state_dict["pattern_analysis"] == full_attack_result.phase1.context_summary

    def test_converter_selection_structure(self, full_attack_result):
        """converter_selection should have selected_converters."""
        state_dict = _full_result_to_state_dict(full_attack_result)
        converter_sel = state_dict["converter_selection"]

        assert converter_sel is not None
        assert "selected_converters" in converter_sel
        assert converter_sel["selected_converters"] == ["Base64Converter", "UrlConverter"]

    def test_converter_selection_none_when_phase2_none(self, mock_phase1_result, mock_phase3_result, mock_composite_score):
        """converter_selection should be None if phase2 is None."""
        result = FullAttackResult(
            campaign_id="test",
            target_url="http://test.com",
            phase1=mock_phase1_result,
            phase2=None,  # No phase2
            phase3=mock_phase3_result,
            is_successful=True,
            overall_severity="HIGH",
            total_score=0.90,
            payloads_generated=3,
            payloads_sent=0,
        )

        state_dict = _full_result_to_state_dict(result)
        assert state_dict["converter_selection"] is None

    def test_attack_results_structure(self, full_attack_result):
        """attack_results should map phase3.attack_responses to dicts."""
        state_dict = _full_result_to_state_dict(full_attack_result)
        attack_results = state_dict["attack_results"]

        assert len(attack_results) == 2
        assert all(isinstance(ar, dict) for ar in attack_results)
        assert all("success" in ar and "payload" in ar and "response" in ar for ar in attack_results)

    def test_attack_results_success_flag(self, full_attack_result):
        """attack_results[].success should be True when no error and is_successful."""
        state_dict = _full_result_to_state_dict(full_attack_result)
        attack_results = state_dict["attack_results"]

        # Both attacks have no error and overall is_successful=True
        assert all(ar["success"] is True for ar in attack_results)

    def test_attack_results_success_false_when_error(self, mock_phase1_result, mock_phase2_result, mock_composite_score):
        """attack_results[].success should be False when error exists."""
        phase3 = Phase3Result(
            campaign_id="test",
            target_url="http://test.com",
            attack_responses=[
                AttackResponse(
                    payload_index=0,
                    payload="test",
                    response="error occurred",
                    status_code=500,
                    latency_ms=100.0,
                    error="Connection timeout",  # Error!
                ),
            ],
            composite_score=mock_composite_score,
            is_successful=False,
            overall_severity="LOW",
            total_score=0.0,
        )

        result = FullAttackResult(
            campaign_id="test",
            target_url="http://test.com",
            phase1=mock_phase1_result,
            phase2=mock_phase2_result,
            phase3=phase3,
            is_successful=False,
            overall_severity="LOW",
            total_score=0.0,
            payloads_generated=1,
            payloads_sent=1,
        )

        state_dict = _full_result_to_state_dict(result)
        assert state_dict["attack_results"][0]["success"] is False

    def test_recon_intelligence_from_context_summary(self, full_attack_result):
        """recon_intelligence should come from context_summary.get('recon_used')."""
        state_dict = _full_result_to_state_dict(full_attack_result)
        assert state_dict["recon_intelligence"] is True

    def test_recon_intelligence_none_when_not_in_context(self, mock_phase1_result, mock_phase2_result, mock_composite_score):
        """recon_intelligence should be None if not in context_summary."""
        phase1 = mock_phase1_result
        phase1.context_summary = {}  # No recon_used key

        phase3 = Phase3Result(
            campaign_id="test",
            target_url="http://test.com",
            attack_responses=[],
            composite_score=mock_composite_score,
            is_successful=False,
            overall_severity="LOW",
            total_score=0.0,
        )

        result = FullAttackResult(
            campaign_id="test",
            target_url="http://test.com",
            phase1=phase1,
            phase2=mock_phase2_result,
            phase3=phase3,
            is_successful=False,
            overall_severity="LOW",
            total_score=0.0,
            payloads_generated=0,
            payloads_sent=0,
        )

        state_dict = _full_result_to_state_dict(result)
        assert state_dict["recon_intelligence"] is None


# ============================================================================
# TESTS: Helper Function _adaptive_result_to_state_dict
# ============================================================================

class TestAdaptiveResultToStateDict:
    """Tests for _adaptive_result_to_state_dict helper function."""

    def test_converts_adaptive_state_to_state_dict(self, mock_adaptive_attack_state):
        """Should convert AdaptiveAttackState dict to valid state dict."""
        state_dict = _adaptive_result_to_state_dict(mock_adaptive_attack_state)

        assert isinstance(state_dict, dict)
        assert "probe_name" in state_dict
        assert "pattern_analysis" in state_dict
        assert "converter_selection" in state_dict
        assert "attack_results" in state_dict

    def test_probe_name_from_phase1(self, mock_adaptive_attack_state):
        """probe_name should come from phase1_result.framing_type."""
        state_dict = _adaptive_result_to_state_dict(mock_adaptive_attack_state)
        assert state_dict["probe_name"] == "encoding"

    def test_probe_name_default_when_no_phase1(self):
        """probe_name should default to 'adaptive' if no phase1_result."""
        state = {
            "phase1_result": None,
            "phase3_result": None,
        }
        state_dict = _adaptive_result_to_state_dict(state)
        assert state_dict["probe_name"] == "adaptive"

    def test_pattern_analysis_from_phase1(self, mock_adaptive_attack_state):
        """pattern_analysis should come from phase1_result.context_summary."""
        state_dict = _adaptive_result_to_state_dict(mock_adaptive_attack_state)
        assert state_dict["pattern_analysis"] == mock_adaptive_attack_state["phase1_result"].context_summary

    def test_pattern_analysis_empty_dict_when_no_phase1(self):
        """pattern_analysis should be {} if no phase1_result."""
        state = {"phase1_result": None, "phase3_result": None}
        state_dict = _adaptive_result_to_state_dict(state)
        assert state_dict["pattern_analysis"] == {}

    def test_converter_selection_from_chain_selection(self, mock_adaptive_attack_state):
        """converter_selection should come from chain_selection_result."""
        state_dict = _adaptive_result_to_state_dict(mock_adaptive_attack_state)
        converter_sel = state_dict["converter_selection"]

        assert converter_sel is not None
        assert "selected_converters" in converter_sel

    def test_converter_selection_from_phase1_when_no_chain_selection(self, mock_adaptive_attack_state):
        """converter_selection should fallback to phase1_result.selected_chain."""
        state = mock_adaptive_attack_state.copy()
        state["chain_selection_result"] = None  # Remove chain selection

        state_dict = _adaptive_result_to_state_dict(state)
        converter_sel = state_dict["converter_selection"]

        assert converter_sel is not None
        assert "selected_converters" in converter_sel
        assert converter_sel["selected_converters"] == ["Base64Converter", "UrlConverter"]

    def test_converter_selection_none_when_no_sources(self, mock_phase1_result):
        """converter_selection should be None if no chain_selection or phase1.selected_chain."""
        phase1 = mock_phase1_result
        phase1.selected_chain = None  # No selected chain

        state = {
            "phase1_result": phase1,
            "chain_selection_result": None,
            "phase3_result": None,
        }
        state_dict = _adaptive_result_to_state_dict(state)
        assert state_dict["converter_selection"] is None

    def test_attack_results_built_from_phase3(self, mock_adaptive_attack_state):
        """attack_results should be built from phase3_result.attack_responses."""
        state_dict = _adaptive_result_to_state_dict(mock_adaptive_attack_state)
        attack_results = state_dict["attack_results"]

        assert len(attack_results) == 2
        assert all(isinstance(ar, dict) for ar in attack_results)

    def test_attack_results_empty_when_no_phase3(self, mock_phase1_result):
        """attack_results should be [] if no phase3_result."""
        state = {
            "phase1_result": mock_phase1_result,
            "phase3_result": None,
            "is_successful": False,
        }
        state_dict = _adaptive_result_to_state_dict(state)
        assert state_dict["attack_results"] == []

    def test_iteration_count_from_state(self, mock_adaptive_attack_state):
        """iteration_count should be state['iteration'] + 1."""
        state_dict = _adaptive_result_to_state_dict(mock_adaptive_attack_state)
        # iteration=2 in state, so count should be 3
        assert state_dict["iteration_count"] == 3

    def test_best_score_from_state(self, mock_adaptive_attack_state):
        """best_score should come from state['best_score']."""
        state_dict = _adaptive_result_to_state_dict(mock_adaptive_attack_state)
        assert state_dict["best_score"] == 0.90

    def test_best_score_default_zero(self):
        """best_score should default to 0.0 if not in state."""
        state = {"phase1_result": None, "phase3_result": None}
        state_dict = _adaptive_result_to_state_dict(state)
        assert state_dict["best_score"] == 0.0

    def test_adaptation_reasoning_from_state(self, mock_adaptive_attack_state):
        """adaptation_reasoning should come from state."""
        state_dict = _adaptive_result_to_state_dict(mock_adaptive_attack_state)
        assert state_dict["adaptation_reasoning"] == "Switched to jailbreak framing for better results"

    def test_adaptation_reasoning_default_empty(self):
        """adaptation_reasoning should default to '' if not in state."""
        state = {"phase1_result": None, "phase3_result": None}
        state_dict = _adaptive_result_to_state_dict(state)
        assert state_dict["adaptation_reasoning"] == ""


# ============================================================================
# TESTS: execute_full_attack Persistence
# ============================================================================

class TestExecuteFullAttackPersistence:
    """Tests for persistence in execute_full_attack()."""

    @pytest.mark.asyncio
    async def test_calls_persist_exploit_result(
        self,
        full_attack_result,
        mock_phase1_result,
        mock_phase2_result,
        mock_phase3_result,
    ):
        """Should call persist_exploit_result with correct parameters."""
        with patch("services.snipers.entrypoint.PayloadArticulation") as mock_pa, \
             patch("services.snipers.entrypoint.Conversion") as mock_conv, \
             patch("services.snipers.entrypoint.AttackExecution") as mock_ae, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format:

            # Setup mocks
            mock_pa_instance = AsyncMock()
            mock_pa_instance.execute.return_value = mock_phase1_result
            mock_pa.return_value = mock_pa_instance

            mock_conv_instance = AsyncMock()
            mock_conv_instance.execute.return_value = mock_phase2_result
            mock_conv.return_value = mock_conv_instance

            mock_ae_instance = AsyncMock()
            mock_ae_instance.execute.return_value = mock_phase3_result
            mock_ae.return_value = mock_ae_instance

            mock_persist.return_value = None  # Async function
            mock_format.return_value = {"formatted": "result"}

            # Execute
            result = await execute_full_attack(
                campaign_id="test-campaign",
                target_url="http://localhost:8082/chat",
                payload_count=3,
            )

            # Verify persist_exploit_result was called
            mock_persist.assert_called_once()
            call_args = mock_persist.call_args

            assert call_args.kwargs["campaign_id"] == "test-campaign"
            assert "scan_id" in call_args.kwargs
            assert call_args.kwargs["target_url"] == "http://localhost:8082/chat"
            assert "exploit_result" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_scan_id_format(
        self,
        mock_phase1_result,
        mock_phase2_result,
        mock_phase3_result,
    ):
        """scan_id should be campaign_id-{hex_suffix} format."""
        with patch("services.snipers.entrypoint.PayloadArticulation") as mock_pa, \
             patch("services.snipers.entrypoint.Conversion") as mock_conv, \
             patch("services.snipers.entrypoint.AttackExecution") as mock_ae, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format:

            mock_pa_instance = AsyncMock()
            mock_pa_instance.execute.return_value = mock_phase1_result
            mock_pa.return_value = mock_pa_instance

            mock_conv_instance = AsyncMock()
            mock_conv_instance.execute.return_value = mock_phase2_result
            mock_conv.return_value = mock_conv_instance

            mock_ae_instance = AsyncMock()
            mock_ae_instance.execute.return_value = mock_phase3_result
            mock_ae.return_value = mock_ae_instance

            mock_persist.return_value = None
            mock_format.return_value = {"formatted": "result"}

            await execute_full_attack(
                campaign_id="test-campaign",
                target_url="http://localhost:8082/chat",
            )

            call_args = mock_persist.call_args
            scan_id = call_args.kwargs["scan_id"]

            assert scan_id.startswith("test-campaign-")
            assert len(scan_id) == len("test-campaign-") + 8  # 8-char hex suffix

    @pytest.mark.asyncio
    async def test_format_exploit_result_called(
        self,
        mock_phase1_result,
        mock_phase2_result,
        mock_phase3_result,
    ):
        """Should call format_exploit_result with state dict."""
        with patch("services.snipers.entrypoint.PayloadArticulation") as mock_pa, \
             patch("services.snipers.entrypoint.Conversion") as mock_conv, \
             patch("services.snipers.entrypoint.AttackExecution") as mock_ae, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format:

            mock_pa_instance = AsyncMock()
            mock_pa_instance.execute.return_value = mock_phase1_result
            mock_pa.return_value = mock_pa_instance

            mock_conv_instance = AsyncMock()
            mock_conv_instance.execute.return_value = mock_phase2_result
            mock_conv.return_value = mock_conv_instance

            mock_ae_instance = AsyncMock()
            mock_ae_instance.execute.return_value = mock_phase3_result
            mock_ae.return_value = mock_ae_instance

            mock_persist.return_value = None
            mock_format.return_value = {"formatted": "result"}

            await execute_full_attack(
                campaign_id="test-campaign",
                target_url="http://localhost:8082/chat",
            )

            mock_format.assert_called_once()
            call_args = mock_format.call_args

            assert "state" in call_args.kwargs
            assert call_args.kwargs["audit_id"] == "test-campaign"
            assert call_args.kwargs["target_url"] == "http://localhost:8082/chat"
            assert "execution_time" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_persist_exception_propagates(
        self,
        mock_phase1_result,
        mock_phase2_result,
        mock_phase3_result,
    ):
        """Should propagate exceptions from persist_exploit_result."""
        with patch("services.snipers.entrypoint.PayloadArticulation") as mock_pa, \
             patch("services.snipers.entrypoint.Conversion") as mock_conv, \
             patch("services.snipers.entrypoint.AttackExecution") as mock_ae, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format:

            mock_pa_instance = AsyncMock()
            mock_pa_instance.execute.return_value = mock_phase1_result
            mock_pa.return_value = mock_pa_instance

            mock_conv_instance = AsyncMock()
            mock_conv_instance.execute.return_value = mock_phase2_result
            mock_conv.return_value = mock_conv_instance

            mock_ae_instance = AsyncMock()
            mock_ae_instance.execute.return_value = mock_phase3_result
            mock_ae.return_value = mock_ae_instance

            mock_format.return_value = {"formatted": "result"}
            mock_persist.side_effect = Exception("S3 upload failed")

            with pytest.raises(Exception, match="S3 upload failed"):
                await execute_full_attack(
                    campaign_id="test-campaign",
                    target_url="http://localhost:8082/chat",
                )


# ============================================================================
# TESTS: execute_adaptive_attack Persistence
# ============================================================================

class TestExecuteAdaptiveAttackPersistence:
    """Tests for persistence in execute_adaptive_attack()."""

    @pytest.mark.asyncio
    async def test_calls_persist_exploit_result(self, mock_adaptive_attack_state):
        """Should call persist_exploit_result with correct parameters."""
        with patch("services.snipers.entrypoint.run_adaptive_attack") as mock_run, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format:

            mock_run.return_value = mock_adaptive_attack_state
            mock_persist.return_value = None
            mock_format.return_value = {"formatted": "result"}

            result = await execute_adaptive_attack(
                campaign_id="test-campaign",
                target_url="http://localhost:8082/chat",
            )

            mock_persist.assert_called_once()
            call_args = mock_persist.call_args

            assert call_args.kwargs["campaign_id"] == "test-campaign"
            assert "scan_id" in call_args.kwargs
            assert call_args.kwargs["target_url"] == "http://localhost:8082/chat"
            assert "exploit_result" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_adaptive_scan_id_format(self, mock_adaptive_attack_state):
        """scan_id for adaptive should be campaign_id-adaptive-{hex_suffix} format."""
        with patch("services.snipers.entrypoint.run_adaptive_attack") as mock_run, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format:

            mock_run.return_value = mock_adaptive_attack_state
            mock_persist.return_value = None
            mock_format.return_value = {"formatted": "result"}

            await execute_adaptive_attack(
                campaign_id="test-campaign",
                target_url="http://localhost:8082/chat",
            )

            call_args = mock_persist.call_args
            scan_id = call_args.kwargs["scan_id"]

            assert scan_id.startswith("test-campaign-adaptive-")
            assert len(scan_id) == len("test-campaign-adaptive-") + 8  # 8-char hex suffix

    @pytest.mark.asyncio
    async def test_format_exploit_result_called_with_adaptive_state(self, mock_adaptive_attack_state):
        """Should call format_exploit_result with adaptive state dict."""
        with patch("services.snipers.entrypoint.run_adaptive_attack") as mock_run, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format:

            mock_run.return_value = mock_adaptive_attack_state
            mock_persist.return_value = None
            mock_format.return_value = {"formatted": "result"}

            await execute_adaptive_attack(
                campaign_id="test-campaign",
                target_url="http://localhost:8082/chat",
                max_iterations=5,
            )

            mock_format.assert_called_once()
            call_args = mock_format.call_args

            assert "state" in call_args.kwargs
            assert call_args.kwargs["audit_id"] == "test-campaign"
            assert call_args.kwargs["target_url"] == "http://localhost:8082/chat"
            assert "execution_time" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_persist_exception_propagates(self, mock_adaptive_attack_state):
        """Should propagate exceptions from persist_exploit_result."""
        with patch("services.snipers.entrypoint.run_adaptive_attack") as mock_run, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format:

            mock_run.return_value = mock_adaptive_attack_state
            mock_format.return_value = {"formatted": "result"}
            mock_persist.side_effect = Exception("S3 upload failed")

            with pytest.raises(Exception, match="S3 upload failed"):
                await execute_adaptive_attack(
                    campaign_id="test-campaign",
                    target_url="http://localhost:8082/chat",
                )

    @pytest.mark.asyncio
    async def test_adaptive_returns_original_state(self, mock_adaptive_attack_state):
        """execute_adaptive_attack should return the state from run_adaptive_attack."""
        with patch("services.snipers.entrypoint.run_adaptive_attack") as mock_run, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format:

            mock_run.return_value = mock_adaptive_attack_state
            mock_persist.return_value = None
            mock_format.return_value = {"formatted": "result"}

            result = await execute_adaptive_attack(
                campaign_id="test-campaign",
                target_url="http://localhost:8082/chat",
            )

            # Should return the state unchanged
            assert result == mock_adaptive_attack_state


# ============================================================================
# TESTS: Execution Time Tracking
# ============================================================================

class TestExecutionTimeTracking:
    """Tests for execution time tracking in persistence."""

    @pytest.mark.asyncio
    async def test_full_attack_execution_time_passed_to_format(
        self,
        mock_phase1_result,
        mock_phase2_result,
        mock_phase3_result,
    ):
        """execution_time should be measured and passed to format_exploit_result."""
        with patch("services.snipers.entrypoint.PayloadArticulation") as mock_pa, \
             patch("services.snipers.entrypoint.Conversion") as mock_conv, \
             patch("services.snipers.entrypoint.AttackExecution") as mock_ae, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format, \
             patch("services.snipers.entrypoint.time") as mock_time:

            # Mock time to control execution_time calculation
            mock_time.time.side_effect = [0.0, 1.5]  # Start at 0, end at 1.5

            mock_pa_instance = AsyncMock()
            mock_pa_instance.execute.return_value = mock_phase1_result
            mock_pa.return_value = mock_pa_instance

            mock_conv_instance = AsyncMock()
            mock_conv_instance.execute.return_value = mock_phase2_result
            mock_conv.return_value = mock_conv_instance

            mock_ae_instance = AsyncMock()
            mock_ae_instance.execute.return_value = mock_phase3_result
            mock_ae.return_value = mock_ae_instance

            mock_persist.return_value = None
            mock_format.return_value = {"formatted": "result"}

            await execute_full_attack(
                campaign_id="test-campaign",
                target_url="http://localhost:8082/chat",
            )

            call_args = mock_format.call_args
            execution_time = call_args.kwargs["execution_time"]

            assert execution_time == 1.5

    @pytest.mark.asyncio
    async def test_adaptive_attack_execution_time_passed_to_format(
        self,
        mock_adaptive_attack_state,
    ):
        """execution_time should be measured and passed to format_exploit_result for adaptive."""
        with patch("services.snipers.entrypoint.run_adaptive_attack") as mock_run, \
             patch("services.snipers.entrypoint.persist_exploit_result") as mock_persist, \
             patch("services.snipers.entrypoint.format_exploit_result") as mock_format, \
             patch("services.snipers.entrypoint.time") as mock_time:

            mock_time.time.side_effect = [0.0, 2.5]  # Start at 0, end at 2.5

            mock_run.return_value = mock_adaptive_attack_state
            mock_persist.return_value = None
            mock_format.return_value = {"formatted": "result"}

            await execute_adaptive_attack(
                campaign_id="test-campaign",
                target_url="http://localhost:8082/chat",
            )

            call_args = mock_format.call_args
            execution_time = call_args.kwargs["execution_time"]

            assert execution_time == 2.5


# ============================================================================
# TESTS: State Dict Validation
# ============================================================================

class TestStateDictValidation:
    """Tests for validating state dict output structure."""

    def test_full_state_dict_has_required_fields(self, full_attack_result):
        """State dict from _full_result_to_state_dict should have required fields."""
        state_dict = _full_result_to_state_dict(full_attack_result)

        required_fields = [
            "probe_name",
            "pattern_analysis",
            "converter_selection",
            "attack_results",
            "recon_intelligence",
        ]

        for field in required_fields:
            assert field in state_dict, f"Missing required field: {field}"

    def test_adaptive_state_dict_has_required_fields(self, mock_adaptive_attack_state):
        """State dict from _adaptive_result_to_state_dict should have required fields."""
        state_dict = _adaptive_result_to_state_dict(mock_adaptive_attack_state)

        required_fields = [
            "probe_name",
            "pattern_analysis",
            "converter_selection",
            "attack_results",
            "recon_intelligence",
            "iteration_count",
            "best_score",
            "best_iteration",
            "adaptation_reasoning",
        ]

        for field in required_fields:
            assert field in state_dict, f"Missing required field: {field}"

    def test_attack_results_payload_preserved(self, full_attack_result):
        """attack_results should preserve original payloads."""
        state_dict = _full_result_to_state_dict(full_attack_result)
        attack_results = state_dict["attack_results"]

        for i, attack_resp in enumerate(full_attack_result.phase3.attack_responses):
            assert attack_results[i]["payload"] == attack_resp.payload
            assert attack_results[i]["response"] == attack_resp.response

    def test_attack_results_response_preserved(self, full_attack_result):
        """attack_results should preserve original responses."""
        state_dict = _full_result_to_state_dict(full_attack_result)
        attack_results = state_dict["attack_results"]

        for i, attack_resp in enumerate(full_attack_result.phase3.attack_responses):
            assert attack_results[i]["response"] == attack_resp.response


# ============================================================================
# TESTS: Edge Cases and Error Conditions
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_full_result_with_empty_attack_responses(self, mock_phase1_result, mock_phase2_result, mock_composite_score):
        """Should handle empty attack_responses gracefully."""
        phase3 = Phase3Result(
            campaign_id="test",
            target_url="http://test.com",
            attack_responses=[],  # Empty!
            composite_score=mock_composite_score,
            is_successful=False,
            overall_severity="LOW",
            total_score=0.0,
        )

        result = FullAttackResult(
            campaign_id="test",
            target_url="http://test.com",
            phase1=mock_phase1_result,
            phase2=mock_phase2_result,
            phase3=phase3,
            is_successful=False,
            overall_severity="LOW",
            total_score=0.0,
            payloads_generated=0,
            payloads_sent=0,
        )

        state_dict = _full_result_to_state_dict(result)
        assert state_dict["attack_results"] == []

    def test_adaptive_state_with_none_phase_results(self):
        """Should handle None phase results gracefully."""
        state = {
            "phase1_result": None,
            "phase3_result": None,
            "chain_selection_result": None,
            "iteration": 0,
        }

        state_dict = _adaptive_result_to_state_dict(state)

        assert state_dict["probe_name"] == "adaptive"
        assert state_dict["pattern_analysis"] == {}
        assert state_dict["converter_selection"] is None
        assert state_dict["attack_results"] == []

    def test_attack_result_with_error_none_is_successful(self, mock_phase1_result, mock_phase2_result, mock_composite_score):
        """Attack with error=None but is_successful=False should have success=False."""
        phase3 = Phase3Result(
            campaign_id="test",
            target_url="http://test.com",
            attack_responses=[
                AttackResponse(
                    payload_index=0,
                    payload="test",
                    response="response",
                    status_code=200,
                    latency_ms=100.0,
                    error=None,  # No error
                ),
            ],
            composite_score=mock_composite_score,
            is_successful=False,  # But not successful overall
            overall_severity="LOW",
            total_score=0.0,
        )

        result = FullAttackResult(
            campaign_id="test",
            target_url="http://test.com",
            phase1=mock_phase1_result,
            phase2=mock_phase2_result,
            phase3=phase3,
            is_successful=False,
            overall_severity="LOW",
            total_score=0.0,
            payloads_generated=1,
            payloads_sent=1,
        )

        state_dict = _full_result_to_state_dict(result)
        # error is None but is_successful is False, so success should be False
        assert state_dict["attack_results"][0]["success"] is False
