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
)
from ..generators import WebSocketGenerator, RateLimiter
from ..utils import (
    estimate_scan_duration,
)
from .scanner_utils import (
    configure_scanner_from_scan_plan,
    stream_probe_execution,
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
        logger.info('GarakScanner initialized')

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
        """Configure HTTP or WebSocket generator from endpoint settings."""
        if connection_type is None:
            if endpoint_url.startswith(('ws://', 'wss://')):
                connection_type = 'websocket'
            else:
                connection_type = 'http'

        self.config = config or {}

        if connection_type == 'websocket':
            self.generator = WebSocketGenerator(
                endpoint_url,
                headers or {},
                timeout=timeout
            )
            logger.info(f'Configured WebSocket endpoint: {endpoint_url}')
        else:
            self.generator = HttpGenerator(
                endpoint_url,
                headers or {},
                timeout=timeout,
                max_retries=max_retries,
                retry_backoff=retry_backoff
            )
            logger.info(f'Configured HTTP endpoint: {endpoint_url}')

        requests_per_second = self.config.get('requests_per_second')
        if requests_per_second is not None:
            self.rate_limiter = RateLimiter(requests_per_second)
            logger.info(f'Rate limiter enabled: {requests_per_second} RPS')

    @observe()
    async def scan_with_streaming(
        self,
        plan: 'ScanPlan'
    ) -> AsyncGenerator[ScannerEvent, None]:
        """Execute scan plan, streaming events per probe and prompt."""
        scan_start_time = time.time()

        try:
            configure_scanner_from_scan_plan(self, plan)
        except Exception as e:
            yield ScanErrorEvent(
                error_type='configuration_error',
                error_message=f'Failed to configure scanner: {str(e)}',
                recoverable=False,
                context={'plan_audit_id': plan.audit_id}
            )
            return

        if not self.generator:
            yield ScanErrorEvent(
                error_type='configuration_error',
                error_message='No generator configured after applying plan',
                recoverable=False,
                context={'target_url': plan.target_url}
            )
            return

        probe_names = plan.selected_probes

        yield ScanStartEvent(
            audit_id=plan.audit_id,
            agent_type=plan.agent_type,
            total_probes=len(probe_names),
            parallel_enabled=False,
            rate_limit_rps=plan.scan_config.requests_per_second,
            estimated_duration_seconds=estimate_scan_duration(plan)
        )

        try:
            async for event in stream_probe_execution(probe_names, plan, self.generator):
                yield event
        except Exception as e:
            logger.error(f'Unexpected error during scan execution: {e}', exc_info=True)
            yield ScanErrorEvent(
                error_type='execution_error',
                error_message=f'Scan execution failed: {str(e)}',
                recoverable=False,
                context={'audit_id': plan.audit_id}
            )
            return

        scan_duration = time.time() - scan_start_time

        yield ScanCompleteEvent(
            total_probes=len(probe_names),
            total_results=0,
            total_pass=0,
            total_fail=0,
            total_error=0,
            duration_seconds=round(scan_duration, 2),
            vulnerabilities_found=0
        )


_scanner: Optional[GarakScanner] = None


def get_scanner() -> GarakScanner:
    """Get or create singleton scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = GarakScanner()
    return _scanner