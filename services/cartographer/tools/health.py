"""Health check utilities for target endpoints.

Provides functions to verify target endpoint availability and health status
before initiating reconnaissance operations.
"""
import asyncio
import aiohttp
from typing import Dict, Any


async def check_target_health(url: str, auth_headers: dict, timeout: int = 10) -> Dict[str, Any]:
    """Check if target endpoint is reachable.

    Performs a lightweight health check by sending a test message to the target
    endpoint and verifying the response status.

    Args:
        url: Target API endpoint URL
        auth_headers: Authentication headers (e.g., Bearer tokens)
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Dictionary containing:
            - healthy (bool): Whether target is reachable and responding
            - message (str): Human-readable status message
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Try a simple POST with empty/test message
            payload = {"message": "health check"}
            async with session.post(
                url,
                json=payload,
                headers=auth_headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status < 500:
                    return {"healthy": True, "message": f"Target reachable (HTTP {response.status})"}
                else:
                    return {"healthy": False, "message": f"Target returned server error (HTTP {response.status})"}
    except aiohttp.ClientConnectorError:
        return {"healthy": False, "message": "Connection refused - target server not running"}
    except asyncio.TimeoutError:
        return {"healthy": False, "message": f"Connection timeout after {timeout}s"}
    except Exception as e:
        return {"healthy": False, "message": f"Connection failed: {str(e)}"}
