"""Attack execution orchestrator.

Coordinates converter transformation and target execution.
Dependencies: libs.connectivity, asyncio
System role: Attack execution pipeline
"""
import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, Optional
import logging
import base64

from libs.connectivity import AsyncHttpClient, ConnectionConfig
from ..models.session import AttackAttempt, AttemptStatus
from ..models.target import TargetConfig, Protocol, AuthType
from ..core.converter_chain import ConverterChainExecutor

logger = logging.getLogger(__name__)


class AttackExecutor:
    """Orchestrates attack execution with streaming callbacks.

    Applies converter chain, sends to target, streams response.
    """

    def __init__(self):
        """Initialize executor with converter chain."""
        self._converter_chain = ConverterChainExecutor()

    async def execute(
        self,
        raw_payload: str,
        converter_names: list[str],
        target: TargetConfig,
        on_progress: Optional[Callable[[str, Any], None]] = None,
    ) -> AttackAttempt:
        """Execute an attack with optional progress callbacks.

        Args:
            raw_payload: Original payload text
            converter_names: Converters to apply
            target: Target configuration
            on_progress: Callback for progress updates

        Returns:
            Completed AttackAttempt

        Raises:
            Exception: If attack execution fails
        """
        attempt = AttackAttempt(
            raw_payload=raw_payload,
            converter_chain=converter_names,
            transformed_payload="",
            target_url=target.url,
            protocol=target.protocol.value,
            headers=target.headers.copy(),
        )

        # Step 1: Transform payload
        if on_progress:
            on_progress("transforming", {"converters": converter_names})

        transform_result = await self._converter_chain.transform_with_steps(
            raw_payload, converter_names
        )
        attempt.transformed_payload = transform_result.final_payload
        attempt.transform_errors = transform_result.errors

        if on_progress:
            on_progress(
                "transformed",
                {
                    "final_payload": transform_result.final_payload,
                    "steps": len(transform_result.steps),
                },
            )

        # Step 2: Build connection config
        config = self._build_config(target)

        # Step 3: Execute based on protocol
        attempt.status = AttemptStatus.EXECUTING
        if on_progress:
            on_progress("executing", {"url": target.url})

        try:
            if target.protocol == Protocol.HTTP:
                await self._execute_http(attempt, config, on_progress)
            else:
                await self._execute_websocket(attempt, config, on_progress)

        except Exception as e:
            attempt.status = AttemptStatus.FAILED
            attempt.error_message = str(e)
            logger.error("Attack failed: %s", e)
            if on_progress:
                on_progress("error", {"message": str(e)})

        return attempt

    def _build_config(self, target: TargetConfig) -> ConnectionConfig:
        """Build connection config from target config.

        Args:
            target: Target configuration

        Returns:
            ConnectionConfig for HTTP client
        """
        headers = target.headers.copy()

        # Apply authentication
        if target.auth.auth_type == AuthType.BEARER:
            headers["Authorization"] = f"Bearer {target.auth.token}"
        elif target.auth.auth_type == AuthType.API_KEY:
            headers[target.auth.header_name] = target.auth.token
        elif target.auth.auth_type == AuthType.BASIC:
            creds = f"{target.auth.username}:{target.auth.password}"
            encoded = base64.b64encode(creds.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        return ConnectionConfig(
            endpoint_url=target.url,
            headers=headers,
            timeout=target.timeout_seconds,
            message_field=target.message_field,
        )

    async def _execute_http(
        self,
        attempt: AttackAttempt,
        config: ConnectionConfig,
        on_progress: Optional[Callable],
    ) -> None:
        """Execute HTTP attack.

        Args:
            attempt: Attack attempt to update
            config: Connection configuration
            on_progress: Optional progress callback
        """
        start = datetime.utcnow()

        async with AsyncHttpClient(config) as client:
            response = await client.send(attempt.transformed_payload)

        attempt.latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
        attempt.response_text = response.text
        attempt.response_status_code = response.status_code
        attempt.response_headers = dict(response.raw.get("headers", {}))
        attempt.status = AttemptStatus.SUCCESS

        if on_progress:
            on_progress(
                "response",
                {
                    "text": response.text,
                    "status_code": response.status_code,
                    "latency_ms": attempt.latency_ms,
                },
            )

    async def _execute_websocket(
        self,
        attempt: AttackAttempt,
        config: ConnectionConfig,
        on_progress: Optional[Callable],
    ) -> None:
        """Execute WebSocket attack.

        Args:
            attempt: Attack attempt to update
            config: Connection configuration
            on_progress: Optional progress callback
        """
        import websockets

        start = datetime.utcnow()

        async with websockets.connect(
            config.endpoint_url,
            extra_headers=config.headers,
        ) as ws:
            await ws.send(attempt.transformed_payload)
            response = await asyncio.wait_for(ws.recv(), timeout=config.timeout)

        attempt.latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
        attempt.response_text = response
        attempt.status = AttemptStatus.SUCCESS

        if on_progress:
            on_progress(
                "response",
                {
                    "text": response,
                    "latency_ms": attempt.latency_ms,
                },
            )
