"""
Sync HTTP client with connection pooling.

Uses requests library for synchronous HTTP requests with session
management, retry strategy, and standardized response extraction.
"""
import logging
import time
from typing import Any, Dict, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


class SyncHttpClient:
    """Sync HTTP client with connection pooling.

    Features:
    - Connection pooling via requests.Session
    - Configurable retry strategy using urllib3.Retry
    - Retries on 5xx status codes
    - Thread-safe session management
    - Response extraction using shared ResponseExtractor
    - Stats tracking

    Usage:
        config = ConnectionConfig(endpoint_url="http://target.com/chat")
        client = SyncHttpClient(config)
        response = client.send("Hello")
        print(response.text)
        client.close()
    """

    def __init__(self, config: ConnectionConfig):
        """Initialize sync HTTP client.

        Args:
            config: Connection configuration
        """
        self.config = config
        self._extractor = ResponseExtractor(config.response_fields)
        self._stats: Dict[str, int] = {"success": 0, "errors": 0}
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create session with retry adapter.

        Returns:
            Configured requests.Session
        """
        session = requests.Session()

        # Set default headers
        session.headers.update(
            {"Content-Type": "application/json", **self.config.headers}
        )

        # Configure retry strategy
        if self.config.max_retries > 0:
            retry_strategy = Retry(
                total=self.config.max_retries,
                backoff_factor=self.config.retry_backoff,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["POST", "GET"],
            )
            # Pool size for parallel execution
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=15,
                pool_maxsize=30,
            )
            session.mount("http://", adapter)
            session.mount("https://", adapter)

        return session

    def send(self, message: str) -> ClientResponse:
        """Send message to endpoint.

        Args:
            message: Message to send

        Returns:
            ClientResponse with extracted text and metadata

        Raises:
            ConnectivityError: On connection failure
            AuthenticationError: On 401/403
            ConnectionTimeoutError: On timeout
        """
        payload = {self.config.message_field: message}
        start_time = time.time()

        try:
            response = self._session.post(
                self.config.endpoint_url,
                json=payload,
                timeout=self.config.timeout,
            )
            latency_ms = (time.time() - start_time) * 1000

            # Auth errors
            if response.status_code in (401, 403):
                self._stats["errors"] += 1
                raise AuthenticationError(
                    response.status_code, self.config.endpoint_url
                )

            # Rate limit
            if response.status_code == 429:
                self._stats["errors"] += 1
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(
                    self.config.endpoint_url,
                    int(retry_after) if retry_after else None,
                )

            # Raise for other HTTP errors
            response.raise_for_status()

            # Parse response
            try:
                data = response.json()
                text = self._extractor.extract(data)
                self._stats["success"] += 1
                return ClientResponse(
                    text=text,
                    raw=data,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                )
            except ValueError:
                # Non-JSON response
                text = response.text
                self._stats["success"] += 1
                return ClientResponse(
                    text=text,
                    raw={"raw_text": text},
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                )

        except requests.ConnectionError as e:
            self._stats["errors"] += 1
            raise ConnectivityError(
                f"Connection failed to {self.config.endpoint_url}: {e}"
            )
        except requests.Timeout as e:
            self._stats["errors"] += 1
            raise ConnectionTimeoutError(
                self.config.timeout, self.config.endpoint_url
            )
        except requests.HTTPError as e:
            self._stats["errors"] += 1
            status_code = e.response.status_code if e.response else "unknown"
            raise ConnectivityError(f"HTTP error {status_code}: {e}")
        except (AuthenticationError, RateLimitError):
            raise
        except Exception as e:
            self._stats["errors"] += 1
            raise ConnectivityError(f"Unexpected error: {type(e).__name__}: {e}")

    def send_sync(self, message: str) -> ClientResponse:
        """Alias for send() - protocol compatibility.

        Args:
            message: Message to send

        Returns:
            ClientResponse with extracted text and metadata
        """
        return self.send(message)

    def health_check(self) -> Tuple[bool, Optional[str]]:
        """Check if endpoint is reachable.

        Returns:
            Tuple of (is_healthy, error_message)
        """
        try:
            # Try HEAD request to base URL first
            base_url = self.config.endpoint_url.rsplit("/", 1)[0]
            response = self._session.head(base_url, timeout=5)
            return True, None
        except requests.RequestException as e:
            # Fall back to simple POST
            try:
                payload = {self.config.message_field: "health_check"}
                response = self._session.post(
                    self.config.endpoint_url,
                    json=payload,
                    timeout=5,
                )
                if response.status_code in (200, 201):
                    return True, None
                return False, f"HTTP {response.status_code}"
            except requests.Timeout:
                return False, "Connection timeout"
            except requests.ConnectionError as e:
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

    def close(self) -> None:
        """Close the session and release resources."""
        if self._session:
            self._session.close()

    def __del__(self) -> None:
        """Clean up session on destruction."""
        self.close()
