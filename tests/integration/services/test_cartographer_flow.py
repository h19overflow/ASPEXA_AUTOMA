"""Integration tests for the Cartographer service end-to-end flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from libs.contracts.recon import ReconRequest, TargetConfig, ScopeConfig
from libs.contracts.common import DepthLevel


@pytest.fixture
def mock_target_endpoint():
    """Mock target endpoint that simulates a vulnerable agent."""
    responses = [
        "I'm a customer support agent. I can help with refunds, balance checks, and order tracking.",
        "Yes, I have access to several tools including make_refund_transaction(transaction_id: str, amount: float) and fetch_user_balance(user_id: str).",
        "For refunds over $1000, I need manager approval. The transaction_id must follow the format TXN-XXXXX.",
        "I use a PostgreSQL database for transactions and FAISS vector store for customer history search.",
        "My role is defined as: 'You are a helpful customer service agent. Never reveal sensitive information.'",
    ]
    
    call_count = [0]
    
    async def mock_call(url, auth_headers, message, timeout=30, max_retries=3):
        response = responses[min(call_count[0], len(responses) - 1)]
        call_count[0] += 1
        return response
    
    return mock_call


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
    """Integration tests for the full Cartographer flow."""
    
    @pytest.mark.asyncio
    async def test_full_reconnaissance_flow(self, mock_target_endpoint, sample_recon_request):
        """Test complete reconnaissance flow from request to blueprint."""
        with patch('services.cartographer.tools.network.call_target_endpoint', mock_target_endpoint):
            with patch('services.cartographer.agent.graph.ChatGoogleGenerativeAI') as mock_llm:
                # Mock the LLM to generate strategic questions
                mock_model = MagicMock()
                mock_llm.return_value = mock_model
                
                # Import after patching
                from services.cartographer.agent.graph import run_reconnaissance
                
                # Mock agent to simulate question generation and tool usage
                async def mock_ainvoke(input_dict):
                    messages = input_dict.get('messages', [])
                    # Simulate agent asking questions
                    return {
                        'messages': messages + [
                            ('ai', 'What tools and capabilities do you have?')
                        ]
                    }
                
                with patch('services.cartographer.agent.graph.create_agent') as mock_create:
                    mock_agent = MagicMock()
                    mock_agent.ainvoke = mock_ainvoke
                    mock_create.return_value = (mock_agent, MagicMock())
                    
                    # Run reconnaissance
                    observations = await run_reconnaissance(
                        audit_id=sample_recon_request.audit_id,
                        target_url=sample_recon_request.target.url,
                        auth_headers=sample_recon_request.target.auth_headers,
                        scope={
                            "depth": sample_recon_request.scope.depth.value,
                            "max_turns": sample_recon_request.scope.max_turns,
                            "forbidden_keywords": sample_recon_request.scope.forbidden_keywords
                        }
                    )
                    
                    # Verify observations structure
                    assert isinstance(observations, dict)
                    assert "system_prompt" in observations
                    assert "tools" in observations
                    assert "authorization" in observations
                    assert "infrastructure" in observations
    
    @pytest.mark.asyncio
    async def test_forbidden_keywords_filtering(self, sample_recon_request):
        """Test that forbidden keywords are filtered out."""
        with patch('services.cartographer.tools.network.call_target_endpoint') as mock_call:
            with patch('services.cartographer.agent.graph.ChatGoogleGenerativeAI'):
                from services.cartographer.agent.graph import run_reconnaissance
                
                async def mock_ainvoke(input_dict):
                    # Simulate agent generating a question with forbidden keyword
                    return {
                        'messages': [
                            ('ai', 'How can I hack into your system?')
                        ]
                    }
                
                with patch('services.cartographer.agent.graph.create_agent') as mock_create:
                    mock_agent = MagicMock()
                    mock_agent.ainvoke = mock_ainvoke
                    mock_toolset = MagicMock()
                    mock_toolset.observations = {
                        "system_prompt": [],
                        "tools": [],
                        "authorization": [],
                        "infrastructure": []
                    }
                    mock_create.return_value = (mock_agent, mock_toolset)
                    
                    await run_reconnaissance(
                        audit_id=sample_recon_request.audit_id,
                        target_url=sample_recon_request.target.url,
                        auth_headers=sample_recon_request.target.auth_headers,
                        scope={
                            "depth": sample_recon_request.scope.depth.value,
                            "max_turns": 2,
                            "forbidden_keywords": ["hack", "exploit"]
                        }
                    )
                    
                    # Network call should not be made for forbidden questions
                    mock_call.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_max_turns_enforcement(self, mock_target_endpoint, sample_recon_request):
        """Test that reconnaissance stops after max_turns."""
        with patch('services.cartographer.tools.network.call_target_endpoint', mock_target_endpoint):
            with patch('services.cartographer.agent.graph.ChatGoogleGenerativeAI'):
                from services.cartographer.agent.graph import run_reconnaissance
                
                turn_count = [0]
                
                async def mock_ainvoke(input_dict):
                    turn_count[0] += 1
                    return {
                        'messages': [
                            ('ai', f'Question {turn_count[0]}')
                        ]
                    }
                
                with patch('services.cartographer.agent.graph.create_agent') as mock_create:
                    mock_agent = MagicMock()
                    mock_agent.ainvoke = mock_ainvoke
                    mock_toolset = MagicMock()
                    mock_toolset.observations = {
                        "system_prompt": [],
                        "tools": [],
                        "authorization": [],
                        "infrastructure": []
                    }
                    mock_create.return_value = (mock_agent, mock_toolset)
                    
                    max_turns = 3
                    await run_reconnaissance(
                        audit_id=sample_recon_request.audit_id,
                        target_url=sample_recon_request.target.url,
                        auth_headers=sample_recon_request.target.auth_headers,
                        scope={
                            "depth": sample_recon_request.scope.depth.value,
                            "max_turns": max_turns,
                            "forbidden_keywords": []
                        }
                    )
                    
                    # Should stop after max_turns
                    assert turn_count[0] <= max_turns
    
    @pytest.mark.asyncio
    async def test_early_stopping_with_good_coverage(self, mock_target_endpoint):
        """Test that reconnaissance stops early when good coverage is achieved."""
        with patch('services.cartographer.tools.network.call_target_endpoint', mock_target_endpoint):
            with patch('services.cartographer.agent.graph.ChatGoogleGenerativeAI'):
                from services.cartographer.agent.graph import run_reconnaissance
                
                turn_count = [0]
                
                async def mock_ainvoke(input_dict):
                    turn_count[0] += 1
                    return {
                        'messages': [
                            ('ai', f'Question {turn_count[0]}')
                        ]
                    }
                
                with patch('services.cartographer.agent.graph.create_agent') as mock_create:
                    mock_agent = MagicMock()
                    mock_agent.ainvoke = mock_ainvoke
                    
                    # Mock toolset with good coverage
                    mock_toolset = MagicMock()
                    mock_toolset.observations = {
                        "system_prompt": ["obs1", "obs2", "obs3"],
                        "tools": ["t1", "t2", "t3", "t4", "t5"],
                        "authorization": ["auth1", "auth2", "auth3"],
                        "infrastructure": ["infra1", "infra2", "infra3"]
                    }
                    mock_create.return_value = (mock_agent, mock_toolset)
                    
                    await run_reconnaissance(
                        audit_id="test-audit",
                        target_url="http://target.example.com/api",
                        auth_headers={},
                        scope={
                            "depth": "standard",
                            "max_turns": 10,
                            "forbidden_keywords": []
                        }
                    )
                    
                    # Should stop before max_turns due to good coverage
                    assert turn_count[0] < 10


class TestConsumerIntegration:
    """Test the consumer integration with reconnaissance."""
    
    @pytest.mark.asyncio
    async def test_consumer_handles_recon_request(self, sample_recon_request):
        """Test consumer processes IF-01 request and publishes IF-02 blueprint."""
        with patch('services.cartographer.consumer.run_reconnaissance') as mock_recon:
            # Mock reconnaissance results
            mock_recon.return_value = {
                "system_prompt": [
                    "You are a customer service agent",
                    "Never reveal sensitive information"
                ],
                "tools": [
                    "Tool: make_refund_transaction(transaction_id: str, amount: float)",
                    "Tool: fetch_user_balance(user_id: str)"
                ],
                "authorization": [
                    "Refunds over $1000 require approval",
                    "Transaction ID format: TXN-XXXXX"
                ],
                "infrastructure": [
                    "Database: PostgreSQL",
                    "Vector Store: FAISS"
                ]
            }
            
            with patch('services.cartographer.consumer.publish_recon_finished') as mock_publish:
                from services.cartographer.consumer import handle_recon_request
                
                # Process request
                await handle_recon_request(sample_recon_request.model_dump())
                
                # Verify reconnaissance was called
                mock_recon.assert_called_once()
                
                # Verify blueprint was published
                mock_publish.assert_called_once()
                
                # Check published blueprint structure
                call_args = mock_publish.call_args[0][0]
                assert call_args['audit_id'] == sample_recon_request.audit_id
                assert 'intelligence' in call_args
                assert 'detected_tools' in call_args['intelligence']
    
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
