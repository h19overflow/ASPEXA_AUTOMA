"""
Decision Logger for Swarm Agent Activities

This module previously provided JSON file logging for agent decisions.
JSON file logging has been disabled - all logging methods are now no-ops.
The class interface is preserved to avoid breaking existing code.
"""
import logging
import threading
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DecisionLogger:
    """
    No-op logger for agent decisions and activities.

    JSON file logging has been disabled. All methods are preserved
    as no-ops to maintain API compatibility.
    """

    def __init__(self, audit_id: str, log_dir: str = "logs"):
        """Initialize decision logger (no-op)."""
        self.audit_id = audit_id

    def log_agent_start(
        self,
        agent_type: str,
        target_url: str,
        config: Dict[str, Any],
        infrastructure: Optional[Dict[str, Any]] = None,
        detected_tools: Optional[list] = None
    ):
        """Log agent initialization (no-op)."""
        pass

    def log_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log tool invocation (no-op)."""
        pass

    def log_tool_result(
        self,
        tool_name: str,
        result: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log tool execution result (no-op)."""
        pass

    def log_decision(
        self,
        decision_type: str,
        decision: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log agent decision (no-op)."""
        pass

    def log_reasoning(
        self,
        reasoning: str,
        context: Optional[Dict[str, Any]] = None,
        agent_type: Optional[str] = None
    ):
        """Log agent reasoning for a decision (no-op)."""
        pass

    def log_scan_progress(
        self,
        progress_type: str,
        progress_data: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log scan progress updates (no-op)."""
        pass

    def log_configuration(
        self,
        config_type: str,
        config_data: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log configuration choices and overrides (no-op)."""
        pass

    def log_parallel_execution(
        self,
        event: str,
        details: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log parallel execution events (no-op)."""
        pass

    def log_rate_limiting(
        self,
        event: str,
        details: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log rate limiting events (no-op)."""
        pass

    def log_scan_complete(
        self,
        summary: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log scan completion with summary (no-op)."""
        pass

    def log_error(
        self,
        error_type: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        agent_type: Optional[str] = None
    ):
        """Log errors during scan execution (no-op)."""
        pass


# Global registry to reuse logger instances per audit_id
_logger_registry: Dict[str, DecisionLogger] = {}
_registry_lock = threading.Lock()


def get_decision_logger(audit_id: str, log_dir: str = "logs") -> DecisionLogger:
    """
    Get or create a DecisionLogger instance for an audit_id.

    Args:
        audit_id: Audit identifier
        log_dir: Ignored (no file logging)

    Returns:
        DecisionLogger instance for this audit_id
    """
    with _registry_lock:
        if audit_id not in _logger_registry:
            _logger_registry[audit_id] = DecisionLogger(audit_id, log_dir)
        return _logger_registry[audit_id]


def clear_logger_registry():
    """Clear the logger registry (useful for testing)."""
    global _logger_registry
    with _registry_lock:
        _logger_registry.clear()
