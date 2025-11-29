# Phase 1: Foundation Setup

## Objective
Set up PyRIT initialization and improve HTTP target adapter.

## Files to Create/Modify

### 1.1 Create: `services/snipers/core/pyrit_init.py`

```python
"""
PyRIT Initialization Module

Centralizes PyRIT memory and configuration setup.
Must be called before any PyRIT operations.
"""
import logging
from typing import Optional

from pyrit.common import IN_MEMORY, DUCK_DB, initialize_pyrit
from pyrit.memory import CentralMemory
from pyrit.prompt_target import OpenAIChatTarget

logger = logging.getLogger(__name__)

_initialized = False


def init_pyrit(persistent: bool = False) -> None:
    """
    Initialize PyRIT memory system.

    Args:
        persistent: If True, use DuckDB for persistence. Otherwise in-memory.
    """
    global _initialized
    if _initialized:
        return

    memory_type = DUCK_DB if persistent else IN_MEMORY
    initialize_pyrit(memory_db_type=memory_type)
    _initialized = True
    logger.info(f"PyRIT initialized with {memory_type} memory")


def get_adversarial_chat() -> OpenAIChatTarget:
    """
    Get the adversarial LLM for attack generation.

    Returns:
        OpenAIChatTarget configured for adversarial prompts
    """
    return OpenAIChatTarget()


def get_scoring_target() -> OpenAIChatTarget:
    """
    Get LLM target for scoring responses.

    Returns:
        OpenAIChatTarget configured for scoring
    """
    return OpenAIChatTarget()


def get_memory() -> CentralMemory:
    """
    Get PyRIT central memory instance.

    Returns:
        CentralMemory instance

    Raises:
        ValueError: If PyRIT not initialized
    """
    if not _initialized:
        raise ValueError("PyRIT not initialized. Call init_pyrit() first.")
    return CentralMemory.get_memory_instance()


def cleanup_pyrit() -> None:
    """Dispose of PyRIT memory engine."""
    global _initialized
    try:
        memory = CentralMemory.get_memory_instance()
        memory.dispose_engine()
        _initialized = False
        logger.info("PyRIT memory disposed")
    except Exception as e:
        logger.warning(f"PyRIT cleanup warning: {e}")
```

### 1.2 Update: `services/snipers/core/__init__.py`

```python
"""Snipers core module."""
from .pyrit_init import (
    init_pyrit,
    get_adversarial_chat,
    get_scoring_target,
    get_memory,
    cleanup_pyrit,
)

__all__ = [
    "init_pyrit",
    "get_adversarial_chat",
    "get_scoring_target",
    "get_memory",
    "cleanup_pyrit",
]
```

### 1.3 Create: `libs/connectivity/adapters/chat_http_target.py`

```python
"""
Chat HTTP Target for PyRIT

HTTP Target with proper conversation support for multi-turn attacks.
"""
import logging
import json
from typing import Optional, Callable

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
```

### 1.4 Update: `libs/connectivity/adapters/__init__.py`

```python
"""Connectivity adapters module."""
from .pyrit_targets import HttpTargetAdapter, WebSocketTargetAdapter
from .chat_http_target import ChatHTTPTarget

__all__ = [
    "HttpTargetAdapter",
    "WebSocketTargetAdapter",
    "ChatHTTPTarget",
]
```

## Validation Steps

### Test 1: PyRIT Initialization

```python
# Run in Python REPL or test file
from services.snipers.core import init_pyrit, get_memory, cleanup_pyrit

# Initialize
init_pyrit()
print("PyRIT initialized successfully")

# Get memory
memory = get_memory()
print(f"Memory instance: {memory}")

# Cleanup
cleanup_pyrit()
print("Cleanup complete")
```

### Test 2: ChatHTTPTarget

```python
import asyncio
from libs.connectivity.adapters import ChatHTTPTarget
from pyrit.models import PromptRequestPiece, PromptRequestResponse

async def test_target():
    target = ChatHTTPTarget(
        endpoint_url="http://localhost:8082/chat",
        prompt_template='{"message": "{PROMPT}"}',
        response_path="response",
    )

    piece = PromptRequestPiece(
        role="user",
        original_value="Hello, how are you?",
    )
    request = PromptRequestResponse(request_pieces=[piece])

    result = await target.send_prompt_async(prompt_request=request)
    print(f"Response: {result.request_pieces[0].converted_value}")

asyncio.run(test_target())
```

## Checklist

- [ ] Create `services/snipers/core/pyrit_init.py`
- [ ] Update `services/snipers/core/__init__.py`
- [ ] Create `libs/connectivity/adapters/chat_http_target.py`
- [ ] Update `libs/connectivity/adapters/__init__.py`
- [ ] Run validation test 1 (PyRIT init)
- [ ] Run validation test 2 (ChatHTTPTarget)
- [ ] All tests pass

## Next Phase
Once Phase 1 is complete, proceed to [Phase 2: Scorers](./02_SCORERS.md).
