"""
Probe loading utilities.

Purpose: Load Garak probes by name/path
Dependencies: garak.probes
Used by: execution/scanner.py
"""
import importlib
import logging
from typing import Any, List

logger = logging.getLogger(__name__)


def load_probe(probe_name: str) -> Any:
    """Load a Garak probe by its module.ClassName path.

    Args:
        probe_name: Full path (e.g., 'dan.Dan_11_0') or short name

    Returns:
        Instantiated probe object

    Raises:
        ValueError: If probe_name format is invalid
        ImportError: If probe module not found
    """
    if "." not in probe_name:
        raise ValueError(f"Probe name must be module.ClassName: {probe_name}")

    # Handle both short and full paths
    if probe_name.startswith("garak.probes."):
        full_module = probe_name.rsplit(".", 1)[0]
        class_name = probe_name.rsplit(".", 1)[1]
    else:
        module_path, class_name = probe_name.rsplit(".", 1)
        full_module = f"garak.probes.{module_path}"

    try:
        module = importlib.import_module(full_module)
        probe_class = getattr(module, class_name)
        return probe_class()
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to load probe {probe_name}: {e}")
        raise


def get_probe_prompts(probe: Any) -> List[str]:
    """Extract prompts from a probe instance.

    Args:
        probe: Instantiated Garak probe

    Returns:
        List of prompt strings
    """
    if hasattr(probe, "prompts"):
        return list(probe.prompts)
    return []


def get_probe_category_from_name(probe_name: str) -> str:
    """Extract category from probe name.

    Args:
        probe_name: Full probe path (e.g., 'dan.Dan_11_0')

    Returns:
        Category string (e.g., 'dan')
    """
    if "." in probe_name:
        # Handle garak.probes.dan.Dan_11_0 -> dan
        parts = probe_name.replace("garak.probes.", "").split(".")
        return parts[0]
    return "unknown"
