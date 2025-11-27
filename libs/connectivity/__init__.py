"""
Connectivity layer for HTTP and future protocol clients.

This package provides centralized client implementations for
communicating with target endpoints, replacing scattered implementations
across services.

Usage:
    from libs.connectivity import ConnectionConfig, AsyncHttpClient, SyncHttpClient

    # Async client
    config = ConnectionConfig(endpoint_url="http://target.com/chat")
    async with AsyncHttpClient(config) as client:
        response = await client.send("Hello")
        print(response.text)

    # Sync client
    client = SyncHttpClient(config)
    response = client.send("Hello")
    client.close()
"""
from .contracts import (
    ClientProtocol,
    ClientResponse,
    ConnectionConfig,
    ConnectivityError,
    ConnectionTimeoutError,
    AuthenticationError,
    RateLimitError,
    ResponseParseError,
)
from .config import ConnectionSettings, get_settings
from .response import ResponseExtractor
from .http import AsyncHttpClient, SyncHttpClient

__all__ = [
    # Contracts
    "ClientProtocol",
    "ClientResponse",
    "ConnectionConfig",
    # Exceptions
    "ConnectivityError",
    "ConnectionTimeoutError",
    "AuthenticationError",
    "RateLimitError",
    "ResponseParseError",
    # Config
    "ConnectionSettings",
    "get_settings",
    # Response
    "ResponseExtractor",
    # HTTP Clients
    "AsyncHttpClient",
    "SyncHttpClient",
]
