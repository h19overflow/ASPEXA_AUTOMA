"""
Detector loading and execution.

Purpose: Load Garak detectors by module path and execute them on attempts
Dependencies: garak.attempt, garak.detectors
Used by: utils.py, execution/scanner.py
"""
import importlib
import logging
from typing import Dict, List

from garak.attempt import Attempt

logger = logging.getLogger(__name__)


def load_detector(detector_path: str):
    """Load a Garak detector by its module path.

    Args:
        detector_path: Detector path (e.g., 'mitigation.MitigationBypass' or full path)

    Returns:
        Instantiated detector object

    Raises:
        ImportError: If detector module not found
        AttributeError: If detector class not found in module
    """
    if "." not in detector_path:
        detector_path = f"garak.detectors.{detector_path}"

    if not detector_path.startswith("garak.detectors.") and not detector_path.startswith("garak_scanner."):
        detector_path = f"garak.detectors.{detector_path}"

    module_name, class_name = detector_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    detector_class = getattr(module, class_name)
    return detector_class()


def run_detectors_on_attempt(attempt: Attempt, probe) -> Dict[str, List[float]]:
    """Run probe's detectors on an attempt and return scores.

    Detector priority (highest to lowest):
    1. primary_detector - explicit single detector override
    2. recommended_detector - Garak's recommended detectors for this probe type
    3. extended_detectors - additional detectors
    4. default_detectors - older API fallback
    5. mitigation.MitigationBypass - generic fallback

    Args:
        attempt: Garak Attempt object with prompt and outputs
        probe: Loaded probe instance (used to get detector config)

    Returns:
        Dict mapping detector names to list of scores (0.0=pass, 1.0=fail)
    """
    results: Dict[str, List[float]] = {}

    # Get detectors from probe - Garak probes define these via metaclass
    detector_paths: List[str] = []

    # Check for primary_detector (set by probe metaclass) - highest priority
    primary = getattr(probe, "primary_detector", None)
    if primary:
        detector_paths.append(primary)

    # Check for recommended_detector - Garak's probe-specific detectors
    # This is critical for DAN probes which recommend ['mitigation.MitigationBypass', 'dan.DAN']
    recommended = getattr(probe, "recommended_detector", None)
    if recommended:
        if isinstance(recommended, list):
            detector_paths.extend(recommended)
        else:
            detector_paths.append(recommended)

    # Check for extended_detectors
    extended = getattr(probe, "extended_detectors", None)
    if extended:
        detector_paths.extend(extended)

    # Check for default_detectors (older API)
    defaults = getattr(probe, "default_detectors", None)
    if defaults:
        detector_paths.extend(defaults)

    # Only use MitigationBypass as a last-resort fallback when the probe defines
    # no detectors of its own. Adding it unconditionally causes false positives:
    # e.g. promptinj uses AttackRogueString (checks if the rogue payload appeared
    # in the output), but MitigationBypass scores 1.0 whenever the LLM's refusal
    # phrase doesn't exactly match its keyword list — marking a clear refusal as VULN.
    if not detector_paths:
        detector_paths.append("garak_scanner.detection.securebank.SecureBankBypass")

    # Remove duplicates while preserving order
    # Also explicitly swap out default mitigation detector for our custom one
    seen = set()
    unique_paths = []
    for path in detector_paths:
        if path == "mitigation.MitigationBypass":
            path = "garak_scanner.detection.securebank.SecureBankBypass"
            
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)
    detector_paths = unique_paths

    logger.debug(f"Running detectors for {probe.__class__.__name__}: {detector_paths}")

    for detector_path in detector_paths:
        try:
            detector = load_detector(detector_path)
            scores = detector.detect(attempt)
            results[detector_path] = scores
            logger.debug(f"Detector {detector_path}: {scores}")
        except Exception as e:
            logger.warning(f"Detector {detector_path} failed: {e}")
            results[detector_path] = [0.0]

    return results
