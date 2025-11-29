"""
Chat HTTP Target for PyRIT

HTTP Target with proper conversation support for multi-turn attacks.
"""
import logging
import json
from typing import Optional

import aiohttp
from pyrit.prompt_target import PromptTarget
from pyrit.models import PromptRequestResponse

logger = logging.getLogger(__name__)


class ChatHTTPTarget(PromptTarget):
    """
    HTTP Target with conversation support.

    Compatible with PyRIT orchestrators including RedTeamingOrchestrator.
    """

    def __init__(
        self,
        endpoint_url: str,
        prompt_template: str = '{"message": "{PROMPT}"}',
        response_path: str = "response",
        headers: Optional[dict] = None,
        timeout: int = 30,
    ):
        """
        Initialize HTTP target.

        Args:
            endpoint_url: Target API endpoint
            prompt_template: JSON template with {PROMPT} placeholder
            response_path: JSON path to extract response (e.g., "response" or "data.message")
            headers: Optional HTTP headers
            timeout: Request timeout in seconds
        """
        super().__init__()
        self._endpoint_url = endpoint_url
        self._prompt_template = prompt_template
        self._response_path = response_path
        self._headers = headers or {"Content-Type": "application/json"}
        self._timeout = timeout

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        """Validate the prompt request."""
        if not prompt_request.request_pieces:
            raise ValueError("No request pieces provided")

        request_piece = prompt_request.request_pieces[0]
        if not request_piece.converted_value and not request_piece.original_value:
            raise ValueError("Request piece has no value")

    async def send_prompt_async(
        self, *, prompt_request: PromptRequestResponse
    ) -> PromptRequestResponse:
        """
        Send prompt and return response.

        Args:
            prompt_request: PyRIT prompt request

        Returns:
            Updated prompt request with response
        """
        self._validate_request(prompt_request=prompt_request)

        request_piece = prompt_request.request_pieces[0]
        prompt_text = request_piece.converted_value or request_piece.original_value

        # Build request body
        body = self._prompt_template.replace("{PROMPT}", self._escape_json(prompt_text))

        logger.debug(f"Sending to {self._endpoint_url}: {prompt_text[:100]}...")

        # Send request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._endpoint_url,
                data=body,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as resp:
                response_text = await resp.text()

        # Parse response
        parsed_response = self._extract_response(response_text)
        request_piece.converted_value = parsed_response

        logger.debug(f"Received response: {parsed_response[:100]}...")

        return prompt_request

    def _extract_response(self, response_text: str) -> str:
        """Extract response from JSON using configured path."""
        try:
            data = json.loads(response_text)
            # Navigate path (e.g., "data.message" -> data["data"]["message"])
            parts = self._response_path.split(".")
            result = data
            for part in parts:
                if isinstance(result, dict) and part in result:
                    result = result[part]
                else:
                    return response_text
            return str(result)
        except json.JSONDecodeError:
            return response_text

    @staticmethod
    def _escape_json(text: str) -> str:
        """Escape text for JSON embedding."""
        return (
            text.replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t')
        )
