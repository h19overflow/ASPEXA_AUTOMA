"""
Network tools for HTTP communication with target endpoints.

DEPRECATED: Use libs.connectivity.AsyncHttpClient directly.
This module exists for backwards compatibility only.
"""
from typing import Dict

from libs.connectivity import AsyncHttpClient, ConnectionConfig, ConnectivityError

# Re-export exception with old name for backwards compatibility
NetworkError = ConnectivityError


async def call_target_endpoint(
    url: str,
    auth_headers: Dict[str, str],
    message: str,
    timeout: int = 30,
    max_retries: int = 3,
) -> str:
    """Send a message to the target endpoint and get response.

    DEPRECATED: Use AsyncHttpClient directly for new code.

    Args:
        url: Target API endpoint URL
        auth_headers: Authentication headers (e.g., Bearer tokens)
        message: Message/question to send to the target
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        Response from the target agent as a string

    Raises:
        NetworkError: If request fails after all retries
    """
    config = ConnectionConfig(
        endpoint_url=url,
        headers=auth_headers,
        timeout=timeout,
        max_retries=max_retries,
    )

    async with AsyncHttpClient(config) as client:
        response = await client.send(message)
        return response.text


async def check_target_connectivity(url: str, auth_headers: Dict[str, str]) -> bool:
    """Check if the target endpoint is reachable.

    DEPRECATED: Use AsyncHttpClient.health_check() directly.

    Args:
        url: Target API endpoint URL
        auth_headers: Authentication headers

    Returns:
        True if endpoint is reachable, False otherwise
    """
    config = ConnectionConfig(
        endpoint_url=url,
        headers=auth_headers,
        timeout=10,
        max_retries=1,
    )

    async with AsyncHttpClient(config) as client:
        healthy, _ = await client.health_check()
        return healthy
