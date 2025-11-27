"""
Connectivity contracts: protocols, exceptions, and data structures.

This module defines the core abstractions for the connectivity layer:
- ClientProtocol: Interface that all connectivity clients must implement
- ConnectionConfig: Configuration for client connections
- ClientResponse: Standardized response wrapper
- Exception hierarchy for connectivity errors
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple


# =============================================================================
# Exception Hierarchy
# =============================================================================


class ConnectivityError(Exception):
    """Base exception for all connectivity-related errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class ConnectionTimeoutError(ConnectivityError):
    """Raised when a connection or request times out."""

    def __init__(self, timeout_seconds: int, endpoint: str):
        super().__init__(f"Request to {endpoint} timed out after {timeout_seconds}s")
        self.timeout_seconds = timeout_seconds
        self.endpoint = endpoint


class AuthenticationError(ConnectivityError):
    """Raised when authentication fails (401/403)."""

    def __init__(self, status_code: int, endpoint: str):
        super().__init__(f"Authentication failed with status {status_code} for {endpoint}")
        self.status_code = status_code
        self.endpoint = endpoint


class RateLimitError(ConnectivityError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(self, endpoint: str, retry_after: Optional[int] = None):
        msg = f"Rate limit exceeded for {endpoint}"
        if retry_after:
            msg += f", retry after {retry_after}s"
        super().__init__(msg)
        self.endpoint = endpoint
        self.retry_after = retry_after


class ResponseParseError(ConnectivityError):
    """Raised when response cannot be parsed."""

    def __init__(self, message: str, raw_response: Optional[str] = None):
        super().__init__(message)
        self.raw_response = raw_response


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class ConnectionConfig:
    """Configuration for client connections.

    Attributes:
        endpoint_url: Target endpoint URL
        headers: HTTP headers to include in requests
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for transient failures
        retry_backoff: Backoff factor for retry delays (exponential)
        message_field: Field name for outgoing message in request body
        response_fields: Priority-ordered list of fields to extract from response
    """

    endpoint_url: str
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    max_retries: int = 3
    retry_backoff: float = 1.0
    message_field: str = "message"
    response_fields: List[str] = field(
        default_factory=lambda: ["response", "text", "output", "message"]
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.endpoint_url:
            raise ValueError("endpoint_url is required")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


@dataclass
class ClientResponse:
    """Standardized response from connectivity clients.

    Attributes:
        text: Extracted text response
        raw: Original raw response data
        status_code: HTTP status code (if applicable)
        latency_ms: Request latency in milliseconds
    """

    text: str
    raw: Dict[str, Any] = field(default_factory=dict)
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None


# =============================================================================
# Protocol Definition
# =============================================================================


class ClientProtocol(Protocol):
    """Protocol that all connectivity clients must implement.

    This defines the interface for both sync and async HTTP clients,
    WebSocket clients, and future protocol implementations.
    """

    async def send(self, message: str) -> ClientResponse:
        """Send a message and get response (async version).

        Args:
            message: Message to send to the endpoint

        Returns:
            ClientResponse with extracted text and metadata

        Raises:
            ConnectivityError: On connection or request failure
        """
        ...

    def send_sync(self, message: str) -> ClientResponse:
        """Send a message and get response (sync version).

        Args:
            message: Message to send to the endpoint

        Returns:
            ClientResponse with extracted text and metadata

        Raises:
            ConnectivityError: On connection or request failure
        """
        ...

    async def health_check(self) -> Tuple[bool, Optional[str]]:
        """Check if endpoint is reachable.

        Returns:
            Tuple of (is_healthy, error_message)
        """
        ...

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics.

        Returns:
            Dictionary with stats like success_count, error_count, etc.
        """
        ...
