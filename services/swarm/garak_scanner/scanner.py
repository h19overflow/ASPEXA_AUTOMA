"""
Core GarakScanner class for security scanning.

This module provides the main scanning interface for executing Garak probes
against target endpoints. It supports both blocking and streaming scan modes,
parallel execution, and rate limiting.
"""
import asyncio
import importlib
import logging
import time
from typing import List, Optional, Dict, Any, Union, AsyncGenerator, TYPE_CHECKING

if TYPE_CHECKING:
    from services.swarm.core.schema import ScanPlan

from services.swarm.core.config import (
    resolve_probe_path,
    get_probe_description,
    get_probe_category,
)
from services.swarm.core.utils import log_performance_metric, get_decision_logger
from .models import (
    ProbeResult,
    ScannerEvent,
    ScanStartEvent,
    ProbeStartEvent,
    PromptResultEvent,
    ProbeCompleteEvent,
    ScanCompleteEvent,
    ScanErrorEvent,
)
from libs.connectivity.adapters import GarakHttpGenerator as HttpGenerator
from libs.monitoring import observe
from .websocket_generator import WebSocketGenerator
from .rate_limiter import RateLimiter
from .utils import (
    configure_scanner_from_plan,
    estimate_scan_duration,
    extract_prompt_text,
    evaluate_output,
    results_to_dicts,
)

logger = logging.getLogger(__name__)


