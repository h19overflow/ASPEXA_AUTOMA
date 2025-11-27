"""Unit tests for connectivity layer (AsyncHttpClient).

Tests the centralized connectivity module that replaced
services/cartographer/tools/network.py.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from libs.connectivity import (
    AsyncHttpClient,
    ConnectionConfig,
    ConnectivityError,
    AuthenticationError,
    ClientResponse,
)


class TestAsyncHttpClient:
    """Test AsyncHttpClient from connectivity layer."""

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test successful HTTP request to target endpoint."""
        config = ConnectionConfig(
            endpoint_url="http://target.example.com/api",
            headers={"Authorization": "Bearer test-token"},
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Hello from target"})

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.close = AsyncMock()

            mock_post_context = MagicMock()
            mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post_context.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(return_value=mock_post_context)

            mock_session_class.return_value = mock_session

            async with AsyncHttpClient(config) as client:
                response = await client.send("Test question")

            assert response.text == "Hello from target"
            assert response.status_code == 200

    def test_connection_config_defaults(self):
        """Test ConnectionConfig default values."""
        config = ConnectionConfig(endpoint_url="http://example.com/api")

        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.message_field == "message"
        assert "response" in config.response_fields

    def test_connection_config_custom_values(self):
        """Test ConnectionConfig with custom values."""
        config = ConnectionConfig(
            endpoint_url="http://example.com/api",
            headers={"X-Custom": "value"},
            timeout=60,
            max_retries=5,
            message_field="prompt",
        )

        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.message_field == "prompt"
        assert config.headers["X-Custom"] == "value"

    def test_connection_config_validation(self):
        """Test ConnectionConfig validation."""
        with pytest.raises(ValueError):
            ConnectionConfig(endpoint_url="")

        with pytest.raises(ValueError):
            ConnectionConfig(endpoint_url="http://example.com", timeout=0)

        with pytest.raises(ValueError):
            ConnectionConfig(endpoint_url="http://example.com", max_retries=-1)

    def test_client_response_creation(self):
        """Test ClientResponse dataclass."""
        response = ClientResponse(
            text="Hello",
            raw={"response": "Hello"},
            status_code=200,
            latency_ms=50.5,
        )

        assert response.text == "Hello"
        assert response.status_code == 200
        assert response.latency_ms == 50.5
        assert response.raw["response"] == "Hello"

    def test_stats_tracking(self):
        """Test that stats are properly initialized."""
        config = ConnectionConfig(endpoint_url="http://example.com/api")
        client = AsyncHttpClient(config)

        stats = client.get_stats()
        assert stats["total_requests"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0.0
