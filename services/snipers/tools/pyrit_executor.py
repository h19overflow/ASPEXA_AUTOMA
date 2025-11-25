"""
PyRIT Executor Module

Coordinates PyRIT converter application and payload sending.
Orchestrates attack execution with fault tolerance and caching.
"""
import logging
from typing import Any, Dict, List

from pyrit.prompt_target import PromptTarget
from pyrit.models import PromptRequestPiece, PromptRequestResponse

from services.snipers.tools.pyrit_bridge import (
    ConverterFactory,
    PayloadTransformer,
)
from services.snipers.tools.pyrit_target_adapters import (
    HttpTargetAdapter,
    WebSocketTargetAdapter,
)

logger = logging.getLogger(__name__)


class PyRITExecutorError(Exception):
    """Raised when PyRIT executor encounters an error."""
    pass


class PyRITExecutor:
    """
    Coordinates PyRIT converter application and payload sending.

    Initialized once per session, reused for multiple payloads.
    """

    def __init__(self):
        """Initialize converter factory and transformer once."""
        # Build expensive components once (CLAUDE.md pattern)
        self._converter_factory = ConverterFactory()
        self._transformer = PayloadTransformer(self._converter_factory)
        self._target_cache: Dict[str, PromptTarget] = {}
        logger.info("Initialized PyRITExecutor")

    def _get_target(self, target_url: str) -> PromptTarget:
        """
        Get or create target adapter for URL (cached).

        Args:
            target_url: Target endpoint URL

        Returns:
            PromptTarget adapter for the URL
        """
        if target_url in self._target_cache:
            logger.debug(f"Using cached target for {target_url}")
            return self._target_cache[target_url]

        # Determine protocol
        if target_url.startswith(("ws://", "wss://")):
            logger.info(f"Creating WebSocket target for {target_url}")
            target = WebSocketTargetAdapter(endpoint_url=target_url)
        else:
            logger.info(f"Creating HTTP target for {target_url}")
            target = HttpTargetAdapter(endpoint_url=target_url)

        self._target_cache[target_url] = target
        return target

    async def execute_attack_async(
        self, payload: str, converter_names: List[str], target_url: str
    ) -> Dict[str, Any]:
        """
        Execute attack: apply converters -> send payload -> return response (async).

        Args:
            payload: Original attack payload
            converter_names: List of converter names to apply sequentially
            target_url: Target endpoint URL

        Returns:
            Dict with:
                - response: str (target's response)
                - transformed_payload: str (payload after converters)
                - errors: List[str] (converter errors, if any)

        Raises:
            ValueError: If payload or target_url empty
            PyRITExecutorError: If execution fails
        """
        # Validate inputs immediately (fail fast)
        if not payload:
            raise ValueError("Payload cannot be empty")
        if not target_url:
            raise ValueError("Target URL cannot be empty")

        logger.info(
            f"Executing attack: payload_len={len(payload)}, "
            f"converters={converter_names}, target={target_url}"
        )

        try:
            # Step 1: Apply converters sequentially (with fault tolerance)
            transformed_payload, converter_errors = await self._transformer.transform_async(
                payload, converter_names
            )

            if converter_errors:
                logger.warning(
                    f"Converter errors occurred: {len(converter_errors)} errors"
                )

            logger.debug(
                f"Payload transformed: original_len={len(payload)}, "
                f"transformed_len={len(transformed_payload)}"
            )

            # Step 2: Get target adapter
            target = self._get_target(target_url)

            # Step 3: Create prompt request
            request_piece = PromptRequestPiece(
                role="user",
                original_value=payload,
                converted_value=transformed_payload,
                original_value_data_type="text",
                converted_value_data_type="text",
            )

            prompt_request = PromptRequestResponse(request_pieces=[request_piece])

            # Step 4: Send via target adapter
            logger.debug("Sending prompt to target...")
            response_request = await target.send_prompt_async(
                prompt_request=prompt_request
            )

            # Extract response from updated request
            response_text = response_request.request_pieces[0].converted_value

            logger.info(
                f"Attack executed successfully: response_len={len(response_text)}"
            )

            return {
                "response": response_text,
                "transformed_payload": transformed_payload,
                "errors": converter_errors,
            }

        except ValueError as e:
            # Re-raise validation errors
            raise
        except Exception as e:
            error_msg = f"Attack execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise PyRITExecutorError(error_msg) from e

    def execute_attack(
        self, payload: str, converter_names: List[str], target_url: str
    ) -> Dict[str, Any]:
        """
        Execute attack: apply converters -> send payload -> return response (sync wrapper).

        Args:
            payload: Original attack payload
            converter_names: List of converter names to apply sequentially
            target_url: Target endpoint URL

        Returns:
            Dict with:
                - response: str (target's response)
                - transformed_payload: str (payload after converters)
                - errors: List[str] (converter errors, if any)

        Raises:
            ValueError: If payload or target_url empty
            PyRITExecutorError: If execution fails
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, need to use nest_asyncio
                import nest_asyncio

                nest_asyncio.apply()
                return loop.run_until_complete(
                    self.execute_attack_async(payload, converter_names, target_url)
                )
            else:
                return loop.run_until_complete(
                    self.execute_attack_async(payload, converter_names, target_url)
                )
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(
                self.execute_attack_async(payload, converter_names, target_url)
            )
