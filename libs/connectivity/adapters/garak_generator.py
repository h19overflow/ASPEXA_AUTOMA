"""
Garak generator adapter using centralized HTTP client.

Provides a Garak-compatible generator that wraps SyncHttpClient,
serving as a drop-in replacement for the original HttpGenerator.
"""
import logging
from typing import List, Optional, Tuple

import garak.generators.base

from libs.connectivity import ConnectionConfig, SyncHttpClient
from libs.connectivity.contracts import ConnectivityError

logger = logging.getLogger(__name__)


class GarakHttpGenerator(garak.generators.base.Generator):
    """Generator that uses centralized SyncHttpClient.

    Drop-in replacement for services/swarm/garak_scanner/http_generator.py.
    Implements the Garak Generator interface while delegating HTTP logic
    to the centralized connectivity layer.

    Supports multiple response formats:
    - {"response": "..."} - Standard format
    - {"text": "..."} - Alternative format
    - {"output": "..."} - Alternative format
    - {"message": "..."} - Chat format
    - {"choices": [{"message": {"content": "..."}}]} - OpenAI format
    """

    def __init__(
        self,
        endpoint_url: str,
        headers: Optional[dict] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        message_field: str = "prompt",
    ):
        """Initialize Garak HTTP generator.

        Args:
            endpoint_url: Target endpoint URL
            headers: HTTP headers to include in requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_backoff: Backoff factor for retries
            message_field: Field name for the prompt in request body
                          (defaults to "prompt" for Garak compatibility)
        """
        # Set name BEFORE calling super().__init__() because parent class needs it
        self.name = "GarakHttpGenerator"
        self.generations = 1

        super().__init__()

        # Create config and client
        self._config = ConnectionConfig(
            endpoint_url=endpoint_url,
            headers=headers or {},
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            message_field=message_field,
        )
        self._client = SyncHttpClient(self._config)

    def validate_endpoint(self) -> Tuple[bool, Optional[str]]:
        """Validate that the endpoint is reachable.

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self._client.health_check()

    def _call_model(self, prompt: str, generations: int = 1) -> List[str]:
        """Send prompt to HTTP endpoint and return responses.

        Args:
            prompt: The prompt text to send
            generations: Number of response generations to request

        Returns:
            List of response strings. Errors are returned as empty strings
            to allow detection to still process them.
        """
        results = []

        for _ in range(generations):
            try:
                response = self._client.send(prompt)
                results.append(response.text)
            except ConnectivityError as e:
                logger.error(f"Connectivity error: {e}")
                results.append("")
            except Exception as e:
                logger.error(f"Unexpected error: {type(e).__name__}: {e}")
                results.append("")

        return results

    def get_stats(self) -> dict:
        """Get request statistics.

        Returns:
            Dictionary with total, successful, failed counts and success rate
        """
        return self._client.get_stats()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()

    def __del__(self) -> None:
        """Clean up client on destruction."""
        self.close()
