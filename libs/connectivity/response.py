"""
Response extraction and normalization.

This module provides utilities to extract text responses from various
API response formats, ensuring consistent handling across different
target endpoint implementations.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResponseExtractor:
    """Extracts response text from various API response formats.

    Supported formats:
    1. {"response": "..."} - Standard format
    2. {"text": "..."} - Alternative format
    3. {"output": "..."} - Alternative format
    4. {"message": "..."} - Chat format
    5. {"choices": [{"message": {"content": "..."}}]} - OpenAI format
    6. {"choices": [{"text": "..."}]} - OpenAI completion format
    7. Fallback: Stringified JSON if no known field matches
    """

    def __init__(self, response_fields: Optional[List[str]] = None):
        """Initialize extractor with priority-ordered response fields.

        Args:
            response_fields: List of field names to check, in priority order.
                           Defaults to ["response", "text", "output", "message"]
        """
        self.response_fields = response_fields or [
            "response",
            "text",
            "output",
            "message",
        ]

    def extract(self, data: Dict[str, Any]) -> str:
        """Extract response text from API response data.

        Args:
            data: JSON response as dictionary

        Returns:
            Extracted text response, or stringified data if no match
        """
        if not isinstance(data, dict):
            logger.warning(f"Expected dict, got {type(data).__name__}")
            return str(data)

        # Check standard fields in priority order
        for field in self.response_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    return value
                # Handle nested content (e.g., {"message": {"content": "..."}})
                if isinstance(value, dict) and "content" in value:
                    return str(value["content"])
                return str(value)

        # OpenAI format: {"choices": [{"message": {"content": "..."}}]}
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            choice = data["choices"][0]

            # Chat completion format
            if isinstance(choice, dict):
                if "message" in choice and isinstance(choice["message"], dict):
                    content = choice["message"].get("content")
                    if content is not None:
                        return str(content)

                # Text completion format
                if "text" in choice:
                    return str(choice["text"])

                # Delta streaming format
                if "delta" in choice and isinstance(choice["delta"], dict):
                    content = choice["delta"].get("content")
                    if content is not None:
                        return str(content)

        # Anthropic format: {"content": [{"text": "..."}]}
        if "content" in data and isinstance(data["content"], list) and data["content"]:
            first_content = data["content"][0]
            if isinstance(first_content, dict) and "text" in first_content:
                return str(first_content["text"])

        # Fallback: stringify the entire response
        logger.warning(f"Unknown response format, keys: {list(data.keys())}")
        return str(data)

    def extract_safe(self, data: Any) -> str:
        """Extract response with error handling.

        Args:
            data: Response data (any type)

        Returns:
            Extracted text, or empty string on error
        """
        try:
            if data is None:
                return ""
            if isinstance(data, str):
                return data
            if isinstance(data, dict):
                return self.extract(data)
            return str(data)
        except Exception as e:
            logger.error(f"Failed to extract response: {e}")
            return ""
