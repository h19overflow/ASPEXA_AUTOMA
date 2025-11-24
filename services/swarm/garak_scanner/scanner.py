"""
Core GarakScanner class for security scanning.
"""
import importlib
import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Union

from garak.attempt import Attempt, Message, Turn, Conversation

from services.swarm.core.config import (
    resolve_probe_path,
    get_probe_description,
    get_probe_category,
)
from services.swarm.core.utils import log_performance_metric
from .models import ProbeResult
from .detectors import get_detector_triggers, run_detectors_on_attempt
from .http_generator import HttpGenerator
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
        self.generator: Optional[HttpGenerator] = None
        logger.info("GarakScanner initialized")

    def configure_http_endpoint(self, endpoint_url: str, headers: dict = None):
        """Configure an HTTP endpoint as the target generator."""
        self.generator = HttpGenerator(endpoint_url, headers or {})
        logger.info(f"Configured HTTP endpoint: {endpoint_url}")

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
            raise RuntimeError("No generator configured. Call configure_http_endpoint first.")

        if isinstance(probe_names, str):
            probe_names = [probe_names]

        all_results = []

        for probe_name in probe_names:
            logger.info(f"Running probe: {probe_name}")
            results = await self._run_single_probe(probe_name, generations)
            all_results.extend(results)

        return all_results

    async def _run_single_probe(self, probe_name: str, generations: int) -> List[ProbeResult]:
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
                # Generate outputs
                gen_start = time.time()
                outputs = self.generator._call_model(prompt_text, generations=generations)
                gen_duration = time.time() - gen_start
                log_performance_metric("probe_generation_time", gen_duration, "seconds")

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