class GarakScanner:
    """
    Security scanner using Garak probes and detectors.

    Core responsibilities:
    1. Load and execute Garak probes against target endpoints
    2. Evaluate outputs with Garak detectors
    3. Parse and structure results
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
        """
        Configure endpoint with factory pattern for HTTP/WebSocket.

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

        # Store config for parallel execution
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

    def configure_http_endpoint(self, endpoint_url: str, headers: dict = None):
        """Configure an HTTP endpoint as the target generator (backward compatibility)."""
        self.configure_endpoint(endpoint_url, headers, connection_type="http")

    async def scan_with_probe(
        self,
        probe_names: Union[str, List[str]],
        generations: int = 1
    ) -> List[ProbeResult]:
        """
        Run specified probes and evaluate with detectors.

        Args:
            probe_names: Single probe name or list of probe names
            generations: Number of outputs to generate per prompt

        Returns:
            List of ProbeResult objects with detector-based pass/fail
        """
        if not self.generator:
            raise RuntimeError("No generator configured. Call configure_endpoint first.")

        if isinstance(probe_names, str):
            probe_names = [probe_names]

        # Get decision logger if audit_id is available
        audit_id = self.config.get("audit_id")
        decision_logger = None
        if audit_id:
            try:
                decision_logger = get_decision_logger(audit_id)
            except Exception as e:
                logger.warning(f"Failed to get decision logger: {e}")

        # Check if parallel execution is enabled
        enable_parallel = self.config.get("enable_parallel_execution", False)

        # Log scan start
        if decision_logger:
            decision_logger.log_scan_progress(
                progress_type="scanner_start",
                progress_data={
                    "probe_count": len(probe_names),
                    "generations": generations,
                    "parallel_enabled": enable_parallel,
                },
                agent_type=self.config.get("agent_type")
            )

        if enable_parallel:
            return await self._run_probes_parallel(probe_names, generations, decision_logger)
        else:
            # Sequential execution (original behavior)
            all_results = []
            for idx, probe_name in enumerate(probe_names):
                logger.info(f"Running probe: {probe_name} ({idx+1}/{len(probe_names)})")

                # Log probe start
                if decision_logger:
                    decision_logger.log_scan_progress(
                        progress_type="probe_start",
                        progress_data={
                            "probe_name": probe_name,
                            "probe_index": idx + 1,
                            "total_probes": len(probe_names),
                            "generations": generations,
                        },
                        agent_type=self.config.get("agent_type")
                    )

                results = await self._run_single_probe(probe_name, generations, decision_logger)
                all_results.extend(results)

                # Log probe complete
                if decision_logger:
                    decision_logger.log_scan_progress(
                        progress_type="probe_complete",
                        progress_data={
                            "probe_name": probe_name,
                            "probe_index": idx + 1,
                            "total_probes": len(probe_names),
                            "results_count": len(results),
                            "fail_count": sum(1 for r in results if r.status == "fail"),
                        },
                        agent_type=self.config.get("agent_type")
                    )

            # Log scan complete
            if decision_logger:
                decision_logger.log_scan_progress(
                    progress_type="scanner_complete",
                    progress_data={
                        "total_results": len(all_results),
                        "total_probes": len(probe_names),
                    },
                    agent_type=self.config.get("agent_type")
                )

            return all_results

    @observe()
    async def scan_with_streaming(
        self,
        plan: "ScanPlan"  # Import from services.swarm.core.schema
    ) -> AsyncGenerator[ScannerEvent, None]:
        """
        Execute scan with real-time event streaming.

        This method provides granular progress updates as the scan executes,
        yielding events for scan start, probe start/complete, individual results,
        and scan completion. Errors are yielded as events rather than raised.

        Args:
            plan: ScanPlan containing probe selection, configuration, and context

        Yields:
            ScannerEvent objects (ScanStartEvent, ProbeStartEvent, etc.)

        Example:
            async for event in scanner.scan_with_streaming(plan):
                if event.event_type == "prompt_result":
                    print(f"Result: {event.status}")
                elif event.event_type == "scan_complete":
                    print(f"Scan done: {event.total_results} results")
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
        generations = plan.generations

        # Emit scan start event
        yield ScanStartEvent(
            audit_id=plan.audit_id,
            agent_type=plan.agent_type,
            total_probes=len(probe_names),
            generations_per_probe=generations,
            parallel_enabled=plan.scan_config.enable_parallel_execution,
            rate_limit_rps=plan.scan_config.requests_per_second,
            estimated_duration_seconds=estimate_scan_duration(plan)
        )

        # Track aggregated results for final event
        all_results: List[ProbeResult] = []

        # Execute probes and stream events
        try:
            async for event in self._stream_probe_execution(
                probe_names,
                generations,
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
        """
        Configure scanner endpoint and settings from ScanPlan.

        Args:
            plan: ScanPlan with target URL, headers, and configuration

        Raises:
            RuntimeError: If configuration fails
        """
        # Extract config using utility function
        self.config = configure_scanner_from_plan(plan)

        # Configure endpoint with plan settings
        self.configure_endpoint(
            endpoint_url=plan.target_url,
            headers={},  # TODO: Extract from plan if needed
            connection_type=plan.scan_config.connection_type,
            timeout=plan.scan_config.request_timeout,
            max_retries=plan.scan_config.max_retries,
            retry_backoff=plan.scan_config.retry_backoff,
            config=self.config
        )

    async def _stream_probe_execution(
        self,
        probe_names: List[str],
        generations: int,
        plan: "ScanPlan"
    ) -> AsyncGenerator[ScannerEvent, None]:
        """
        Execute probes and stream events for each step.

        Args:
            probe_names: List of probe names to execute
            generations: Number of generations per prompt
            plan: ScanPlan for context

        Yields:
            ScannerEvent objects for probe start/complete and prompt results
        """
        for probe_idx, probe_name in enumerate(probe_names):
            probe_start_time = time.time()

            try:
                # Load probe metadata
                probe_description = get_probe_description(probe_name)
                probe_category = get_probe_category(probe_name)
                probe_path = resolve_probe_path(probe_name)

                # Load probe class
                module_name, class_name = probe_path.rsplit(".", 1)
                module = importlib.import_module(module_name)
                probe_class = getattr(module, class_name)
                probe = probe_class(self.generator)
                prompts = probe.prompts

                # Emit probe start event
                yield ProbeStartEvent(
                    probe_name=probe_name,
                    probe_description=probe_description,
                    probe_category=probe_category,
                    probe_index=probe_idx + 1,
                    total_probes=len(probe_names),
                    total_prompts=len(prompts),
                    generations=generations
                )

                # Track probe-level statistics
                probe_results: List[ProbeResult] = []

                # Execute each prompt
                async for result_event in self._stream_prompt_execution(
                    probe=probe,
                    probe_name=probe_name,
                    probe_description=probe_description,
                    probe_category=probe_category,
                    prompts=prompts,
                    generations=generations
                ):
                    yield result_event

                    # Track for probe summary
                    if isinstance(result_event, PromptResultEvent):
                        probe_results.append(ProbeResult(
                            probe_name=result_event.probe_name,
                            probe_description=probe_description,
                            category=probe_category,
                            prompt=result_event.prompt,
                            output=result_event.output,
                            status=result_event.status,
                            detector_name=result_event.detector_name,
                            detector_score=result_event.detector_score,
                            detection_reason=result_event.detection_reason
                        ))

                # Emit probe complete event
                probe_duration = time.time() - probe_start_time
                pass_count = sum(1 for r in probe_results if r.status == "pass")
                fail_count = sum(1 for r in probe_results if r.status == "fail")
                error_count = sum(1 for r in probe_results if r.status == "error")

                yield ProbeCompleteEvent(
                    probe_name=probe_name,
                    probe_index=probe_idx + 1,
                    total_probes=len(probe_names),
                    results_count=len(probe_results),
                    pass_count=pass_count,
                    fail_count=fail_count,
                    error_count=error_count,
                    duration_seconds=round(probe_duration, 2)
                )

            except Exception as e:
                logger.error(f"Error executing probe {probe_name}: {e}", exc_info=True)
                yield ScanErrorEvent(
                    error_type="probe_execution_error",
                    error_message=f"Probe {probe_name} failed: {str(e)}",
                    probe_name=probe_name,
                    recoverable=True,
                    context={
                        "probe_index": probe_idx + 1,
                        "total_probes": len(probe_names)
                    }
                )

    async def _stream_prompt_execution(
        self,
        probe: Any,
        probe_name: str,
        probe_description: str,
        probe_category: str,
        prompts: List[Any],
        generations: int
    ) -> AsyncGenerator[Union[PromptResultEvent, ScanErrorEvent], None]:
        """
        Execute prompts for a single probe and stream result events.

        Args:
            probe: Loaded probe instance
            probe_name: Probe identifier
            probe_description: Human-readable probe description
            probe_category: Probe category
            prompts: List of prompts to execute
            generations: Number of generations per prompt

        Yields:
            PromptResultEvent for each successful evaluation
            ScanErrorEvent for failures
        """
        for prompt_idx, prompt_data in enumerate(prompts):
            # Extract prompt text using utility function
            prompt_text = extract_prompt_text(prompt_data)

            try:
                # Generate outputs
                gen_start = time.time()
                parallel_gens = self.config.get("enable_parallel_execution", False)

                if parallel_gens:
                    outputs = await self._run_generations_parallel(
                        prompt_text,
                        generations,
                        decision_logger=None
                    )
                else:
                    outputs = self.generator._call_model(prompt_text, generations=generations)

                gen_duration_ms = int((time.time() - gen_start) * 1000)

                # Evaluate each output
                for output_text in outputs:
                    eval_start = time.time()

                    try:
                        result = await evaluate_output(
                            probe, probe_name, probe_description, probe_category,
                            prompt_text, output_text
                        )

                        eval_duration_ms = int((time.time() - eval_start) * 1000)

                        # Emit prompt result event
                        yield PromptResultEvent(
                            probe_name=probe_name,
                            prompt_index=prompt_idx + 1,
                            total_prompts=len(prompts),
                            prompt=prompt_text,
                            output=output_text,
                            status=result.status,
                            detector_name=result.detector_name,
                            detector_score=result.detector_score,
                            detection_reason=result.detection_reason,
                            generation_duration_ms=gen_duration_ms,
                            evaluation_duration_ms=eval_duration_ms
                        )

                    except Exception as eval_err:
                        logger.warning(f"Detector evaluation error: {eval_err}")
                        yield ScanErrorEvent(
                            error_type="evaluation_error",
                            error_message=f"Detector evaluation failed: {str(eval_err)}",
                            probe_name=probe_name,
                            prompt_index=prompt_idx + 1,
                            recoverable=True,
                            context={"output_length": len(output_text)}
                        )

            except Exception as e:
                logger.error(f"Error generating outputs for prompt {prompt_idx + 1}: {e}")
                yield ScanErrorEvent(
                    error_type="generation_error",
                    error_message=f"Generation failed: {str(e)}",
                    probe_name=probe_name,
                    prompt_index=prompt_idx + 1,
                    recoverable=True,
                    context={"prompt_length": len(prompt_text)}
                )

    async def _run_probes_parallel(
        self,
        probe_names: List[str],
        generations: int,
        decision_logger = None
    ) -> List[ProbeResult]:
        """
        Run probes in parallel with semaphore controls.

        Args:
            probe_names: List of probe names to run
            generations: Number of outputs to generate per prompt
            decision_logger: Optional decision logger for progress tracking

        Returns:
            List of ProbeResult objects (maintains probe order)
        """
        max_concurrent_probes = self.config.get("max_concurrent_probes", 1)
        probe_semaphore = asyncio.Semaphore(max_concurrent_probes)

        logger.info(
            f"Running {len(probe_names)} probes in parallel "
            f"(max concurrent: {max_concurrent_probes})"
        )

        # Log parallel execution start
        if decision_logger:
            decision_logger.log_parallel_execution(
                event="parallel_probes_start",
                details={
                    "total_probes": len(probe_names),
                    "max_concurrent": max_concurrent_probes,
                    "generations": generations,
                },
                agent_type=self.config.get("agent_type")
            )

        async def run_probe_with_semaphore(probe_name: str, probe_idx: int) -> List[ProbeResult]:
            """Run a single probe with semaphore control."""
            async with probe_semaphore:
                # Log probe start
                if decision_logger:
                    decision_logger.log_scan_progress(
                        progress_type="probe_start",
                        progress_data={
                            "probe_name": probe_name,
                            "probe_index": probe_idx + 1,
                            "total_probes": len(probe_names),
                            "generations": generations,
                            "parallel": True,
                        },
                        agent_type=self.config.get("agent_type")
                    )

                results = await self._run_single_probe(probe_name, generations, decision_logger)

                # Log probe complete
                if decision_logger:
                    decision_logger.log_scan_progress(
                        progress_type="probe_complete",
                        progress_data={
                            "probe_name": probe_name,
                            "probe_index": probe_idx + 1,
                            "total_probes": len(probe_names),
                            "results_count": len(results),
                            "fail_count": sum(1 for r in results if r.status == "fail"),
                            "parallel": True,
                        },
                        agent_type=self.config.get("agent_type")
                    )

                return results

        # Run all probes in parallel (order maintained by asyncio.gather)
        results_list = await asyncio.gather(
            *[run_probe_with_semaphore(name, idx) for idx, name in enumerate(probe_names)]
        )

        # Flatten results while maintaining probe order
        all_results = []
        for results in results_list:
            all_results.extend(results)

        # Log parallel execution complete
        if decision_logger:
            decision_logger.log_parallel_execution(
                event="parallel_probes_complete",
                details={
                    "total_probes": len(probe_names),
                    "total_results": len(all_results),
                },
                agent_type=self.config.get("agent_type")
            )

            decision_logger.log_scan_progress(
                progress_type="scanner_complete",
                progress_data={
                    "total_results": len(all_results),
                    "total_probes": len(probe_names),
                },
                agent_type=self.config.get("agent_type")
            )

        return all_results

    async def _run_single_probe(
        self,
        probe_name: str,
        generations: int,
        decision_logger = None
    ) -> List[ProbeResult]:
        """
        Run a single probe and evaluate results.

        Args:
            probe_name: Probe identifier to load and execute
            generations: Number of outputs per prompt
            decision_logger: Optional decision logger for progress tracking

        Returns:
            List of ProbeResult objects for all prompts in the probe
        """
        probe_start = time.time()
        probe_path = resolve_probe_path(probe_name)
        probe_description = get_probe_description(probe_name)
        probe_category = get_probe_category(probe_name)

        module_name, class_name = probe_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        probe_class = getattr(module, class_name)
        probe = probe_class(self.generator)

        # Garak probes use 'prompts' attribute, not 'probe_prompts'
        prompts = probe.prompts
        logger.info(f"Probe {probe_name} has {len(prompts)} prompts")

        results = []

        for idx, prompt_data in enumerate(prompts):
            prompt_text = extract_prompt_text(prompt_data)
            logger.debug(f"Testing prompt {idx+1}/{len(prompts)}: {prompt_text[:80]}")

            outputs = []
            try:
                # Generate outputs (with parallel support if enabled)
                gen_start = time.time()
                parallel_gens = self.config.get("enable_parallel_execution", False)

                # Log generation start
                if decision_logger:
                    decision_logger.log_scan_progress(
                        progress_type="generation_start",
                        progress_data={
                            "probe_name": probe_name,
                            "prompt_index": idx + 1,
                            "total_prompts": len(prompts),
                            "generations": generations,
                            "parallel": parallel_gens,
                        },
                        agent_type=self.config.get("agent_type")
                    )

                if parallel_gens:
                    outputs = await self._run_generations_parallel(prompt_text, generations, decision_logger)
                else:
                    outputs = self.generator._call_model(prompt_text, generations=generations)
                gen_duration = time.time() - gen_start
                log_performance_metric("probe_generation_time", gen_duration, "seconds")

                # Log generation complete
                if decision_logger:
                    decision_logger.log_scan_progress(
                        progress_type="generation_complete",
                        progress_data={
                            "probe_name": probe_name,
                            "prompt_index": idx + 1,
                            "total_prompts": len(prompts),
                            "outputs_count": len(outputs),
                            "duration_seconds": round(gen_duration, 2),
                        },
                        agent_type=self.config.get("agent_type")
                    )

                # Evaluate each output with detectors
                eval_start = time.time()
                for output_text in outputs:
                    try:
                        result = await evaluate_output(
                            probe, probe_name, probe_description, probe_category,
                            prompt_text, output_text
                        )
                        results.append(result)
                    except Exception as eval_err:
                        # Detector evaluation failed but preserve the output
                        logger.warning(f"Detector evaluation error (output preserved): {eval_err}")
                        results.append(ProbeResult(
                            probe_name=probe_name,
                            probe_description=probe_description,
                            category=probe_category,
                            prompt=prompt_text,
                            output=output_text,  # Preserve actual output
                            status="error",
                            detector_name="none",
                            detector_score=0.0,
                            detection_reason=f"Detector error: {str(eval_err)}"
                        ))
                eval_duration = time.time() - eval_start
                log_performance_metric("detector_evaluation_time", eval_duration, "seconds")

            except Exception as e:
                logger.error(f"Error generating outputs: {e}")
                # Use first output if available, otherwise empty
                output_for_error = outputs[0] if outputs else ""
                results.append(ProbeResult(
                    probe_name=probe_name,
                    probe_description=probe_description,
                    category=probe_category,
                    prompt=prompt_text,
                    output=output_for_error,
                    status="error",
                    detector_name="none",
                    detector_score=0.0,
                    detection_reason=f"Generation error: {str(e)}"
                ))

        probe_duration = time.time() - probe_start
        log_performance_metric("probe_execution_time", probe_duration, "seconds")
        logger.info(f"Probe {probe_name} completed in {probe_duration:.2f}s with {len(results)} results")

        return results

    async def _run_generations_parallel(
        self,
        prompt_text: str,
        generations: int,
        decision_logger = None
    ) -> List[str]:
        """
        Run multiple generation attempts in parallel with semaphore and rate limiting.

        Args:
            prompt_text: The prompt to send
            generations: Number of generation attempts
            decision_logger: Optional decision logger for progress tracking

        Returns:
            List of response strings
        """
        max_concurrent_generations = self.config.get("max_concurrent_generations", 1)
        generation_semaphore = asyncio.Semaphore(max_concurrent_generations)

        # Log parallel generations start
        if decision_logger:
            decision_logger.log_parallel_execution(
                event="parallel_generations_start",
                details={
                    "generations": generations,
                    "max_concurrent": max_concurrent_generations,
                    "rate_limiter_enabled": self.rate_limiter is not None,
                },
                agent_type=self.config.get("agent_type")
            )

        async def run_generation_with_limits(gen_idx: int) -> str:
            """Run a single generation with semaphore and rate limiting."""
            async with generation_semaphore:
                # Apply rate limiting if configured
                if self.rate_limiter:
                    # Log rate limiting
                    if decision_logger:
                        decision_logger.log_rate_limiting(
                            event="rate_limit_acquire",
                            details={
                                "generation_index": gen_idx + 1,
                                "total_generations": generations,
                            },
                            agent_type=self.config.get("agent_type")
                        )
                    await self.rate_limiter.acquire()

                # Call generator (may be sync or async)
                if hasattr(self.generator, '_call_model'):
                    result = self.generator._call_model(prompt_text, generations=1)
                    # _call_model returns a list, get first element
                    return result[0] if result else ""
                else:
                    return ""

        # Run all generations in parallel
        outputs = await asyncio.gather(
            *[run_generation_with_limits(gen_idx) for gen_idx in range(generations)]
        )

        # Log parallel generations complete
        if decision_logger:
            decision_logger.log_parallel_execution(
                event="parallel_generations_complete",
                details={
                    "generations": generations,
                    "outputs_count": len(outputs),
                },
                agent_type=self.config.get("agent_type")
            )

        return outputs

    def results_to_dicts(self, results: List[ProbeResult]) -> List[dict]:
        """
        Convert ProbeResult objects to dicts for in-memory processing.

        Args:
            results: List of ProbeResult objects from scanning

        Returns:
            List of result dicts ready for report parsing
        """
        return results_to_dicts(results)


_scanner: Optional[GarakScanner] = None


def get_scanner() -> GarakScanner:
    """Get or create singleton scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = GarakScanner()
    return _scanner
