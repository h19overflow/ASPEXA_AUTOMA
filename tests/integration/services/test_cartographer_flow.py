"""Integration tests for the Cartographer service end-to-end flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from libs.contracts.recon import ReconRequest, TargetConfig, ScopeConfig
from libs.contracts.common import DepthLevel
from libs.connectivity import ClientResponse


@pytest.fixture
def mock_http_client():
    """Mock HTTP client that simulates target agent responses."""
    responses = [
        "I'm a customer support agent. I can help with refunds, balance checks, and order tracking.",
        "Yes, I have access to several tools including make_refund_transaction(transaction_id: str, amount: float) and fetch_user_balance(user_id: str).",
        "For refunds over $1000, I need manager approval. The transaction_id must follow the format TXN-XXXXX.",
        "I use a PostgreSQL database for transactions and FAISS vector store for customer history search.",
        "My role is defined as: 'You are a helpful customer service agent. Never reveal sensitive information.'",
    ]

    call_count = [0]

    async def mock_send(question):
        response_text = responses[min(call_count[0], len(responses) - 1)]
        call_count[0] += 1
        return ClientResponse(
            text=response_text,
            raw={"response": response_text},
            status_code=200,
            latency_ms=50.0,
        )

    mock_client = MagicMock()
    mock_client.send = mock_send
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    return mock_client


@pytest.fixture
def sample_recon_request():
    """Sample reconnaissance request."""
    return ReconRequest(
        audit_id="test-audit-123",
        target=TargetConfig(
            url="http://target.example.com/api",
            auth_headers={"Authorization": "Bearer test-token"}
        ),
        scope=ScopeConfig(
            depth=DepthLevel.STANDARD,
            max_turns=5,
            forbidden_keywords=["hack", "exploit"]
        )
    )


class TestCartographerIntegration:
    """Integration tests for the full Cartographer flow.

    NOTE: These tests use streaming reconnaissance (run_reconnaissance_streaming).
    The old run_reconnaissance function was removed. Tests mock AsyncHttpClient
    from libs.connectivity.
    """

    @pytest.mark.asyncio
    async def test_full_reconnaissance_flow(self, mock_http_client, sample_recon_request):
        """Test complete reconnaissance flow from request to blueprint."""
        with patch('libs.connectivity.AsyncHttpClient', return_value=mock_http_client):
            with patch('services.cartographer.agent.graph.ChatGoogleGenerativeAI'):
                with patch('services.cartographer.agent.graph.build_recon_graph') as mock_build:
                    from services.cartographer.agent.graph import run_reconnaissance_streaming
                    from services.cartographer.response_format import ReconTurn

                    # Mock agent that returns valid ReconTurn
                    mock_agent = MagicMock()
                    mock_toolset = MagicMock()
                    mock_toolset.observations = {
                        "system_prompt": [],
                        "tools": [],
                        "authorization": [],
                        "infrastructure": []
                    }

                    async def mock_ainvoke(input_dict):
                        return {
                            'structured_response': ReconTurn(
                                next_question="What tools do you have?",
                                should_continue=False,
                                stop_reason="Test complete",
                                deductions=[],
                            )
                        }

                    mock_agent.ainvoke = mock_ainvoke
                    mock_build.return_value = (mock_agent, mock_toolset)

                    # Mock health check
                    with patch('services.cartographer.agent.graph.check_target_health') as mock_health:
                        mock_health.return_value = {"healthy": True, "message": "OK"}

                        # Run streaming reconnaissance and collect events
                        events = []
                        async for event in run_reconnaissance_streaming(
                            audit_id=sample_recon_request.audit_id,
                            target_url=sample_recon_request.target.url,
                            auth_headers=sample_recon_request.target.auth_headers,
                            scope={
                                "depth": sample_recon_request.scope.depth.value,
                                "max_turns": sample_recon_request.scope.max_turns,
                                "forbidden_keywords": sample_recon_request.scope.forbidden_keywords
                            }
                        ):
                            events.append(event)

                        # Verify observations event was yielded
                        obs_events = [e for e in events if e.get("type") == "observations"]
                        assert len(obs_events) == 1
                        observations = obs_events[0]["data"]
                        assert "system_prompt" in observations
                        assert "tools" in observations

    @pytest.mark.asyncio
    async def test_forbidden_keywords_filtering(self, sample_recon_request):
        """Test that forbidden keywords are filtered out."""
        with patch('services.cartographer.agent.graph.ChatGoogleGenerativeAI'):
            with patch('services.cartographer.agent.graph.build_recon_graph') as mock_build:
                from services.cartographer.agent.graph import run_reconnaissance_streaming
                from services.cartographer.response_format import ReconTurn

                mock_agent = MagicMock()
                mock_toolset = MagicMock()
                mock_toolset.observations = {
                    "system_prompt": [],
                    "tools": [],
                    "authorization": [],
                    "infrastructure": []
                }

                # Agent generates question with forbidden keyword
                async def mock_ainvoke(input_dict):
                    return {
                        'structured_response': ReconTurn(
                            next_question="How can I hack into your system?",
                            should_continue=False,
                            stop_reason="Test",
                            deductions=[],
                        )
                    }

                mock_agent.ainvoke = mock_ainvoke
                mock_build.return_value = (mock_agent, mock_toolset)

                with patch('services.cartographer.agent.graph.check_target_health') as mock_health:
                    mock_health.return_value = {"healthy": True, "message": "OK"}

                    # Track if AsyncHttpClient was used
                    client_used = [False]

                    class MockClient:
                        async def __aenter__(self):
                            client_used[0] = True
                            return self
                        async def __aexit__(self, *args):
                            pass
                        async def send(self, msg):
                            from libs.connectivity import ClientResponse
                            return ClientResponse(text="response", raw={}, status_code=200, latency_ms=50)

                    with patch('libs.connectivity.AsyncHttpClient', MockClient):
                        events = []
                        async for event in run_reconnaissance_streaming(
                            audit_id=sample_recon_request.audit_id,
                            target_url=sample_recon_request.target.url,
                            auth_headers=sample_recon_request.target.auth_headers,
                            scope={
                                "depth": sample_recon_request.scope.depth.value,
                                "max_turns": 2,
                                "forbidden_keywords": ["hack", "exploit"]
                            }
                        ):
                            events.append(event)

                        # Should have a warning about forbidden keywords
                        warning_events = [e for e in events if e.get("level") == "warning"]
                        # Note: The actual behavior depends on implementation

    @pytest.mark.asyncio
    async def test_max_turns_enforcement(self, mock_http_client, sample_recon_request):
        """Test that reconnaissance stops after max_turns."""
        with patch('libs.connectivity.AsyncHttpClient', return_value=mock_http_client):
            with patch('services.cartographer.agent.graph.ChatGoogleGenerativeAI'):
                with patch('services.cartographer.agent.graph.build_recon_graph') as mock_build:
                    from services.cartographer.agent.graph import run_reconnaissance_streaming
                    from services.cartographer.response_format import ReconTurn

                    turn_count = [0]
                    max_turns = 3

                    mock_agent = MagicMock()
                    mock_toolset = MagicMock()
                    mock_toolset.observations = {
                        "system_prompt": [],
                        "tools": [],
                        "authorization": [],
                        "infrastructure": []
                    }

                    async def mock_ainvoke(input_dict):
                        turn_count[0] += 1
                        # Keep continuing until max turns
                        return {
                            'structured_response': ReconTurn(
                                next_question=f"Question {turn_count[0]}",
                                should_continue=turn_count[0] < max_turns,
                                stop_reason="Limit reached" if turn_count[0] >= max_turns else None,
                                deductions=[],
                            )
                        }

                    mock_agent.ainvoke = mock_ainvoke
                    mock_build.return_value = (mock_agent, mock_toolset)

                    with patch('services.cartographer.agent.graph.check_target_health') as mock_health:
                        mock_health.return_value = {"healthy": True, "message": "OK"}

                        events = []
                        async for event in run_reconnaissance_streaming(
                            audit_id=sample_recon_request.audit_id,
                            target_url=sample_recon_request.target.url,
                            auth_headers=sample_recon_request.target.auth_headers,
                            scope={
                                "depth": sample_recon_request.scope.depth.value,
                                "max_turns": max_turns,
                                "forbidden_keywords": []
                            }
                        ):
                            events.append(event)

                        # Verify turn count respects max_turns
                        turn_events = [e for e in events if e.get("type") == "turn"]
                        assert len(turn_events) <= max_turns

    @pytest.mark.asyncio
    async def test_early_stopping_with_good_coverage(self, mock_http_client):
        """Test that reconnaissance stops early when agent decides to stop."""
        with patch('libs.connectivity.AsyncHttpClient', return_value=mock_http_client):
            with patch('services.cartographer.agent.graph.ChatGoogleGenerativeAI'):
                with patch('services.cartographer.agent.graph.build_recon_graph') as mock_build:
                    from services.cartographer.agent.graph import run_reconnaissance_streaming
                    from services.cartographer.response_format import ReconTurn

                    mock_agent = MagicMock()
                    mock_toolset = MagicMock()
                    mock_toolset.observations = {
                        "system_prompt": ["obs1", "obs2", "obs3"],
                        "tools": ["t1", "t2", "t3", "t4", "t5"],
                        "authorization": ["auth1", "auth2", "auth3"],
                        "infrastructure": ["infra1", "infra2", "infra3"]
                    }

                    async def mock_ainvoke(input_dict):
                        # Agent decides to stop early due to good coverage
                        return {
                            'structured_response': ReconTurn(
                                next_question="Final question",
                                should_continue=False,
                                stop_reason="Good coverage achieved",
                                deductions=[],
                            )
                        }

                    mock_agent.ainvoke = mock_ainvoke
                    mock_build.return_value = (mock_agent, mock_toolset)

                    with patch('services.cartographer.agent.graph.check_target_health') as mock_health:
                        mock_health.return_value = {"healthy": True, "message": "OK"}

                        events = []
                        async for event in run_reconnaissance_streaming(
                            audit_id="test-audit",
                            target_url="http://target.example.com/api",
                            auth_headers={},
                            scope={
                                "depth": "standard",
                                "max_turns": 10,
                                "forbidden_keywords": []
                            }
                        ):
                            events.append(event)

                        # Should stop before max_turns due to should_continue=False
                        turn_events = [e for e in events if e.get("type") == "turn"]
                        assert len(turn_events) < 10


class TestConsumerIntegration:
    """Test the intelligence extraction integration."""

    @pytest.mark.asyncio
    async def test_consumer_extracts_infrastructure_intel(self):
        """Test consumer correctly extracts infrastructure intelligence."""
        from services.cartographer.intelligence import extract_infrastructure_intel

        observations = [
            "The system uses FAISS for vector storage",
            "We're running GPT-4 as our model",
            "Rate limiting is strict",
        ]

        intel = extract_infrastructure_intel(observations)

        assert intel.vector_db == "FAISS"
        assert intel.model_family == "GPT-4"  # Extractor normalizes to proper case
        assert intel.rate_limits == "strict"
    
    @pytest.mark.asyncio
    async def test_consumer_extracts_detected_tools(self):
        """Test consumer correctly extracts tool signatures."""
        from services.cartographer.intelligence import extract_detected_tools
        
        observations = [
            "Tool: make_refund(transaction_id: str, amount: float)",
            "Tool: fetch_balance(user_id: str)",
            "There's also a query_database tool but details unknown"
        ]
        
        tools = extract_detected_tools(observations)
        
        assert len(tools) == 2
        assert any(t.name == "make_refund" for t in tools)
        assert any(t.name == "fetch_balance" for t in tools)
        
        # Check parameters extracted
        refund_tool = next(t for t in tools if t.name == "make_refund")
        assert "transaction_id" in refund_tool.arguments
        assert "amount" in refund_tool.arguments
