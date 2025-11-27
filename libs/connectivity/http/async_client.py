"""
Async HTTP client for target communication.

Uses aiohttp for asynchronous HTTP requests with connection pooling,
retry logic, and standardized response extraction.
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple

import aiohttp

from libs.connectivity.contracts import (
    AuthenticationError,
    ClientResponse,
    ConnectionConfig,
    ConnectionTimeoutError,
    ConnectivityError,
    RateLimitError,
)
from libs.connectivity.response import ResponseExtractor

logger = logging.getLogger(__name__)


class AsyncHttpClient:
    """Async HTTP client for target communication.

    Features:
    - Async context manager for session lifecycle
    - Exponential backoff retry logic
    - Configurable timeout per request
    - Auth header injection from config
    - Response extraction using shared ResponseExtractor
    - Stats tracking (success/error counts)

    Usage:
        config = ConnectionConfig(endpoint_url="http://target.com/chat")
        async with AsyncHttpClient(config) as client:
            response = await client.send("Hello")
            print(response.text)
    """

    def __init__(self, config: ConnectionConfig):
        """Initialize async HTTP client.

        Args:
            config: Connection configuration
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._extractor = ResponseExtractor(config.response_fields)
        self._stats: Dict[str, int] = {"success": 0, "errors": 0}

    async def __aenter__(self) -> "AsyncHttpClient":
        """Create aiohttp session on context entry."""
        headers = {"Content-Type": "application/json", **self.config.headers}
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Close session on context exit."""
        if self._session:
            await self._session.close()
            self._session = None

    async def send(self, message: str) -> ClientResponse:
        """Send message to endpoint with retry logic.

        Args:
            message: Message to send

        Returns:
            ClientResponse with extracted text and metadata

        Raises:
            ConnectivityError: On connection failure after all retries
            AuthenticationError: On 401/403 (no retry)
            ConnectionTimeoutError: On timeout after all retries
        """
        if not self._session:
            raise ConnectivityError("Client not initialized. Use 'async with' context.")

        payload = {self.config.message_field: message}
        last_error: Optional[str] = None
        start_time = time.time()

        for attempt in range(self.config.max_retries):
            try:
                async with self._session.post(
                    self.config.endpoint_url,
                    json=payload,
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000

                    # Auth errors - no retry
                    if response.status in (401, 403):
                        self._stats["errors"] += 1
                        raise AuthenticationError(
                            response.status, self.config.endpoint_url
                        )

                    # Rate limit - could retry with backoff
                    if response.status == 429:
                        self._stats["errors"] += 1
                        retry_after = response.headers.get("Retry-After")
                        raise RateLimitError(
                            self.config.endpoint_url,
                            int(retry_after) if retry_after else None,
                        )

                    # Success
                    if response.status == 200:
                        try:
                            data = await response.json()
                            text = self._extractor.extract(data)
                            self._stats["success"] += 1
                            return ClientResponse(
                                text=text,
                                raw=data,
                                status_code=response.status,
                                latency_ms=latency_ms,
                            )
                        except Exception as e:
                            # Non-JSON response
                            text = await response.text()
                            self._stats["success"] += 1
                            return ClientResponse(
                                text=text,
                                raw={"raw_text": text},
                                status_code=response.status,
                                latency_ms=latency_ms,
                            )

                    # Other errors - might be transient
                    error_text = await response.text()
                    last_error = f"HTTP {response.status}: {error_text[:200]}"

            except asyncio.TimeoutError:
                last_error = f"Request timeout after {self.config.timeout}s"
            except aiohttp.ClientError as e:
                last_error = f"Client error: {str(e)}"
            except (AuthenticationError, RateLimitError):
                raise
            except Exception as e:
                last_error = f"Unexpected error: {type(e).__name__}: {str(e)}"

            # Wait before retry (exponential backoff)
            if attempt < self.config.max_retries - 1:
                backoff = (2**attempt) * self.config.retry_backoff
                logger.debug(
                    f"Retry {attempt + 1}/{self.config.max_retries} "
                    f"after {backoff}s: {last_error}"
                )
                await asyncio.sleep(backoff)

        # All retries failed
        self._stats["errors"] += 1
        if "timeout" in (last_error or "").lower():
            raise ConnectionTimeoutError(
                self.config.timeout, self.config.endpoint_url
            )
        raise ConnectivityError(
            f"Failed after {self.config.max_retries} attempts: {last_error}"
        )

    async def health_check(self) -> Tuple[bool, Optional[str]]:
        """Check if endpoint is reachable.

        Returns:
            Tuple of (is_healthy, error_message)
        """
        try:
            # Create temporary session for health check
            headers = {"Content-Type": "application/json", **self.config.headers}
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(
                headers=headers, timeout=timeout
            ) as session:
                # Try a simple request
                payload = {self.config.message_field: "health_check"}
                async with session.post(
                    self.config.endpoint_url,
                    json=payload,
                ) as response:
                    if response.status in (200, 201):
                        return True, None
                    return False, f"HTTP {response.status}"

        except asyncio.TimeoutError:
            return False, "Connection timeout"
        except aiohttp.ClientError as e:
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics.

        Returns:
            Dictionary with success, error counts and success rate
        """
        total = self._stats["success"] + self._stats["errors"]
        return {
            "total_requests": total,
            "successful": self._stats["success"],
            "failed": self._stats["errors"],
            "success_rate": self._stats["success"] / total if total > 0 else 0.0,
        }
