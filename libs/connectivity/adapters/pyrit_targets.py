"""PyRIT Target Adapters.

Purpose: Adapt connectivity clients to work with PyRIT orchestrator
Role: Wrap HTTP/WebSocket infrastructure for PyRIT PromptTarget compatibility
Dependencies: pyrit, libs.connectivity
"""
import logging
from typing import Optional

from pyrit.prompt_target import PromptTarget
from pyrit.models import PromptRequestResponse

from libs.connectivity.adapters import GarakHttpGenerator as HttpGenerator
from services.swarm.garak_scanner.websocket_generator import WebSocketGenerator

logger = logging.getLogger(__name__)


class HttpTargetAdapter(PromptTarget):
    """Adapter for HttpGenerator to work with PyRIT orchestrator.

    Wraps existing HTTP infrastructure for PyRIT compatibility.
    """

    def __init__(
        self,
        endpoint_url: str,
        headers: Optional[dict] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize with existing HttpGenerator.

        Args:
            endpoint_url: HTTP endpoint URL
            headers: Optional HTTP headers
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        super().__init__()
        self._generator = HttpGenerator(
            endpoint_url=endpoint_url,
            headers=headers,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._endpoint_url = endpoint_url
        logger.info(f"Initialized HttpTargetAdapter for {endpoint_url}")

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        """Validate the prompt request before sending.

        Args:
            prompt_request: PyRIT prompt request/response object

        Raises:
            ValueError: If request is invalid
        """
        if not prompt_request.request_pieces:
            raise ValueError("No request pieces provided")

        request_piece = prompt_request.request_pieces[0]
        if not request_piece.converted_value and not request_piece.original_value:
            raise ValueError("Request piece has no value")

    async def send_prompt_async(
        self, *, prompt_request: PromptRequestResponse
    ) -> PromptRequestResponse:
        """Send prompt via HTTP generator (PyRIT async interface).

        Args:
            prompt_request: PyRIT prompt request/response object

        Returns:
            Updated prompt request with response

        Raises:
            ValueError: If no request pieces provided
            RuntimeError: If HTTP request fails
        """
        self._validate_request(prompt_request=prompt_request)

        request_piece = prompt_request.request_pieces[0]
        prompt_text = request_piece.converted_value or request_piece.original_value

        logger.debug(f"Sending HTTP prompt: {prompt_text[:100]}...")

        responses = self._generator._call_model(prompt_text, generations=1)

        if not responses or not responses[0]:
            raise RuntimeError("HTTP request failed - empty response")

        request_piece.converted_value = responses[0]
        logger.debug(f"Received HTTP response: {responses[0][:100]}...")

        return prompt_request


class WebSocketTargetAdapter(PromptTarget):
    """Adapter for WebSocketGenerator to work with PyRIT orchestrator.

    Wraps existing WebSocket infrastructure for PyRIT compatibility.
    """

    def __init__(
        self,
        endpoint_url: str,
        headers: Optional[dict] = None,
        timeout: int = 30,
    ):
        """Initialize with existing WebSocketGenerator.

        Args:
            endpoint_url: WebSocket endpoint URL (ws:// or wss://)
            headers: Optional WebSocket headers
            timeout: Request timeout in seconds
        """
        super().__init__()
        self._generator = WebSocketGenerator(
            endpoint_url=endpoint_url, headers=headers, timeout=timeout
        )
        self._endpoint_url = endpoint_url
        logger.info(f"Initialized WebSocketTargetAdapter for {endpoint_url}")

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        """Validate the prompt request before sending.

        Args:
            prompt_request: PyRIT prompt request/response object

        Raises:
            ValueError: If request is invalid
        """
        if not prompt_request.request_pieces:
            raise ValueError("No request pieces provided")

        request_piece = prompt_request.request_pieces[0]
        if not request_piece.converted_value and not request_piece.original_value:
            raise ValueError("Request piece has no value")

    async def send_prompt_async(
        self, *, prompt_request: PromptRequestResponse
    ) -> PromptRequestResponse:
        """Send prompt via WebSocket generator (PyRIT async interface).

        Args:
            prompt_request: PyRIT prompt request/response object

        Returns:
            Updated prompt request with response

        Raises:
            ValueError: If no request pieces provided
            RuntimeError: If WebSocket request fails
        """
        self._validate_request(prompt_request=prompt_request)

        request_piece = prompt_request.request_pieces[0]
        prompt_text = request_piece.converted_value or request_piece.original_value

        logger.debug(f"Sending WebSocket prompt: {prompt_text[:100]}...")

        responses = self._generator._call_model(prompt_text, generations=1)

        if not responses or not responses[0]:
            raise RuntimeError("WebSocket request failed - empty response")

        request_piece.converted_value = responses[0]
        logger.debug(f"Received WebSocket response: {responses[0][:100]}...")

        return prompt_request
