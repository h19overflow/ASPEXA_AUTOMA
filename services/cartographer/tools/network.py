"""Network tools for HTTP communication with target endpoints."""
# TODO: This should be moved to a global tools file and inserted into each agent's graph.
import aiohttp
import asyncio
from typing import Dict, Optional


class NetworkError(Exception):
    """Custom exception for network-related errors."""
    pass


async def call_target_endpoint(
    url: str,
    auth_headers: Dict[str, str],
    message: str,
    timeout: int = 30,
    max_retries: int = 3
) -> str:
    """Send a message to the target endpoint and get response.
    
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
    headers = {
        "Content-Type": "application/json",
        **auth_headers
    }
    
    payload = {"message": message}
    
    last_error = None
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", result.get("message", str(result)))
                    elif response.status in [401, 403]:
                        # Authentication/Authorization errors shouldn't retry
                        raise NetworkError(f"Authentication failed: {response.status}")
                    else:
                        # Other errors might be transient
                        error_text = await response.text()
                        last_error = f"HTTP {response.status}: {error_text}"
                        
        except asyncio.TimeoutError:
            last_error = f"Request timeout after {timeout}s"
        except aiohttp.ClientError as e:
            last_error = f"Client error: {str(e)}"
        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
        
        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)
    
    # All retries failed
    raise NetworkError(f"Failed to reach target after {max_retries} attempts. Last error: {last_error}")


async def check_target_connectivity(url: str, auth_headers: Dict[str, str]) -> bool:
    """Check if the target endpoint is reachable.
    
    Args:
        url: Target API endpoint URL
        auth_headers: Authentication headers
    
    Returns:
        True if endpoint is reachable, False otherwise
    """
    try:
        response = await call_target_endpoint(
            url=url,
            auth_headers=auth_headers,
            message="Hello",
            timeout=10,
            max_retries=1
        )
        return True
    except NetworkError:
        return False
