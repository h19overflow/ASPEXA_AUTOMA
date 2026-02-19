"""
Core GarakScanner class for streaming security scanning.

Purpose: Main scanning orchestrator for executing Garak probes via streaming events
Dependencies: garak.probes, generators, detection, models, scanner_utils
Used by: graph/nodes/execute_agent.py, entrypoint.py

This module provides the main scanning orchestrator for executing Garak probes
against target LLM endpoints via real-time event streaming. It maintains the
scanner state and delegates execution logic to scanner_utils.
"""
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from services.swarm.core.schema import ScanPlan

from libs.connectivity.adapters import GarakHttpGenerator as HttpGenerator
from libs.monitoring import observe

from ..models import (
    ScannerEvent,
    ScanStartEvent,
    ScanCompleteEvent,
    ScanErrorEvent,
    PromptResultEvent,
    ProbeResult,
)
from ..generators import WebSocketGenerator, RateLimiter
from ..utils import (
    estimate_scan_duration,
)
from .scanner_utils import (
    configure_scanner_from_scan_plan,
    stream_probe_execution,
    stream_prompt_execution,
)

logger = logging.getLogger(__name__)


class GarakScanner:
    """Orchestrator for streaming security scanning using Garak probes.

    Core responsibility: Manage scanner state and coordinate streaming probe execution.
    Logic for probe execution is delegated to scanner_utils module.
    """

    def __init__(self):
        self.generator: Optional[Union[HttpGenerator, WebSocketGenerator]] = None
        self.config: Optional[Dict[str, Any]] = None
        self.rate_limiter: Optional[RateLimiter] = None
        logger.info("GarakScanner initialized")

    def configure_endpoint(
        self,
        endpoint_url: str,
        headers: dict = None,
        connection_type: str = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        config: Optional[Dict[str, Any]] = None
    ):
        """Configure endpoint with factory pattern for HTTP/WebSocket.

        Args:
            endpoint_url: Target endpoint URL
            headers: Optional headers dict
            connection_type: 'http' or 'websocket' (auto-detected from URL if None)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_backoff: Exponential backoff multiplier
            config: Full scan configuration dict (for rate limiting, etc.)
        """
        # Auto-detect connection type from URL if not specified
        if connection_type is None:
            if endpoint_url.startswith(("ws://", "wss://")):
                connection_type = "websocket"
            else:
                connection_type = "http"

        # Store config
        self.config = config or {}

        # Create appropriate generator
        if connection_type == "websocket":
            self.generator = WebSocketGenerator(
                endpoint_url,
                headers or {},
                timeout=timeout
            )
            logger.info(f"Configured WebSocket endpoint: {endpoint_url}")
        else:
            self.generator = HttpGenerator(
                endpoint_url,
                headers or {},
                timeout=timeout,
                max_retries=max_retries,
                retry_backoff=retry_backoff
            )
            logger.info(f"Configured HTTP endpoint: {endpoint_url}")

        # Initialize rate limiter if configured
        requests_per_second = self.config.get("requests_per_second")
        if requests_per_second is not None:
            self.rate_limiter = RateLimiter(requests_per_second)
            logger.info(f"Rate limiter enabled: {requests_per_second} RPS")

    @observe()
    async def scan_with_streaming(
        self,
        plan: "ScanPlan"
    ) -> AsyncGenerator[ScannerEvent, None]:
        """Execute scan with real-time event streaming.

        This method provides granular progress updates as the scan executes,
        yielding events for scan start, probe start/complete, individual results,
        and scan completion. Errors are yielded as events rather than raised.

        Args:
            plan: ScanPlan containing probe selection, configuration, and context

        Yields:
            ScannerEvent objects (ScanStartEvent, ProbeStartEvent, etc.)
        """
        scan_start_time = time.time()

        # Configure scanner from plan
        try:
            self._configure_from_plan(plan)
        except Exception as e:
            yield ScanErrorEvent(
                error_type="configuration_error",
                error_message=f"Failed to configure scanner: {str(e)}",
                recoverable=False,
                context={"plan_audit_id": plan.audit_id}
            )
            return

        # Validate generator is configured
        if not self.generator:
            yield ScanErrorEvent(
                error_type="configuration_error",
                error_message="No generator configured after applying plan",
                recoverable=False,
                context={"target_url": plan.target_url}
            )
            return

        probe_names = plan.selected_probes

        # Emit scan start event
        yield ScanStartEvent(
            audit_id=plan.audit_id,
            agent_type=plan.agent_type,
            total_probes=len(probe_names),
            parallel_enabled=False,
            rate_limit_rps=plan.scan_config.requests_per_second,
            estimated_duration_seconds=estimate_scan_duration(plan)
        )

        # Track aggregated results for final event
        all_results: List[ProbeResult] = []

        # Execute probes and stream events
        try:
            async for event in self._stream_probe_execution(
                probe_names,
                plan
            ):
                yield event

                # Collect results for final summary
                if isinstance(event, PromptResultEvent):
                    all_results.append(ProbeResult(
                        probe_name=event.probe_name,
                        probe_description="",
                        category="",
                        prompt=event.prompt,
                        output=event.output,
                        status=event.status,
                        detector_name=event.detector_name,
                        detector_score=event.detector_score,
                        detection_reason=event.detection_reason
                    ))
        except Exception as e:
            logger.error(f"Unexpected error during scan execution: {e}", exc_info=True)
            yield ScanErrorEvent(
                error_type="execution_error",
                error_message=f"Scan execution failed: {str(e)}",
                recoverable=False,
                context={"audit_id": plan.audit_id}
            )
            return

        # Emit scan complete event
        scan_duration = time.time() - scan_start_time
        total_pass = sum(1 for r in all_results if r.status == "pass")
        total_fail = sum(1 for r in all_results if r.status == "fail")
        total_error = sum(1 for r in all_results if r.status == "error")

        yield ScanCompleteEvent(
            total_probes=len(probe_names),
            total_results=len(all_results),
            total_pass=total_pass,
            total_fail=total_fail,
            total_error=total_error,
            duration_seconds=round(scan_duration, 2),
            vulnerabilities_found=total_fail
        )

    def _configure_from_plan(self, plan: "ScanPlan") -> None:
        """Configure scanner endpoint and settings from ScanPlan."""
        configure_scanner_from_scan_plan(self, plan)

    async def _stream_probe_execution(
        self,
        probe_names: List[str],
        plan: "ScanPlan"
    ) -> AsyncGenerator[ScannerEvent, None]:
        """Execute probes and stream events for each step."""
        async for event in stream_probe_execution(probe_names, plan, self.generator):
            yield event

    async def _stream_prompt_execution(
        self,
        probe: Any,
        probe_name: str,
        probe_description: str,
        probe_category: str,
        prompts: List[Any],
    ) -> AsyncGenerator[Union[PromptResultEvent, ScanErrorEvent], None]:
        """Execute prompts for a single probe and stream result events."""
        async for event in stream_prompt_execution(
            probe, probe_name, probe_description, probe_category,
            prompts, self.generator
        ):
            yield event


_scanner: Optional[GarakScanner] = None


def get_scanner() -> GarakScanner:
    """Get or create singleton scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = GarakScanner()
    return _scanner
