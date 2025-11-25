"""
Decision Logger for Swarm Agent Activities

Provides structured JSON logging for all agent decisions, tool calls, and scan progress.
Logs are written in JSON Lines format (one JSON object per line) for easy streaming
and frontend integration.
"""
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DecisionLogger:
    """
    Thread-safe logger for agent decisions and activities.
    
    Writes structured JSON logs to a file per audit_id in JSON Lines format.
    """
    
    def __init__(self, audit_id: str, log_dir: str = "logs"):
        """
        Initialize decision logger for an audit.
        
        Args:
            audit_id: Audit identifier for this scan
            log_dir: Directory to store log files (default: "logs")
        """
        self.audit_id = audit_id
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / f"swarm_decisions_{audit_id}.json"
        self._lock = threading.Lock()
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize log file with header comment (JSON Lines doesn't support comments,
        # but we can add a metadata line at the start)
        if not self.log_file.exists():
            self._write_metadata()
    
    def _write_metadata(self):
        """Write metadata line at the start of the log file."""
        metadata = {
            "timestamp": self._get_timestamp(),
            "event_type": "log_metadata",
            "audit_id": self.audit_id,
            "data": {
                "log_format": "json_lines",
                "version": "1.0",
                "description": "Swarm agent decision log"
            }
        }
        self._write_line(metadata)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format with timezone."""
        return datetime.now(timezone.utc).isoformat()
    
    def _write_line(self, data: Dict[str, Any]):
        """Thread-safe write of a JSON line to the log file."""
        with self._lock:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False)
                    f.write('\n')
            except Exception as e:
                logger.error(f"Failed to write decision log: {e}", exc_info=True)
    
    def log_agent_start(
        self,
        agent_type: str,
        target_url: str,
        config: Dict[str, Any],
        infrastructure: Optional[Dict[str, Any]] = None,
        detected_tools: Optional[list] = None
    ):
        """Log agent initialization."""
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "agent_start",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "target_url": target_url,
                "config": config,
                "infrastructure": infrastructure or {},
                "detected_tools_count": len(detected_tools) if detected_tools else 0,
            }
        })
    
    def log_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log tool invocation."""
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "tool_call",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "tool_name": tool_name,
                "parameters": parameters,
            }
        })
    
    def log_tool_result(
        self,
        tool_name: str,
        result: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log tool execution result."""
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "tool_result",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "tool_name": tool_name,
                "result": result,
            }
        })
    
    def log_decision(
        self,
        decision_type: str,
        decision: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """
        Log agent decision.
        
        Args:
            decision_type: Type of decision (e.g., "probe_selection", "generation_adjustment")
            decision: Decision details
            agent_type: Agent type making the decision
        """
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "decision",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "decision_type": decision_type,
                "decision": decision,
            }
        })
    
    def log_reasoning(
        self,
        reasoning: str,
        context: Optional[Dict[str, Any]] = None,
        agent_type: Optional[str] = None
    ):
        """Log agent reasoning for a decision."""
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "reasoning",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "reasoning": reasoning,
                "context": context or {},
            }
        })
    
    def log_scan_progress(
        self,
        progress_type: str,
        progress_data: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """
        Log scan progress updates.
        
        Args:
            progress_type: Type of progress (e.g., "probe_start", "probe_complete", "generation_complete")
            progress_data: Progress details
            agent_type: Agent type
        """
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "progress",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "progress_type": progress_type,
                "progress": progress_data,
            }
        })
    
    def log_configuration(
        self,
        config_type: str,
        config_data: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log configuration choices and overrides."""
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "config",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "config_type": config_type,
                "config": config_data,
            }
        })
    
    def log_parallel_execution(
        self,
        event: str,
        details: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log parallel execution events (probe start, completion, etc.)."""
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "parallel_execution",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "event": event,
                "details": details,
            }
        })
    
    def log_rate_limiting(
        self,
        event: str,
        details: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log rate limiting events."""
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "rate_limiting",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "event": event,
                "details": details,
            }
        })
    
    def log_scan_complete(
        self,
        summary: Dict[str, Any],
        agent_type: Optional[str] = None
    ):
        """Log scan completion with summary."""
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "scan_complete",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "summary": summary,
            }
        })
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        agent_type: Optional[str] = None
    ):
        """Log errors during scan execution."""
        self._write_line({
            "timestamp": self._get_timestamp(),
            "event_type": "error",
            "audit_id": self.audit_id,
            "agent_type": agent_type,
            "data": {
                "error_type": error_type,
                "error_message": error_message,
                "error_details": error_details or {},
            }
        })


# Global registry to reuse logger instances per audit_id
_logger_registry: Dict[str, DecisionLogger] = {}
_registry_lock = threading.Lock()


def get_decision_logger(audit_id: str, log_dir: str = "logs") -> DecisionLogger:
    """
    Get or create a DecisionLogger instance for an audit_id.
    
    This ensures we reuse the same logger instance throughout a scan,
    maintaining consistency and avoiding file handle issues.
    
    Args:
        audit_id: Audit identifier
        log_dir: Directory to store log files
        
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

