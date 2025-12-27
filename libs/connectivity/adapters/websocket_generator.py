"""
WebSocket generator for Garak scanner.

Purpose: Send probe prompts to WebSocket endpoints
Dependencies: websockets, garak.generators.base
Used by: execution/scanner.py
"""
import asyncio
import json
import logging
import time
from typing import List, Optional, Tuple

import websockets
import garak.generators.base

from libs.connectivity.response import ResponseExtractor

logger = logging.getLogger(__name__)


class WebSocketGeneratorError(Exception):
    """Raised when WebSocket generator encounters an error."""
    pass


class WebSocketGenerator(garak.generators.base.Generator):
    """Generator that sends prompts to a WebSocket endpoint.

    Supports multiple response formats via centralized ResponseExtractor:
    - {"response": "..."} - Standard format
    - {"text": "..."} - Alternative format
    - {"output": "..."} - Alternative format
    - {"message": "..."} - Chat format
    - {"choices": [{"message": {"content": "..."}}]} - OpenAI format
    """

    def __init__(self, endpoint_url: str, headers: dict = None, timeout: int = 30):
        # Set name BEFORE calling super().__init__() because parent class needs it
        self.name = "WebSocketGenerator"
        self.generations = 1

        super().__init__()

        # Validate and normalize WebSocket URL
        if not endpoint_url.startswith(("ws://", "wss://")):
            raise ValueError(f"WebSocket URL must start with ws:// or wss://, got: {endpoint_url}")

        self.endpoint_url = endpoint_url
        self.headers = headers or {}
        self.timeout = timeout
        self._connection_validated = False
        self._error_count = 0
        self._success_count = 0
        self._extractor = ResponseExtractor()

    def validate_endpoint(self) -> Tuple[bool, Optional[str]]:
        """Validate that the WebSocket endpoint is reachable.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            async def test_connection():
                try:
                    async with websockets.connect(
                        self.endpoint_url,
                        extra_headers=self.headers,
                        timeout=5
                    ) as ws:
                        await ws.ping()
                        return True
                except Exception as e:
                    logger.debug(f"WebSocket validation error: {e}")
                    return False

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return True, None
                else:
                    result = loop.run_until_complete(test_connection())
                    return result, None
            except RuntimeError:
                result = asyncio.run(test_connection())
                return result, None

        except Exception as e:
            return False, str(e)

    def _extract_response(self, data: dict) -> str:
        """Extract response text from various API response formats."""
        return self._extractor.extract(data)

    async def _send_and_receive(self, prompt: str) -> str:
        """Send a prompt via WebSocket and receive response.

        Args:
            prompt: The prompt text to send

        Returns:
            Response text or empty string on error
        """
        try:
            request_start = time.time()

            async with websockets.connect(
                self.endpoint_url,
                extra_headers=self.headers,
                timeout=self.timeout
            ) as ws:
                payload = {"prompt": prompt}
                await ws.send(json.dumps(payload))

                response_text = await asyncio.wait_for(ws.recv(), timeout=self.timeout)

                request_duration = time.time() - request_start
                logger.debug(f"WebSocket request latency: {request_duration:.3f}s")

                try:
                    data = json.loads(response_text)
                    output = self._extract_response(data)
                    self._success_count += 1
                    return output
                except json.JSONDecodeError:
                    logger.warning(f"Non-JSON WebSocket response: {response_text[:100]}")
                    self._success_count += 1
                    return response_text

        except asyncio.TimeoutError:
            self._error_count += 1
            logger.error(f"WebSocket request timeout after {self.timeout}s")
            return ""
        except websockets.exceptions.ConnectionClosed:
            self._error_count += 1
            logger.error("WebSocket connection closed unexpectedly")
            return ""
        except websockets.exceptions.InvalidURI:
            self._error_count += 1
            logger.error(f"Invalid WebSocket URI: {self.endpoint_url}")
            return ""
        except Exception as e:
            self._error_count += 1
            logger.error(f"WebSocket error: {type(e).__name__}: {e}")
            return ""

    def _call_model(self, prompt: str, generations: int = 1) -> List[str]:
        """Send prompt to WebSocket endpoint and return responses.

        Args:
            prompt: The prompt text to send
            generations: Number of response generations to request

        Returns:
            List of response strings. Errors are returned as empty strings.
        """
        results = []

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                tasks = [self._send_and_receive(prompt) for _ in range(generations)]
                results = loop.run_until_complete(asyncio.gather(*tasks))
            else:
                tasks = [self._send_and_receive(prompt) for _ in range(generations)]
                results = asyncio.run(asyncio.gather(*tasks))
        except RuntimeError:
            tasks = [self._send_and_receive(prompt) for _ in range(generations)]
            results = asyncio.run(asyncio.gather(*tasks))

        return results

    def get_stats(self) -> dict:
        """Get request statistics."""
        total = self._success_count + self._error_count
        return {
            "total_requests": total,
            "successful": self._success_count,
            "failed": self._error_count,
            "success_rate": self._success_count / total if total > 0 else 0.0,
        }
