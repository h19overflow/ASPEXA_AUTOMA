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
    """Configure scanner endpoint and generator from a ScanPlan. Modifies scanner_instance in place."""
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
    Execute probes sequentially, yielding streaming events per prompt.

    Yields ProbeStartEvent, PromptResultEvent, ProbeCompleteEvent per probe.
    Probe errors are recoverable — subsequent probes continue.
    """
    for probe_idx, probe_name in enumerate(probe_names):
        probe_start_time = time.time()

        try:
            probe_description = get_probe_description(probe_name)
            probe_category = get_probe_category(probe_name)
            probe_path = resolve_probe_path(probe_name)

            module_name, class_name = probe_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            probe_class = getattr(module, class_name)
            probe = probe_class(generator)

            max_prompts = getattr(plan.scan_config, 'max_prompts_per_probe', 5)
            prompts = probe.prompts[:max_prompts]

            yield ProbeStartEvent(
                probe_name=probe_name,
                probe_description=probe_description,
                probe_category=probe_category,
                probe_index=probe_idx + 1,
                total_probes=len(probe_names),
                total_prompts=len(prompts),
            )

            probe_results: List[ProbeResult] = []

            async for result_event in stream_prompt_execution(
                probe=probe,
                probe_name=probe_name,
                probe_description=probe_description,
                probe_category=probe_category,
                prompts=prompts,
                generator=generator,
            ):
                yield result_event

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


async def stream_prompt_execution(
    probe: Any,
    probe_name: str,
    probe_description: str,
    probe_category: str,
    prompts: List[Any],
    generator: Union["HttpGenerator", "WebSocketGenerator"]
) -> AsyncGenerator[Union[PromptResultEvent, ScanErrorEvent], None]:
    """
    Send each prompt to the target LLM, evaluate the response, and yield a PromptResultEvent.

    Generation and evaluation errors are yielded as recoverable ScanErrorEvents.
    """
    for prompt_idx, prompt_data in enumerate(prompts):
        # Extract the actual prompt text from the probe's prompt object
        prompt_text = extract_prompt_text(prompt_data)

        try:
            gen_start = time.time()
            outputs = generator._call_model(prompt_text, generations=1)
            output_text = outputs[0] if outputs else ""
            gen_duration_ms = int((time.time() - gen_start) * 1000)

            eval_start = time.time()
            try:
                result = await evaluate_output(
                    probe, probe_name, probe_description, probe_category,
                    prompt_text, output_text
                )
                eval_duration_ms = int((time.time() - eval_start) * 1000)

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
            logger.error(f"Error generating output for prompt {prompt_idx + 1}: {e}")
            yield ScanErrorEvent(
                error_type="generation_error",
                error_message=f"Generation failed: {str(e)}",
                probe_name=probe_name,
                prompt_index=prompt_idx + 1,
                recoverable=True,
                context={"prompt_length": len(prompt_text)}
            )
