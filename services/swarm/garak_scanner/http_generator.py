"""
HTTP generator for Garak scanner.

Sends probe prompts to an HTTP endpoint and collects responses.
"""
import logging
import time
from typing import List, Optional, Tuple

import requests
import garak.generators.base

from services.swarm.core.utils import log_performance_metric

logger = logging.getLogger(__name__)


class HttpGeneratorError(Exception):
    """Raised when HTTP generator encounters an error."""
    pass


class HttpGenerator(garak.generators.base.Generator):
    """Generator that sends prompts to an HTTP endpoint.

    Supports multiple response formats:
    - {"response": "..."} - Standard format
    - {"text": "..."} - Alternative format
    - {"output": "..."} - Alternative format
    - {"message": "..."} - Chat format
    - {"choices": [{"message": {"content": "..."}}]} - OpenAI format
    """

    def __init__(self, endpoint_url: str, headers: dict = None):
        # Set name BEFORE calling super().__init__() because parent class needs it
        self.name = "HttpGenerator"
        self.generations = 1

        super().__init__()

        self.endpoint_url = endpoint_url
        self.headers = headers or {}
        self._connection_validated = False
        self._error_count = 0
        self._success_count = 0

    def validate_endpoint(self) -> Tuple[bool, Optional[str]]:
        """Validate that the endpoint is reachable.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            response = requests.head(
                self.endpoint_url.rsplit('/', 1)[0],  # Check base URL
                timeout=5
            )
            return True, None
        except requests.RequestException as e:
            return False, str(e)

    def _extract_response(self, data: dict) -> str:
        """Extract response text from various API response formats."""
        # Standard formats
        if "response" in data:
            return data["response"]
        if "text" in data:
            return data["text"]
        if "output" in data:
            return data["output"]
        if "message" in data:
            return data["message"]

        # OpenAI format
        if "choices" in data and data["choices"]:
            choice = data["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
            if "text" in choice:
                return choice["text"]

        # Fallback: stringify the entire response
        logger.warning(f"Unknown response format, returning raw: {list(data.keys())}")
        return str(data)

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

        for gen_idx in range(generations):
            try:
                payload = {"prompt": prompt}
                request_start = time.time()

                response = requests.post(
                    self.endpoint_url,
                    json=payload,
                    headers=self.headers,
                    timeout=30
                )

                request_duration = time.time() - request_start
                log_performance_metric("http_request_latency", request_duration, "seconds")

                response.raise_for_status()

                try:
                    data = response.json()
                    output = self._extract_response(data)
                    results.append(output)
                    self._success_count += 1
                except ValueError as e:
                    # Response is not JSON - use raw text
                    logger.warning(f"Non-JSON response from endpoint: {response.text[:100]}")
                    results.append(response.text)
                    self._success_count += 1

            except requests.ConnectionError as e:
                self._error_count += 1
                logger.error(f"Connection failed to {self.endpoint_url}: {e}")
                # Return empty string so detector can still evaluate (will likely pass)
                results.append("")

            except requests.Timeout as e:
                self._error_count += 1
                logger.error(f"Request timeout after 30s: {e}")
                results.append("")

            except requests.HTTPError as e:
                self._error_count += 1
                status_code = e.response.status_code if e.response else "unknown"
                logger.error(f"HTTP error {status_code}: {e}")
                # For 4xx/5xx errors, we might still get useful response body
                if e.response is not None:
                    try:
                        error_body = e.response.text[:500]
                        results.append(error_body)
                    except Exception:
                        results.append("")
                else:
                    results.append("")

            except Exception as e:
                self._error_count += 1
                logger.error(f"Unexpected error during HTTP request: {type(e).__name__}: {e}")
                results.append("")

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
