"""
Unit tests for Snipers API Gateway routers.

Purpose: Test HTTP layer for all snipers attack phase endpoints
Role: Validates request/response serialization, error handling, and endpoint behavior
Dependencies: FastAPI TestClient, pytest, unittest.mock
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api_gateway.schemas.snipers import (
    Phase1Request,
    Phase1Response,
    Phase2Request,
    Phase2Response,
    Phase3Request,
    Phase3Response,
    FullAttackRequest,
    FullAttackResponse,
    AdaptiveAttackRequest,
    AdaptiveAttackResponse,
    FramingType,
    ScorerType,
)
from services.api_gateway.routers.snipers.phase1 import router as phase1_router
from services.api_gateway.routers.snipers.phase2 import router as phase2_router
from services.api_gateway.routers.snipers.phase3 import router as phase3_router
from services.api_gateway.routers.snipers.attack import router as attack_router


@pytest.fixture
def client():
    """FastAPI TestClient for the snipers routers."""
    app = FastAPI()
    app.include_router(phase1_router, prefix="/api/snipers")
    app.include_router(phase2_router, prefix="/api/snipers")
    app.include_router(phase3_router, prefix="/api/snipers")
    app.include_router(attack_router, prefix="/api/snipers")
    return TestClient(app)


# =============================================================================
# Phase 1: Payload Articulation Tests
# =============================================================================


class TestPhase1Endpoints:
    """Tests for Phase 1 (Payload Articulation) endpoints."""

    @pytest.mark.asyncio
    async def test_phase1_basic_request(self, client):
        """Test Phase 1 basic execution with minimal parameters."""
        with patch(
            "services.api_gateway.routers.snipers.phase1.PayloadArticulation"
        ) as mock_phase1_class:
            # Setup mock
            mock_phase1 = AsyncMock()
            mock_phase1_class.return_value = mock_phase1

            mock_result = MagicMock()
            mock_result.campaign_id = "test-campaign"
            mock_result.selected_chain = None
            mock_result.articulated_payloads = [
                "payload1",
                "payload2",
                "payload3",
            ]
            mock_result.framing_type = "qa_testing"
            mock_result.framing_types_used = ["qa_testing"]
            mock_result.context_summary = {"tools": ["search"]}
            mock_result.garak_objective = "test objective"
            mock_result.defense_patterns = ["pattern1"]
            mock_result.tools_detected = ["tool1"]

            mock_phase1.execute = AsyncMock(return_value=mock_result)

            # Execute request
            payload = {
                "campaign_id": "test-campaign",
                "payload_count": 3,
            }
            response = client.post("/api/snipers/phase1", json=payload)

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["campaign_id"] == "test-campaign"
            assert len(data["articulated_payloads"]) == 3
            assert data["framing_type"] == "qa_testing"
            assert data["selected_chain"] is None

    @pytest.mark.asyncio
    async def test_phase1_with_framing_types(self, client):
        """Test Phase 1 with specific framing types."""
        with patch(
            "services.api_gateway.routers.snipers.phase1.PayloadArticulation"
        ) as mock_phase1_class:
            mock_phase1 = AsyncMock()
            mock_phase1_class.return_value = mock_phase1

            mock_result = MagicMock()
            mock_result.campaign_id = "test-campaign"
            mock_result.selected_chain = None
            mock_result.articulated_payloads = ["payload1"]
            mock_result.framing_type = "compliance_audit"
            mock_result.framing_types_used = ["compliance_audit"]
            mock_result.context_summary = {}
            mock_result.garak_objective = "compliance test"
            mock_result.defense_patterns = []
            mock_result.tools_detected = []

            mock_phase1.execute = AsyncMock(return_value=mock_result)

            payload = {
                "campaign_id": "test-campaign",
                "payload_count": 1,
                "framing_types": ["compliance_audit", "debugging"],
            }
            response = client.post("/api/snipers/phase1", json=payload)

            assert response.status_code == 200
            # Verify execute was called with enum values converted to strings
            call_args = mock_phase1.execute.call_args
            assert call_args[1]["framing_types"] == [
                "compliance_audit",
                "debugging",
            ]

    @pytest.mark.asyncio
    async def test_phase1_with_custom_framing(self, client):
        """Test Phase 1 with custom framing strategy."""
        with patch(
            "services.api_gateway.routers.snipers.phase1.PayloadArticulation"
        ) as mock_phase1_class:
            mock_phase1 = AsyncMock()
            mock_phase1_class.return_value = mock_phase1

            mock_result = MagicMock()
            mock_result.campaign_id = "test-campaign"
            mock_result.selected_chain = MagicMock(
                chain_id="chain-1",
                converter_names=["converter1"],
                defense_patterns=["pattern1"],
            )
            mock_result.articulated_payloads = ["custom_payload"]
            mock_result.framing_type = "custom"
            mock_result.framing_types_used = ["custom"]
            mock_result.context_summary = {}
            mock_result.garak_objective = "custom test"
            mock_result.defense_patterns = ["pattern1"]
            mock_result.tools_detected = []

            mock_phase1.execute = AsyncMock(return_value=mock_result)

            payload = {
                "campaign_id": "test-campaign",
                "payload_count": 1,
                "custom_framing": {
                    "name": "custom_framing",
                    "system_context": "Custom context",
                    "user_prefix": "Prefix: ",
                    "user_suffix": " :Suffix",
                },
            }
            response = client.post("/api/snipers/phase1", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["selected_chain"] is not None
            assert data["selected_chain"]["chain_id"] == "chain-1"
            assert data["selected_chain"]["converter_names"] == ["converter1"]

    @pytest.mark.asyncio
    async def test_phase1_request_validation_missing_campaign(self, client):
        """Test Phase 1 validation: missing campaign_id."""
        payload = {"payload_count": 3}
        response = client.post("/api/snipers/phase1", json=payload)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_phase1_request_validation_invalid_payload_count(self, client):
        """Test Phase 1 validation: payload_count out of range."""
        payload = {
            "campaign_id": "test",
            "payload_count": 10,  # Max is 6
        }
        response = client.post("/api/snipers/phase1", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_phase1_error_handling_value_error(self, client):
        """Test Phase 1 error handling: ValueError from service."""
        with patch(
            "services.api_gateway.routers.snipers.phase1.PayloadArticulation"
        ) as mock_phase1_class:
            mock_phase1 = AsyncMock()
            mock_phase1_class.return_value = mock_phase1
            mock_phase1.execute = AsyncMock(
                side_effect=ValueError("Invalid campaign")
            )

            payload = {
                "campaign_id": "invalid-campaign",
                "payload_count": 3,
            }
            response = client.post("/api/snipers/phase1", json=payload)

            assert response.status_code == 400
            assert "Invalid campaign" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_phase1_error_handling_generic_error(self, client):
        """Test Phase 1 error handling: generic exception."""
        with patch(
            "services.api_gateway.routers.snipers.phase1.PayloadArticulation"
        ) as mock_phase1_class:
            mock_phase1 = AsyncMock()
            mock_phase1_class.return_value = mock_phase1
            mock_phase1.execute = AsyncMock(side_effect=Exception("Service error"))

            payload = {
                "campaign_id": "test-campaign",
                "payload_count": 3,
            }
            response = client.post("/api/snipers/phase1", json=payload)

            assert response.status_code == 500
            assert "Phase 1 execution failed" in response.json()["detail"]

    def test_phase1_list_framing_types(self, client):
        """Test GET /framing-types endpoint."""
        response = client.get("/api/snipers/phase1/framing-types")

        assert response.status_code == 200
        data = response.json()
        assert "framing_types" in data
        assert len(data["framing_types"]) == 6

        framing_names = [f["name"] for f in data["framing_types"]]
        assert "qa_testing" in framing_names
        assert "compliance_audit" in framing_names
        assert "documentation" in framing_names
        assert "debugging" in framing_names
        assert "educational" in framing_names
        assert "research" in framing_names


# =============================================================================
# Phase 2: Conversion Tests
# =============================================================================


class TestPhase2Endpoints:
    """Tests for Phase 2 (Conversion) endpoints."""

    @pytest.mark.asyncio
    async def test_phase2_basic_request(self, client):
        """Test Phase 2 basic execution with payloads."""
        with patch(
            "services.api_gateway.routers.snipers.phase2.Conversion"
        ) as mock_phase2_class:
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2

            # Mock converted payload object
            mock_payload = MagicMock()
            mock_payload.original = "original_payload"
            mock_payload.converted = "converted_payload"
            mock_payload.chain_id = "chain-1"
            mock_payload.converters_applied = ["converter1"]
            mock_payload.errors = None

            mock_result = MagicMock()
            mock_result.chain_id = "chain-1"
            mock_result.converter_names = ["converter1"]
            mock_result.payloads = [mock_payload]
            mock_result.success_count = 1
            mock_result.error_count = 0

            mock_phase2.execute = AsyncMock(return_value=mock_result)

            payload = {
                "payloads": ["original_payload"],
                "converter_names": ["converter1"],
            }
            response = client.post("/api/snipers/phase2", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["chain_id"] == "chain-1"
            assert len(data["payloads"]) == 1
            assert data["payloads"][0]["original"] == "original_payload"
            assert data["payloads"][0]["converted"] == "converted_payload"
            assert data["success_count"] == 1
            assert data["error_count"] == 0

    @pytest.mark.asyncio
    async def test_phase2_with_converter_params(self, client):
        """Test Phase 2 with converter parameters."""
        with patch(
            "services.api_gateway.routers.snipers.phase2.Conversion"
        ) as mock_phase2_class:
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2

            mock_payload = MagicMock()
            mock_payload.original = "payload"
            mock_payload.converted = "converted"
            mock_payload.chain_id = "chain-1"
            mock_payload.converters_applied = ["converter1"]
            mock_payload.errors = None

            mock_result = MagicMock()
            mock_result.chain_id = "chain-1"
            mock_result.converter_names = ["converter1"]
            mock_result.payloads = [mock_payload]
            mock_result.success_count = 1
            mock_result.error_count = 0

            mock_phase2.execute = AsyncMock(return_value=mock_result)

            payload = {
                "payloads": ["payload"],
                "converter_names": ["converter1"],
                "converter_params": {
                    "converter1": {"param1": "value1"}
                },
            }
            response = client.post("/api/snipers/phase2", json=payload)

            assert response.status_code == 200
            # Verify params were passed
            call_args = mock_phase2.execute.call_args
            assert call_args[1]["converter_params"]["converter1"]["param1"] == "value1"

    @pytest.mark.asyncio
    async def test_phase2_with_phase1_result(self, client):
        """Test Phase 2 using Phase 1 result."""
        with patch(
            "services.api_gateway.routers.snipers.phase2.Conversion"
        ) as mock_phase2_class, patch(
            "services.api_gateway.routers.snipers.phase2.ConverterChain"
        ) as mock_chain_class:
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2

            mock_payload = MagicMock()
            mock_payload.original = "payload"
            mock_payload.converted = "converted"
            mock_payload.chain_id = "chain-1"
            mock_payload.converters_applied = ["converter1"]
            mock_payload.errors = None

            mock_result = MagicMock()
            mock_result.chain_id = "chain-1"
            mock_result.converter_names = ["converter1"]
            mock_result.payloads = [mock_payload]
            mock_result.success_count = 1
            mock_result.error_count = 0

            mock_phase2.execute = AsyncMock(return_value=mock_result)
            mock_chain_class.from_converter_names = MagicMock(
                return_value=MagicMock()
            )

            phase1_response = {
                "campaign_id": "test-campaign",
                "selected_chain": {
                    "chain_id": "chain-1",
                    "converter_names": ["converter1"],
                    "defense_patterns": [],
                },
                "articulated_payloads": ["payload"],
                "framing_type": "qa_testing",
                "framing_types_used": ["qa_testing"],
                "context_summary": {},
                "garak_objective": "test",
                "defense_patterns": [],
                "tools_detected": [],
            }

            payload = {
                "phase1_response": phase1_response,
            }
            response = client.post("/api/snipers/phase2/with-phase1", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["chain_id"] == "chain-1"

    @pytest.mark.asyncio
    async def test_phase2_request_validation_empty_payloads(self, client):
        """Test Phase 2 validation: empty payloads list."""
        payload = {
            "payloads": [],
        }
        response = client.post("/api/snipers/phase2", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_phase2_request_validation_missing_payloads(self, client):
        """Test Phase 2 validation: missing payloads."""
        payload = {}
        response = client.post("/api/snipers/phase2", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_phase2_error_handling_value_error(self, client):
        """Test Phase 2 error handling: ValueError."""
        with patch(
            "services.api_gateway.routers.snipers.phase2.Conversion"
        ) as mock_phase2_class:
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2
            mock_phase2.execute = AsyncMock(
                side_effect=ValueError("Invalid payload")
            )

            payload = {
                "payloads": ["invalid"],
            }
            response = client.post("/api/snipers/phase2", json=payload)

            assert response.status_code == 400
            assert "Invalid payload" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_phase2_list_converters(self, client):
        """Test GET /converters endpoint."""
        with patch(
            "services.api_gateway.routers.snipers.phase2.Conversion"
        ) as mock_phase2_class:
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2
            mock_phase2.list_available_converters = MagicMock(
                return_value=["converter1", "converter2", "converter3"]
            )

            response = client.get("/api/snipers/phase2/converters")

            assert response.status_code == 200
            data = response.json()
            assert "converters" in data
            assert len(data["converters"]) == 3
            assert "converter1" in data["converters"]

    @pytest.mark.asyncio
    async def test_phase2_preview_conversion(self, client):
        """Test POST /preview endpoint."""
        with patch(
            "services.api_gateway.routers.snipers.phase2.Conversion"
        ) as mock_phase2_class:
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2

            mock_payload = MagicMock()
            mock_payload.original = "test_payload"
            mock_payload.converted = "test_payload_converted"
            mock_payload.chain_id = "chain-preview"
            mock_payload.converters_applied = ["converter1"]
            mock_payload.errors = None

            mock_result = MagicMock()
            mock_result.payloads = [mock_payload]

            mock_phase2.execute = AsyncMock(return_value=mock_result)

            response = client.post(
                "/api/snipers/phase2/preview",
                params={
                    "payload": "test_payload",
                    "converters": "converter1",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["original"] == "test_payload"
            assert data["converted"] == "test_payload_converted"

    @pytest.mark.asyncio
    async def test_phase2_preview_no_payloads(self, client):
        """Test preview error handling: no payloads converted."""
        with patch(
            "services.api_gateway.routers.snipers.phase2.Conversion"
        ) as mock_phase2_class:
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2

            mock_result = MagicMock()
            mock_result.payloads = []

            mock_phase2.execute = AsyncMock(return_value=mock_result)

            response = client.post(
                "/api/snipers/phase2/preview",
                params={
                    "payload": "test_payload",
                    "converters": "converter1",
                },
            )

            assert response.status_code == 500


# =============================================================================
# Phase 3: Attack Execution Tests
# =============================================================================


class TestPhase3Endpoints:
    """Tests for Phase 3 (Attack Execution) endpoints."""

    @pytest.mark.asyncio
    async def test_phase3_basic_request(self, client):
        """Test Phase 3 basic execution."""
        with patch(
            "services.api_gateway.routers.snipers.phase3.AttackExecution"
        ) as mock_phase3_class:
            mock_phase3 = AsyncMock()
            mock_phase3_class.return_value = mock_phase3

            # Mock attack response
            mock_attack_resp = MagicMock()
            mock_attack_resp.payload_index = 0
            mock_attack_resp.payload = "test_payload"
            mock_attack_resp.response = "target response"
            mock_attack_resp.status_code = 200
            mock_attack_resp.latency_ms = 100.5
            mock_attack_resp.error = None

            # Mock scorer result
            mock_scorer = MagicMock()
            mock_scorer.severity.value = "high"
            mock_scorer.confidence = 0.85
            mock_scorer.reasoning = "Detected jailbreak"

            # Mock composite score
            mock_composite = MagicMock()
            mock_composite.overall_severity.value = "high"
            mock_composite.total_score = 0.85
            mock_composite.is_successful = True
            mock_composite.scorer_results = {"jailbreak": mock_scorer}

            # Mock phase3 result
            mock_result = MagicMock()
            mock_result.campaign_id = "test-campaign"
            mock_result.target_url = "http://localhost:8000"
            mock_result.attack_responses = [mock_attack_resp]
            mock_result.composite_score = mock_composite
            mock_result.is_successful = True
            mock_result.overall_severity = "high"
            mock_result.total_score = 0.85
            mock_result.learned_chain = None
            mock_result.failure_analysis = None
            mock_result.adaptation_strategy = None

            mock_phase3.execute = AsyncMock(return_value=mock_result)

            payload = {
                "campaign_id": "test-campaign",
                "target_url": "http://localhost:8000",
                "payloads": [
                    {
                        "original": "payload",
                        "converted": "payload",
                        "chain_id": "chain-1",
                        "converters_applied": [],
                    }
                ],
            }
            response = client.post("/api/snipers/phase3", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["campaign_id"] == "test-campaign"
            assert data["target_url"] == "http://localhost:8000"
            assert data["is_successful"] is True
            assert data["overall_severity"] == "high"
            assert len(data["attack_responses"]) == 1

    @pytest.mark.asyncio
    async def test_phase3_with_custom_headers(self, client):
        """Test Phase 3 with custom HTTP headers."""
        with patch(
            "services.api_gateway.routers.snipers.phase3.AttackExecution"
        ) as mock_phase3_class:
            mock_phase3 = AsyncMock()
            mock_phase3_class.return_value = mock_phase3

            # Setup minimal mocks
            mock_attack_resp = MagicMock()
            mock_attack_resp.payload_index = 0
            mock_attack_resp.payload = "payload"
            mock_attack_resp.response = "response"
            mock_attack_resp.status_code = 200
            mock_attack_resp.latency_ms = 100.0
            mock_attack_resp.error = None

            mock_scorer = MagicMock()
            mock_scorer.severity.value = "low"
            mock_scorer.confidence = 0.1

            mock_composite = MagicMock()
            mock_composite.overall_severity.value = "low"
            mock_composite.total_score = 0.1
            mock_composite.is_successful = False
            mock_composite.scorer_results = {"jailbreak": mock_scorer}

            mock_result = MagicMock()
            mock_result.campaign_id = "test"
            mock_result.target_url = "http://localhost"
            mock_result.attack_responses = [mock_attack_resp]
            mock_result.composite_score = mock_composite
            mock_result.is_successful = False
            mock_result.overall_severity = "low"
            mock_result.total_score = 0.1
            mock_result.learned_chain = None
            mock_result.failure_analysis = None
            mock_result.adaptation_strategy = None

            mock_phase3.execute = AsyncMock(return_value=mock_result)

            payload = {
                "campaign_id": "test",
                "target_url": "http://localhost",
                "payloads": [
                    {
                        "original": "p",
                        "converted": "p",
                        "chain_id": "c",
                        "converters_applied": [],
                    }
                ],
                "headers": {
                    "X-Custom-Header": "custom-value",
                },
            }
            response = client.post("/api/snipers/phase3", json=payload)

            assert response.status_code == 200
            # Verify headers were passed
            call_args = mock_phase3_class.call_args
            assert call_args[1]["headers"]["X-Custom-Header"] == "custom-value"

    @pytest.mark.asyncio
    async def test_phase3_request_validation_empty_payloads(self, client):
        """Test Phase 3 validation: empty payloads."""
        payload = {
            "campaign_id": "test",
            "target_url": "http://localhost",
            "payloads": [],
        }
        response = client.post("/api/snipers/phase3", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_phase3_request_validation_timeout_range(self, client):
        """Test Phase 3 validation: timeout out of range."""
        payload = {
            "campaign_id": "test",
            "target_url": "http://localhost",
            "payloads": [
                {
                    "original": "p",
                    "converted": "p",
                    "chain_id": "c",
                    "converters_applied": [],
                }
            ],
            "timeout": 150,  # Max is 120
        }
        response = client.post("/api/snipers/phase3", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_phase3_list_scorers(self, client):
        """Test GET /scorers endpoint."""
        response = client.get("/api/snipers/phase3/scorers")

        assert response.status_code == 200
        data = response.json()
        assert "scorers" in data
        assert len(data["scorers"]) == 5

        scorer_names = [s["name"] for s in data["scorers"]]
        assert "jailbreak" in scorer_names
        assert "prompt_leak" in scorer_names
        assert "data_leak" in scorer_names
        assert "tool_abuse" in scorer_names
        assert "pii_exposure" in scorer_names


# =============================================================================
# Full Attack Tests
# =============================================================================


class TestFullAttackEndpoint:
    """Tests for full attack endpoint."""

    @pytest.mark.asyncio
    async def test_full_attack_basic_request(self, client):
        """Test full attack basic execution."""
        with patch(
            "services.api_gateway.routers.snipers.attack.execute_full_attack"
        ) as mock_execute:
            # Mock phase1 result
            mock_phase1 = MagicMock()
            mock_phase1.campaign_id = "test-campaign"
            mock_phase1.selected_chain = MagicMock(
                chain_id="chain-1",
                converter_names=["converter1"],
                defense_patterns=["pattern1"],
            )
            mock_phase1.articulated_payloads = ["payload1"]
            mock_phase1.framing_type = "qa_testing"
            mock_phase1.framing_types_used = ["qa_testing"]
            mock_phase1.context_summary = {}
            mock_phase1.garak_objective = "test"
            mock_phase1.defense_patterns = ["pattern1"]
            mock_phase1.tools_detected = []

            # Mock phase2 result
            mock_payload = MagicMock()
            mock_payload.original = "payload1"
            mock_payload.converted = "converted1"
            mock_payload.chain_id = "chain-1"
            mock_payload.converters_applied = ["converter1"]
            mock_payload.errors = None

            mock_phase2 = MagicMock()
            mock_phase2.chain_id = "chain-1"
            mock_phase2.converter_names = ["converter1"]
            mock_phase2.payloads = [mock_payload]
            mock_phase2.success_count = 1
            mock_phase2.error_count = 0

            # Mock phase3 result
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

            mock_composite = MagicMock()
            mock_composite.overall_severity.value = "high"
            mock_composite.total_score = 0.85
            mock_composite.is_successful = True
            mock_composite.scorer_results = {"jailbreak": mock_scorer}

            mock_phase3 = MagicMock()
            mock_phase3.campaign_id = "test-campaign"
            mock_phase3.target_url = "http://localhost"
            mock_phase3.attack_responses = [mock_attack_resp]
            mock_phase3.composite_score = mock_composite
            mock_phase3.is_successful = True
            mock_phase3.overall_severity = "high"
            mock_phase3.total_score = 0.85
            mock_phase3.learned_chain = None
            mock_phase3.failure_analysis = None
            mock_phase3.adaptation_strategy = None

            # Mock full result
            mock_result = MagicMock()
            mock_result.campaign_id = "test-campaign"
            mock_result.target_url = "http://localhost"
            mock_result.phase1 = mock_phase1
            mock_result.phase2 = mock_phase2
            mock_result.phase3 = mock_phase3
            mock_result.is_successful = True
            mock_result.overall_severity = "high"
            mock_result.total_score = 0.85
            mock_result.payloads_generated = 1
            mock_result.payloads_sent = 1

            mock_execute.return_value = mock_result

            payload = {
                "campaign_id": "test-campaign",
                "target_url": "http://localhost",
                "payload_count": 1,
            }
            response = client.post("/api/snipers/attack/full", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["campaign_id"] == "test-campaign"
            assert "scan_id" in data
            assert data["is_successful"] is True
            assert "phase1" in data
            assert "phase2" in data
            assert "phase3" in data

    @pytest.mark.asyncio
    async def test_full_attack_with_framing_override(self, client):
        """Test full attack with framing type override."""
        with patch(
            "services.api_gateway.routers.snipers.attack.execute_full_attack"
        ) as mock_execute:
            # Setup minimal mocks
            mock_phase1 = MagicMock()
            mock_phase1.campaign_id = "test"
            mock_phase1.selected_chain = None
            mock_phase1.articulated_payloads = ["p"]
            mock_phase1.framing_type = "compliance_audit"
            mock_phase1.framing_types_used = ["compliance_audit"]
            mock_phase1.context_summary = {}
            mock_phase1.garak_objective = "test"
            mock_phase1.defense_patterns = []
            mock_phase1.tools_detected = []

            mock_payload = MagicMock()
            mock_payload.original = "p"
            mock_payload.converted = "p"
            mock_payload.chain_id = "c"
            mock_payload.converters_applied = []
            mock_payload.errors = None

            mock_phase2 = MagicMock()
            mock_phase2.chain_id = "c"
            mock_phase2.converter_names = []
            mock_phase2.payloads = [mock_payload]
            mock_phase2.success_count = 1
            mock_phase2.error_count = 0

            mock_attack_resp = MagicMock()
            mock_attack_resp.payload_index = 0
            mock_attack_resp.payload = "p"
            mock_attack_resp.response = "r"
            mock_attack_resp.status_code = 200
            mock_attack_resp.latency_ms = 50.0
            mock_attack_resp.error = None

            mock_scorer = MagicMock()
            mock_scorer.severity.value = "low"
            mock_scorer.confidence = 0.1

            mock_composite = MagicMock()
            mock_composite.overall_severity.value = "low"
            mock_composite.total_score = 0.1
            mock_composite.is_successful = False
            mock_composite.scorer_results = {"jailbreak": mock_scorer}

            mock_phase3 = MagicMock()
            mock_phase3.campaign_id = "test"
            mock_phase3.target_url = "http://localhost"
            mock_phase3.attack_responses = [mock_attack_resp]
            mock_phase3.composite_score = mock_composite
            mock_phase3.is_successful = False
            mock_phase3.overall_severity = "low"
            mock_phase3.total_score = 0.1
            mock_phase3.learned_chain = None
            mock_phase3.failure_analysis = None
            mock_phase3.adaptation_strategy = None

            mock_result = MagicMock()
            mock_result.campaign_id = "test"
            mock_result.target_url = "http://localhost"
            mock_result.phase1 = mock_phase1
            mock_result.phase2 = mock_phase2
            mock_result.phase3 = mock_phase3
            mock_result.is_successful = False
            mock_result.overall_severity = "low"
            mock_result.total_score = 0.1
            mock_result.payloads_generated = 1
            mock_result.payloads_sent = 1

            mock_execute.return_value = mock_result

            payload = {
                "campaign_id": "test",
                "target_url": "http://localhost",
                "payload_count": 1,
                "framing_types": ["compliance_audit"],
            }
            response = client.post("/api/snipers/attack/full", json=payload)

            assert response.status_code == 200
            # Verify framing types were converted to strings
            call_args = mock_execute.call_args
            assert call_args[1]["framing_types"] == ["compliance_audit"]

    @pytest.mark.asyncio
    async def test_full_attack_request_validation_missing_campaign(self, client):
        """Test full attack validation: missing campaign."""
        payload = {
            "target_url": "http://localhost",
            "payload_count": 1,
        }
        response = client.post("/api/snipers/attack/full", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_full_attack_error_handling(self, client):
        """Test full attack error handling."""
        with patch(
            "services.api_gateway.routers.snipers.attack.execute_full_attack"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Attack failed")

            payload = {
                "campaign_id": "test",
                "target_url": "http://localhost",
                "payload_count": 1,
            }
            response = client.post("/api/snipers/attack/full", json=payload)

            assert response.status_code == 500
            assert "Full attack failed" in response.json()["detail"]


# =============================================================================
# Adaptive Attack Tests
# =============================================================================


class TestAdaptiveAttackEndpoint:
    """Tests for adaptive attack endpoint."""

    @pytest.mark.asyncio
    async def test_adaptive_attack_basic_request(self, client):
        """Test adaptive attack basic execution."""
        with patch(
            "services.api_gateway.routers.snipers.attack.execute_adaptive_attack"
        ) as mock_execute:
            mock_result = {
                "campaign_id": "test-campaign",
                "target_url": "http://localhost",
                "is_successful": True,
                "iteration": 2,  # 0-indexed, so 3 iterations total
                "best_score": 0.95,
                "best_iteration": 2,
                "iteration_history": [
                    {
                        "iteration": 1,
                        "is_successful": False,
                        "score": 0.3,
                        "framing": "qa_testing",
                        "converters": ["converter1"],
                    },
                    {
                        "iteration": 2,
                        "is_successful": False,
                        "score": 0.6,
                        "framing": "compliance_audit",
                        "converters": ["converter2"],
                    },
                    {
                        "iteration": 3,
                        "is_successful": True,
                        "score": 0.95,
                        "framing": "debugging",
                        "converters": ["converter3"],
                    },
                ],
                "phase3_result": None,
                "adaptation_reasoning": "Switched to debugging framing",
            }

            mock_execute.return_value = mock_result

            payload = {
                "campaign_id": "test-campaign",
                "target_url": "http://localhost",
                "max_iterations": 5,
            }
            response = client.post("/api/snipers/attack/adaptive", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["campaign_id"] == "test-campaign"
            assert "scan_id" in data
            assert data["is_successful"] is True
            assert data["total_iterations"] == 3
            assert data["best_score"] == 0.95
            assert len(data["iteration_history"]) == 3

    @pytest.mark.asyncio
    async def test_adaptive_attack_with_success_scorers(self, client):
        """Test adaptive attack with specific success scorers."""
        with patch(
            "services.api_gateway.routers.snipers.attack.execute_adaptive_attack"
        ) as mock_execute:
            mock_result = {
                "campaign_id": "test",
                "target_url": "http://localhost",
                "is_successful": False,
                "iteration": 4,
                "best_score": 0.5,
                "best_iteration": 2,
                "iteration_history": [],
                "phase3_result": None,
                "adaptation_reasoning": "No success scorers met threshold",
            }

            mock_execute.return_value = mock_result

            payload = {
                "campaign_id": "test",
                "target_url": "http://localhost",
                "max_iterations": 5,
                "success_scorers": ["jailbreak", "prompt_leak"],
                "success_threshold": 0.8,
            }
            response = client.post("/api/snipers/attack/adaptive", json=payload)

            assert response.status_code == 200
            # Verify scorers were converted to strings
            call_args = mock_execute.call_args
            assert call_args[1]["success_scorers"] == ["jailbreak", "prompt_leak"]
            assert call_args[1]["success_threshold"] == 0.8

    @pytest.mark.asyncio
    async def test_adaptive_attack_with_phase3_result(self, client):
        """Test adaptive attack with phase3 result in response."""
        with patch(
            "services.api_gateway.routers.snipers.attack.execute_adaptive_attack"
        ) as mock_execute:
            # Mock phase3 result
            mock_attack_resp = MagicMock()
            mock_attack_resp.payload_index = 0
            mock_attack_resp.payload = "payload"
            mock_attack_resp.response = "response"
            mock_attack_resp.status_code = 200
            mock_attack_resp.latency_ms = 100.0
            mock_attack_resp.error = None

            mock_scorer = MagicMock()
            mock_scorer.severity.value = "critical"
            mock_scorer.confidence = 0.95

            mock_composite = MagicMock()
            mock_composite.overall_severity.value = "critical"
            mock_composite.total_score = 0.95
            mock_composite.is_successful = True
            mock_composite.scorer_results = {"jailbreak": mock_scorer}

            mock_phase3 = MagicMock()
            mock_phase3.campaign_id = "test"
            mock_phase3.target_url = "http://localhost"
            mock_phase3.attack_responses = [mock_attack_resp]
            mock_phase3.composite_score = mock_composite
            mock_phase3.is_successful = True
            mock_phase3.overall_severity = "critical"
            mock_phase3.total_score = 0.95
            mock_phase3.failure_analysis = None
            mock_phase3.adaptation_strategy = None

            mock_result = {
                "campaign_id": "test",
                "target_url": "http://localhost",
                "is_successful": True,
                "iteration": 1,
                "best_score": 0.95,
                "best_iteration": 1,
                "iteration_history": [
                    {
                        "iteration": 1,
                        "is_successful": True,
                        "score": 0.95,
                    }
                ],
                "phase3_result": mock_phase3,
                "adaptation_reasoning": "Success on first iteration",
            }

            mock_execute.return_value = mock_result

            payload = {
                "campaign_id": "test",
                "target_url": "http://localhost",
                "max_iterations": 5,
            }
            response = client.post("/api/snipers/attack/adaptive", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["final_phase3"] is not None
            assert data["final_phase3"]["is_successful"] is True

    @pytest.mark.asyncio
    async def test_adaptive_attack_request_validation_max_iterations(self, client):
        """Test adaptive attack validation: max_iterations out of range."""
        payload = {
            "campaign_id": "test",
            "target_url": "http://localhost",
            "max_iterations": 25,  # Max is 20
        }
        response = client.post("/api/snipers/attack/adaptive", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_adaptive_attack_request_validation_threshold(self, client):
        """Test adaptive attack validation: success_threshold out of range."""
        payload = {
            "campaign_id": "test",
            "target_url": "http://localhost",
            "success_threshold": 1.5,  # Max is 1.0
        }
        response = client.post("/api/snipers/attack/adaptive", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_adaptive_attack_error_handling(self, client):
        """Test adaptive attack error handling."""
        with patch(
            "services.api_gateway.routers.snipers.attack.execute_adaptive_attack"
        ) as mock_execute:
            mock_execute.side_effect = ValueError("Invalid configuration")

            payload = {
                "campaign_id": "test",
                "target_url": "http://localhost",
            }
            response = client.post("/api/snipers/attack/adaptive", json=payload)

            assert response.status_code == 400
            assert "Invalid configuration" in response.json()["detail"]


# =============================================================================
# Response Serialization Tests
# =============================================================================


class TestResponseSerialization:
    """Tests for response model serialization."""

    @pytest.mark.asyncio
    async def test_phase1_response_serialization_with_chain(self, client):
        """Test Phase1Response serializes chain correctly."""
        with patch(
            "services.api_gateway.routers.snipers.phase1.PayloadArticulation"
        ) as mock_phase1_class:
            mock_phase1 = AsyncMock()
            mock_phase1_class.return_value = mock_phase1

            mock_chain = MagicMock()
            mock_chain.chain_id = "chain-test"
            mock_chain.converter_names = ["conv1", "conv2"]
            mock_chain.defense_patterns = ["def1", "def2"]

            mock_result = MagicMock()
            mock_result.campaign_id = "test"
            mock_result.selected_chain = mock_chain
            mock_result.articulated_payloads = ["p1", "p2"]
            mock_result.framing_type = "research"
            mock_result.framing_types_used = ["research"]
            mock_result.context_summary = {"key": "value"}
            mock_result.garak_objective = "test objective"
            mock_result.defense_patterns = ["def1", "def2"]
            mock_result.tools_detected = ["tool1"]

            mock_phase1.execute = AsyncMock(return_value=mock_result)

            payload = {"campaign_id": "test", "payload_count": 2}
            response = client.post("/api/snipers/phase1", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["selected_chain"]["chain_id"] == "chain-test"
            assert data["selected_chain"]["converter_names"] == ["conv1", "conv2"]
            assert data["selected_chain"]["defense_patterns"] == ["def1", "def2"]

    @pytest.mark.asyncio
    async def test_phase2_response_payload_errors(self, client):
        """Test Phase2Response serializes payload errors correctly."""
        with patch(
            "services.api_gateway.routers.snipers.phase2.Conversion"
        ) as mock_phase2_class:
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2

            mock_payload = MagicMock()
            mock_payload.original = "original"
            mock_payload.converted = ""
            mock_payload.chain_id = "chain-1"
            mock_payload.converters_applied = ["converter1"]
            mock_payload.errors = ["Conversion failed", "Timeout"]

            mock_result = MagicMock()
            mock_result.chain_id = "chain-1"
            mock_result.converter_names = ["converter1"]
            mock_result.payloads = [mock_payload]
            mock_result.success_count = 0
            mock_result.error_count = 1

            mock_phase2.execute = AsyncMock(return_value=mock_result)

            payload = {"payloads": ["original"]}
            response = client.post("/api/snipers/phase2", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert len(data["payloads"][0]["errors"]) == 2
            assert "Conversion failed" in data["payloads"][0]["errors"]

    @pytest.mark.asyncio
    async def test_phase3_response_multiple_scorers(self, client):
        """Test Phase3Response serializes multiple scorers correctly."""
        with patch(
            "services.api_gateway.routers.snipers.phase3.AttackExecution"
        ) as mock_phase3_class:
            mock_phase3 = AsyncMock()
            mock_phase3_class.return_value = mock_phase3

            mock_attack_resp = MagicMock()
            mock_attack_resp.payload_index = 0
            mock_attack_resp.payload = "payload"
            mock_attack_resp.response = "response"
            mock_attack_resp.status_code = 200
            mock_attack_resp.latency_ms = 100.0
            mock_attack_resp.error = None

            # Mock multiple scorers
            mock_scorer1 = MagicMock()
            mock_scorer1.severity.value = "high"
            mock_scorer1.confidence = 0.85

            mock_scorer2 = MagicMock()
            mock_scorer2.severity.value = "medium"
            mock_scorer2.confidence = 0.6

            mock_composite = MagicMock()
            mock_composite.overall_severity.value = "high"
            mock_composite.total_score = 0.85
            mock_composite.is_successful = True
            mock_composite.scorer_results = {
                "jailbreak": mock_scorer1,
                "data_leak": mock_scorer2,
            }

            mock_result = MagicMock()
            mock_result.campaign_id = "test"
            mock_result.target_url = "http://localhost"
            mock_result.attack_responses = [mock_attack_resp]
            mock_result.composite_score = mock_composite
            mock_result.is_successful = True
            mock_result.overall_severity = "high"
            mock_result.total_score = 0.85
            mock_result.learned_chain = None
            mock_result.failure_analysis = None
            mock_result.adaptation_strategy = None

            mock_phase3.execute = AsyncMock(return_value=mock_result)

            payload = {
                "campaign_id": "test",
                "target_url": "http://localhost",
                "payloads": [
                    {
                        "original": "p",
                        "converted": "p",
                        "chain_id": "c",
                        "converters_applied": [],
                    }
                ],
            }
            response = client.post("/api/snipers/phase3", json=payload)

            assert response.status_code == 200
            data = response.json()
            scorer_results = data["composite_score"]["scorer_results"]
            assert len(scorer_results) == 2
            assert scorer_results["jailbreak"]["severity"] == "high"
            assert scorer_results["data_leak"]["severity"] == "medium"


# =============================================================================
# Integration Tests: Response Consistency
# =============================================================================


class TestResponseConsistency:
    """Tests for response consistency across different request paths."""

    @pytest.mark.asyncio
    async def test_phase1_and_phase2_consistency(self, client):
        """Test that Phase 1 output can feed into Phase 2."""
        with patch(
            "services.api_gateway.routers.snipers.phase1.PayloadArticulation"
        ) as mock_phase1_class, patch(
            "services.api_gateway.routers.snipers.phase2.Conversion"
        ) as mock_phase2_class, patch(
            "services.api_gateway.routers.snipers.phase2.ConverterChain"
        ) as mock_chain_class:
            # Setup Phase 1
            mock_phase1 = AsyncMock()
            mock_phase1_class.return_value = mock_phase1

            mock_chain = MagicMock()
            mock_chain.chain_id = "chain-1"
            mock_chain.converter_names = ["converter1"]
            mock_chain.defense_patterns = []

            mock_result1 = MagicMock()
            mock_result1.campaign_id = "test"
            mock_result1.selected_chain = mock_chain
            mock_result1.articulated_payloads = ["payload1"]
            mock_result1.framing_type = "qa_testing"
            mock_result1.framing_types_used = ["qa_testing"]
            mock_result1.context_summary = {}
            mock_result1.garak_objective = "test"
            mock_result1.defense_patterns = []
            mock_result1.tools_detected = []

            mock_phase1.execute = AsyncMock(return_value=mock_result1)

            # Setup Phase 2
            mock_phase2 = AsyncMock()
            mock_phase2_class.return_value = mock_phase2

            mock_payload = MagicMock()
            mock_payload.original = "payload1"
            mock_payload.converted = "payload1_converted"
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
            mock_chain_class.from_converter_names = MagicMock(
                return_value=MagicMock()
            )

            # Execute Phase 1
            phase1_resp = client.post(
                "/api/snipers/phase1",
                json={"campaign_id": "test", "payload_count": 1},
            )
            assert phase1_resp.status_code == 200

            phase1_data = phase1_resp.json()

            # Use Phase 1 output as Phase 2 input
            phase2_resp = client.post(
                "/api/snipers/phase2/with-phase1",
                json={"phase1_response": phase1_data},
            )

            assert phase2_resp.status_code == 200
            phase2_data = phase2_resp.json()
            assert phase2_data["converter_names"] == phase1_data["selected_chain"]["converter_names"]
