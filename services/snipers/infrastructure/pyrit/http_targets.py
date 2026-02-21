"""
PyRIT HTTP/WebSocket Target Adapters

Adapts connectivity clients to PyRIT PromptTarget interface for use
in PyRIT orchestrators (e.g., RedTeamingOrchestrator).
"""
import logging
import json
from typing import Optional

import aiohttp
from pyrit.prompt_target import PromptTarget
from pyrit.models import PromptRequestResponse

from libs.connectivity.adapters.garak_generator import GarakHttpGenerator as HttpGenerator
from libs.connectivity.adapters.websocket_generator import WebSocketGenerator

logger = logging.getLogger(__name__)


class HttpTargetAdapter(PromptTarget):
    """Wraps HTTP infrastructure for PyRIT orchestrator compatibility."""

    def __init__(
        self,
        endpoint_url: str,
        headers: Optional[dict] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
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
        if not prompt_request.request_pieces:
            raise ValueError("No request pieces provided")
        request_piece = prompt_request.request_pieces[0]
        if not request_piece.converted_value and not request_piece.original_value:
            raise ValueError("Request piece has no value")

    async def send_prompt_async(
        self, *, prompt_request: PromptRequestResponse
    ) -> PromptRequestResponse:
        self._validate_request(prompt_request=prompt_request)
        request_piece = prompt_request.request_pieces[0]
        prompt_text = request_piece.converted_value or request_piece.original_value

        responses = self._generator._call_model(prompt_text, generations=1)
        if not responses or not responses[0]:
            raise RuntimeError("HTTP request failed - empty response")

        request_piece.converted_value = responses[0]
        return prompt_request


class WebSocketTargetAdapter(PromptTarget):
    """Wraps WebSocket infrastructure for PyRIT orchestrator compatibility."""

    def __init__(
        self,
        endpoint_url: str,
        headers: Optional[dict] = None,
        timeout: int = 30,
    ):
        super().__init__()
        self._generator = WebSocketGenerator(
            endpoint_url=endpoint_url, headers=headers, timeout=timeout
        )
        self._endpoint_url = endpoint_url
        logger.info(f"Initialized WebSocketTargetAdapter for {endpoint_url}")

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        if not prompt_request.request_pieces:
            raise ValueError("No request pieces provided")
        request_piece = prompt_request.request_pieces[0]
        if not request_piece.converted_value and not request_piece.original_value:
            raise ValueError("Request piece has no value")

    async def send_prompt_async(
        self, *, prompt_request: PromptRequestResponse
    ) -> PromptRequestResponse:
        self._validate_request(prompt_request=prompt_request)
        request_piece = prompt_request.request_pieces[0]
        prompt_text = request_piece.converted_value or request_piece.original_value

        responses = self._generator._call_model(prompt_text, generations=1)
        if not responses or not responses[0]:
            raise RuntimeError("WebSocket request failed - empty response")

        request_piece.converted_value = responses[0]
        return prompt_request


class ChatHTTPTarget(PromptTarget):
    """HTTP target with conversation support for multi-turn PyRIT attacks."""

    def __init__(
        self,
        endpoint_url: str,
        prompt_template: str = '{"message": "{PROMPT}"}',
        response_path: str = "response",
        headers: Optional[dict] = None,
        timeout: int = 30,
    ):
        super().__init__()
        self._endpoint_url = endpoint_url
        self._prompt_template = prompt_template
        self._response_path = response_path
        self._headers = headers or {"Content-Type": "application/json"}
        self._timeout = timeout

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        if not prompt_request.request_pieces:
            raise ValueError("No request pieces provided")
        request_piece = prompt_request.request_pieces[0]
        if not request_piece.converted_value and not request_piece.original_value:
            raise ValueError("Request piece has no value")

    async def send_prompt_async(
        self, *, prompt_request: PromptRequestResponse
    ) -> PromptRequestResponse:
        self._validate_request(prompt_request=prompt_request)
        request_piece = prompt_request.request_pieces[0]
        prompt_text = request_piece.converted_value or request_piece.original_value

        body = self._prompt_template.replace("{PROMPT}", self._escape_json(prompt_text))

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._endpoint_url,
                data=body,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as resp:
                response_text = await resp.text()

        request_piece.converted_value = self._extract_response(response_text)
        return prompt_request

    def _extract_response(self, response_text: str) -> str:
        try:
            data = json.loads(response_text)
            result = data
            for part in self._response_path.split("."):
                if isinstance(result, dict) and part in result:
                    result = result[part]
                else:
                    return response_text
            return str(result)
        except json.JSONDecodeError:
            return response_text

    @staticmethod
    def _escape_json(text: str) -> str:
        return (
            text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
