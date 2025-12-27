"""
Utility functions for GarakScanner probe execution.

Purpose: Encapsulate probe execution logic for better testability and maintainability
Dependencies: garak.probes, generators, detection, models, core.config, utils
Used by: scanner.py

This module contains the core logic for configuring the scanner and executing
probes with streaming event support. These functions are separated from the
GarakScanner class to enable:

1. Unit testing without full scanner instantiation
2. Reusable execution logic across different contexts
3. Clear separation between orchestration and execution
"""
import importlib
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from services.swarm.core.schema import ScanPlan
    from libs.connectivity.adapters import GarakHttpGenerator as HttpGenerator
    from ..generators import WebSocketGenerator

from services.swarm.core.config import (
    resolve_probe_path,
    get_probe_description,
    get_probe_category,
)

from ..models import (
    ProbeResult,
    ScannerEvent,
    ProbeStartEvent,
    PromptResultEvent,
    ProbeCompleteEvent,
    ScanErrorEvent,
)
from ..utils import (
    configure_scanner_from_plan,
    extract_prompt_text,
    evaluate_output,
)

logger = logging.getLogger(__name__)


def configure_scanner_from_scan_plan(
    scanner_instance: Any,
    plan: "ScanPlan"
) -> None:
    """
    Configure scanner endpoint, generator, and rate limiter from ScanPlan.

    This function extracts configuration from a ScanPlan and applies it to the
    scanner instance. It sets up the appropriate generator (HTTP or WebSocket),
    applies timeout/retry settings, and initializes rate limiting if configured.

    Args:
        scanner_instance: GarakScanner instance to configure
        plan: ScanPlan containing:
            - target_url: Endpoint URL (http/https or ws/wss)
            - scan_config.connection_type: Optional connection type override
            - scan_config.request_timeout: Request timeout in seconds
            - scan_config.max_retries: Retry attempts
            - scan_config.retry_backoff: Exponential backoff multiplier
            - scan_config.requests_per_second: Optional rate limit

    Returns:
        None (modifies scanner_instance in place)

    Side Effects:
        - Sets scanner_instance.config dict with plan configuration
        - Sets scanner_instance.generator (HTTPGenerator or WebSocketGenerator)
        - Sets scanner_instance.rate_limiter (if requests_per_second configured)

    Example:
        configure_scanner_from_scan_plan(scanner, plan)
        # scanner.generator is now configured and ready for probes
    """
    scanner_instance.config = configure_scanner_from_plan(plan)

    scanner_instance.configure_endpoint(
        endpoint_url=plan.target_url,
        headers={},
        connection_type=plan.scan_config.connection_type,
        timeout=plan.scan_config.request_timeout,
        max_retries=plan.scan_config.max_retries,
        retry_backoff=plan.scan_config.retry_backoff,
        config=scanner_instance.config
    )


async def stream_probe_execution(
    probe_names: List[str],
    plan: "ScanPlan",
    generator: Union["HttpGenerator", "WebSocketGenerator"]
) -> AsyncGenerator[ScannerEvent, None]:
    """
    Execute probes sequentially and stream real-time events for progress tracking.

    This is the core probe execution loop. For each probe name in the input list:

    1. Load probe metadata (description, category) via config lookups
    2. Dynamically import probe class using importlib
    3. Instantiate probe with the generator
    4. Emit ProbeStartEvent with probe metadata and prompt count
    5. Execute all prompts via stream_prompt_execution
    6. Aggregate prompt results to get pass/fail/error counts
    7. Emit ProbeCompleteEvent with aggregated statistics
    8. Handle errors gracefully and emit ScanErrorEvent (recoverable=True)

    Errors during probe execution do NOT stop subsequent probes.

    Args:
        probe_names: List of probe identifiers
            Examples: ["dan", "promptinj", "encoding", "glitch", "leak"]
        plan: ScanPlan containing scan context:
            - audit_id: Unique scan identifier
            - agent_type: Type of agent (for logging/categorization)
        generator: Configured generator for sending prompts
            Either HTTPGenerator or WebSocketGenerator, pre-configured
            with target endpoint details

    Yields:
        ProbeStartEvent: When probe begins execution
            Contains: probe_name, description, category, index, total_prompts

        PromptResultEvent: For each prompt result (delegated from stream_prompt_execution)
            Contains: prompt, output, status, detector_name/score, timing

        ProbeCompleteEvent: When probe finishes with aggregated stats
            Contains: probe_name, results_count, pass/fail/error counts, duration

        ScanErrorEvent (recoverable=True): If probe loading/execution fails
            Subsequent probes continue executing

    Example:
        async for event in stream_probe_execution(["dan", "promptinj"], plan, gen):
            if isinstance(event, ProbeStartEvent):
                print(f"Starting {event.probe_name}: {event.total_prompts} prompts")
            elif isinstance(event, PromptResultEvent):
                print(f"  Prompt {event.prompt_index}: {event.status}")
            elif isinstance(event, ProbeCompleteEvent):
                print(f"Complete: {event.fail_count} failures")
    """
    for probe_idx, probe_name in enumerate(probe_names):
        probe_start_time = time.time()

        try:
            # Load probe metadata from centralized config
            probe_description = get_probe_description(probe_name)
            probe_category = get_probe_category(probe_name)
            probe_path = resolve_probe_path(probe_name)

            # Dynamically load probe class
            # Example: probe_path = "garak.probes.dan.Dan_11_0"
            module_name, class_name = probe_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            probe_class = getattr(module, class_name)
            probe = probe_class(generator)
            prompts = probe.prompts

            # Emit event indicating probe is starting
            yield ProbeStartEvent(
                probe_name=probe_name,
                probe_description=probe_description,
                probe_category=probe_category,
                probe_index=probe_idx + 1,
                total_probes=len(probe_names),
                total_prompts=len(prompts),
            )

            # Track individual prompt results for aggregation
            probe_results: List[ProbeResult] = []

            # Execute each prompt and collect results
            async for result_event in stream_prompt_execution(
                probe=probe,
                probe_name=probe_name,
                probe_description=probe_description,
                probe_category=probe_category,
                prompts=prompts,
                generator=generator,
            ):
                yield result_event

                # Accumulate results for probe statistics
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

            # Calculate aggregate statistics for this probe
            probe_duration = time.time() - probe_start_time
            pass_count = sum(1 for r in probe_results if r.status == "pass")
            fail_count = sum(1 for r in probe_results if r.status == "fail")
            error_count = sum(1 for r in probe_results if r.status == "error")

            # Emit final event for probe with statistics
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


