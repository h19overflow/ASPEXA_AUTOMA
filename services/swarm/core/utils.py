"""
Logging utilities for Swarm service.
Provides consistent structured logging with correlation IDs.
"""
import logging
import json
import time
from typing import Dict, Any, Optional
from functools import wraps

from services.swarm.core.decision_logger import get_decision_logger as _get_decision_logger, DecisionLogger

logger = logging.getLogger(__name__)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging with correlation IDs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add correlation IDs if present
        if hasattr(record, "audit_id"):
            log_data["audit_id"] = record.audit_id
        if hasattr(record, "agent_type"):
            log_data["agent_type"] = record.agent_type
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def log_scan_start(audit_id: str, agent_type: str, config: Dict[str, Any]) -> None:
    """Log scan start with correlation IDs."""
    extra = {
        "audit_id": audit_id,
        "agent_type": agent_type,
        "extra_fields": {
            "event": "scan_start",
            "config": config,
        }
    }
    logger.info(f"Starting scan for audit {audit_id} with agent {agent_type}", extra=extra)


def log_scan_complete(
    audit_id: str,
    agent_type: str,
    duration: float,
    results: Dict[str, Any]
) -> None:
    """Log scan completion with metrics."""
    extra = {
        "audit_id": audit_id,
        "agent_type": agent_type,
        "extra_fields": {
            "event": "scan_complete",
            "duration_seconds": round(duration, 2),
            "vulnerabilities_found": len(results.get("vulnerabilities", [])),
            "probes_executed": len(results.get("probes_executed", [])),
            "success": results.get("success", False),
        }
    }
    logger.info(
        f"Scan completed for audit {audit_id} in {duration:.2f}s",
        extra=extra
    )


def log_scan_error(
    audit_id: str,
    agent_type: str,
    error: str,
    duration: Optional[float] = None
) -> None:
    """Log scan error with context."""
    extra = {
        "audit_id": audit_id,
        "agent_type": agent_type,
        "extra_fields": {
            "event": "scan_error",
            "error": error,
        }
    }
    if duration is not None:
        extra["extra_fields"]["duration_seconds"] = round(duration, 2)
    
    logger.error(
        f"Scan failed for audit {audit_id}: {error}",
        extra=extra
    )


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = "seconds",
    audit_id: Optional[str] = None,
    agent_type: Optional[str] = None
) -> None:
    """Log a performance metric."""
    extra = {
        "extra_fields": {
            "event": "performance_metric",
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
        }
    }
    if audit_id:
        extra["audit_id"] = audit_id
    if agent_type:
        extra["agent_type"] = agent_type
    
    logger.info(f"Metric: {metric_name}={value} {unit}", extra=extra)


def time_function(func):
    """Decorator to log function execution time."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            logger.debug(
                f"{func.__name__} completed in {duration:.2f}s",
                extra={"extra_fields": {"function": func.__name__, "duration": duration}}
            )
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(
                f"{func.__name__} failed after {duration:.2f}s: {e}",
                extra={"extra_fields": {"function": func.__name__, "duration": duration, "error": str(e)}}
            )
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.debug(
                f"{func.__name__} completed in {duration:.2f}s",
                extra={"extra_fields": {"function": func.__name__, "duration": duration}}
            )
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(
                f"{func.__name__} failed after {duration:.2f}s: {e}",
                extra={"extra_fields": {"function": func.__name__, "duration": duration, "error": str(e)}}
            )
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def get_decision_logger(audit_id: str, log_dir: str = "logs") -> DecisionLogger:
    """
    Get or create a DecisionLogger instance for an audit_id.
    
    This is a convenience wrapper that provides access to the decision logger
    from the utils module. The logger writes structured JSON logs for all
    agent decisions, tool calls, and scan progress.
    
    Args:
        audit_id: Audit identifier for the scan
        log_dir: Directory to store log files (default: "logs")
        
    Returns:
        DecisionLogger instance for this audit_id
        
    Example:
        logger = get_decision_logger("audit-123")
        logger.log_agent_start("agent_jailbreak", "https://api.example.com", {...})
    """
    return _get_decision_logger(audit_id, log_dir)

