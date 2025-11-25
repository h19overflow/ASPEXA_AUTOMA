"""
Core GarakScanner class for security scanning.
"""
import asyncio
import importlib
import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

from garak.attempt import Attempt, Message, Turn, Conversation

from services.swarm.core.config import (
    resolve_probe_path,
    get_probe_description,
    get_probe_category,
)
from services.swarm.core.utils import log_performance_metric, get_decision_logger
from .models import ProbeResult
from .detectors import get_detector_triggers, run_detectors_on_attempt
from .http_generator import HttpGenerator
from .websocket_generator import WebSocketGenerator
from .rate_limiter import RateLimiter
from .report_parser import generate_comprehensive_report

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
        """Run a single probe and evaluate results."""
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
            if isinstance(prompt_data, str):
                prompt_text = prompt_data
            elif isinstance(prompt_data, dict):
                prompt_text = prompt_data.get("prompt", str(prompt_data))
            else:
                prompt_text = str(prompt_data)

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
                        result = await self._evaluate_output(
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

    def _build_conversation(self, prompt_text: str, output_text: str) -> Optional[Conversation]:
        """Build garak Conversation object with proper Message format.

        Handles different garak versions with varying Message constructors.
        """
        try:
            # Try garak's Message class - it uses positional args (text) not keyword (role=)
            # Different garak versions may have different signatures
            msg_user = Message(prompt_text)
            msg_user.role = "user"
            msg_assistant = Message(output_text)
            msg_assistant.role = "assistant"
            turn = Turn(messages=[msg_user, msg_assistant])
            return Conversation(turns=[turn])
        except (TypeError, AttributeError) as e:
            logger.debug(f"Could not build Conversation with Message objects: {e}")
            try:
                # Fallback: Try without role attribute
                msg_user = Message(prompt_text)
                msg_assistant = Message(output_text)
                turn = Turn(messages=[msg_user, msg_assistant])
                return Conversation(turns=[turn])
            except Exception as e2:
                logger.warning(f"Failed to build Conversation: {e2}")
                return None

    async def _evaluate_output(
        self,
        probe,
        probe_name: str,
        probe_description: str,
        probe_category: str,
        prompt_text: str,
        output_text: str
    ) -> ProbeResult:
        """Evaluate a single output with detectors."""
        # Build attempt object
        attempt = Attempt()
        attempt.prompt = prompt_text
        attempt.outputs = [output_text]
        attempt.status = 2  # Garak status for "generated"

        # Set detector triggers
        attempt.notes = get_detector_triggers(probe, prompt_text, output_text)

        # Build conversation structure for detectors (optional - some detectors don't need it)
        conversation = self._build_conversation(prompt_text, output_text)
        if conversation:
            attempt.messages = conversation

        # Run detectors
        all_detector_results = run_detectors_on_attempt(attempt, probe)

        # Determine overall result
        status = "pass"
        max_score = 0.0
        failing_detector = "none"
        detection_reason = "All detectors passed"

        for detector_name, scores in all_detector_results.items():
            detector_max = max(scores) if scores else 0.0
            if detector_max > max_score:
                max_score = detector_max
                failing_detector = detector_name

            if detector_max >= 0.5:
                status = "fail"

        if status == "fail":
            detection_reason = f"Detector {failing_detector} triggered (score: {max_score:.2f})"

        return ProbeResult(
            probe_name=probe_name,
            probe_description=probe_description,
            category=probe_category,
            prompt=prompt_text,
            output=output_text,
            status=status,
            detector_name=failing_detector,
            detector_score=max_score,
            detection_reason=detection_reason
        )

    def save_results(
        self,
        results: List[ProbeResult],
        output_path: Path,
        audit_id: str = "audit-default",
        affected_component: str = "unknown"
    ):
        """Save scan results to JSONL format and generate comprehensive JSON report.

        Args:
            results: List of ProbeResult objects from scanning
            output_path: Path to save raw JSONL results
            audit_id: Audit identifier for report metadata
            affected_component: Component being audited for report metadata
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Step 1: Save raw JSONL results
        with open(output_path, "w") as f:
            for result in results:
                record = {
                    "probe_name": result.probe_name,
                    "probe_description": result.probe_description,
                    "category": result.category,
                    "prompt": result.prompt,
                    "output": result.output,
                    "status": result.status,
                    "detector_name": result.detector_name,
                    "detector_score": result.detector_score,
                    "detection_reason": result.detection_reason,
                }
                f.write(json.dumps(record) + "\n")

        logger.info(f"Saved {len(results)} results to {output_path}")

        # Step 2: Generate comprehensive report
        try:
            report_output_path = output_path.parent / f"{output_path.stem}_report.json"
            report = generate_comprehensive_report(
                report_path=output_path,
                audit_id=audit_id,
                affected_component=affected_component,
                output_path=report_output_path
            )
            logger.info(f"Generated comprehensive report: {report_output_path}")
            logger.info(f"Report summary: {report['metadata']['total_vulnerability_clusters']} vulnerability clusters, "
                       f"{report['metadata']['total_vulnerable_probes']} vulnerable probes, "
                       f"{report['metadata']['total_vulnerability_findings']} vulnerability findings")
        except Exception as e:
            logger.error(f"Failed to generate comprehensive report: {e}")


_scanner: Optional[GarakScanner] = None


def get_scanner() -> GarakScanner:
    """Get or create singleton scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = GarakScanner()
    return _scanner