async def stream_prompt_execution(
    probe: Any,
    probe_name: str,
    probe_description: str,
    probe_category: str,
    prompts: List[Any],
    generator: Union["HttpGenerator", "WebSocketGenerator"]
) -> AsyncGenerator[Union[PromptResultEvent, ScanErrorEvent], None]:
    """
    Execute all prompts for a single probe and stream individual result events.

    For each prompt in the probe's prompt list:

    1. Extract prompt text from prompt_data object
    2. Time generation: Call generator._call_model(prompt_text) to get LLM output
    3. Time evaluation: Call evaluate_output() to run detector evaluation
    4. Emit PromptResultEvent with:
        - status: "pass" (benign) or "fail" (vulnerable) or "error" (detection failed)
        - detector_name/score: Which detector triggered and confidence score
        - generation/evaluation timing in milliseconds
    5. Handle errors at two levels:
        - Generation errors (LLM unavailable, timeout, etc.)
        - Evaluation errors (detector failure, missing plugin, etc.)

    Each error is caught and yielded as ScanErrorEvent with recoverable=True,
    allowing execution to continue with remaining prompts.

    Args:
        probe: Instantiated Garak probe object
            Must have: prompts attribute (list), detectors configured
        probe_name: Probe identifier (e.g., "dan", "promptinj")
            Used in event logging for traceability
        probe_description: Human-readable probe description
            Example: "Jailbreak attempts via Direct Answer Negation"
        probe_category: Vulnerability category
            Examples: "jailbreak", "pii", "sql_injection", "auth_bypass"
        prompts: List of prompt objects from probe.prompts
            Typically extracted via get_prompt() in earlier code
        generator: Generator for executing prompts against target
            Provides _call_model(prompt_text, generations=1) method

    Yields:
        PromptResultEvent: For each successfully evaluated prompt
            Contains:
            - prompt: Exact prompt text sent
            - output: LLM output received
            - status: "pass" (safe) or "fail" (vulnerable) or "error" (detection failed)
            - detector_name: Which detector returned this result
            - detector_score: Confidence score from detector (0.0-1.0 typically)
            - detection_reason: Human-readable explanation of detection
            - generation_duration_ms: Time to get LLM output
            - evaluation_duration_ms: Time to run detectors

        ScanErrorEvent (recoverable=True): If generation or evaluation fails
            Allows continuation with next prompt
            Contains: error_type, error_message, probe_name, prompt_index

    Example:
        async for event in stream_prompt_execution(
            probe, "dan", "Direct Answer Negation", "jailbreak",
            probe.prompts, generator
        ):
            if isinstance(event, PromptResultEvent):
                print(f"Prompt {event.prompt_index}: {event.status}")
                print(f"  Detector: {event.detector_name} ({event.detector_score})")
            elif isinstance(event, ScanErrorEvent):
                print(f"Error on prompt {event.prompt_index}: {event.error_message}")
    """
    for prompt_idx, prompt_data in enumerate(prompts):
        # Extract the actual prompt text from the probe's prompt object
        prompt_text = extract_prompt_text(prompt_data)

        try:
            # Phase 1: Generate LLM output
            gen_start = time.time()

            # Execute prompt once against the target LLM
            # generations=1 means single output (no sampling multiple responses)
            outputs = generator._call_model(prompt_text, generations=1)
            output_text = outputs[0] if outputs else ""

            gen_duration_ms = int((time.time() - gen_start) * 1000)
            eval_start = time.time()

            try:
                # Phase 2: Evaluate output with detectors
                # evaluate_output delegates to detector pipeline based on probe config
                result = await evaluate_output(
                    probe, probe_name, probe_description, probe_category,
                    prompt_text, output_text
                )

                eval_duration_ms = int((time.time() - eval_start) * 1000)

                # Emit result event with timing
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
                # Detector evaluation failed, but we preserve the output
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
            # Generation failed (LLM timeout, connection error, etc.)
            logger.error(f"Error generating output for prompt {prompt_idx + 1}: {e}")
            yield ScanErrorEvent(
                error_type="generation_error",
                error_message=f"Generation failed: {str(e)}",
                probe_name=probe_name,
                prompt_index=prompt_idx + 1,
                recoverable=True,
                context={"prompt_length": len(prompt_text)}
            )
