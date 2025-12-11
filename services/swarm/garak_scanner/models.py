"""
Data models for garak scanner.

Includes:
- ProbeResult: Legacy result from individual probe executions
- Scanner events: Streaming event types for real-time scan progress
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Union, Dict, Any, Optional


@dataclass
class ProbeResult:
    """Result from a single probe execution with detector-based pass/fail."""
    probe_name: str
    probe_description: str
    category: str
    prompt: str
    output: str
    status: str  # 'pass', 'fail', 'error'
    detector_name: str
    detector_score: float
    detection_reason: str


# ============================================================================
# Scanner Streaming Events
# ============================================================================


@dataclass
class ScanStartEvent:
    """Emitted when a scan begins.

    Provides initial scan context and configuration overview.
    """
    event_type: str = "scan_start"
    timestamp: str = ""
    audit_id: str = ""
    agent_type: str = ""
    total_probes: int = 0
    parallel_enabled: bool = False
    rate_limit_rps: Optional[float] = None
    estimated_duration_seconds: Optional[int] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ProbeStartEvent:
    """Emitted when a probe starts execution.

    Indicates which probe is beginning and its context.
    """
    event_type: str = "probe_start"
    timestamp: str = ""
    probe_name: str = ""
    probe_description: str = ""
    probe_category: str = ""
    probe_index: int = 0
    total_probes: int = 0
    total_prompts: int = 0

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class PromptResultEvent:
    """Emitted after each prompt/output pair is evaluated.

    Provides granular feedback on individual attack attempts.
    """
    event_type: str = "prompt_result"
    timestamp: str = ""
    probe_name: str = ""
    prompt_index: int = 0
    total_prompts: int = 0
    prompt: str = ""
    output: str = ""
    status: str = ""  # 'pass', 'fail', 'error'
    detector_name: str = ""
    detector_score: float = 0.0
    detection_reason: str = ""
    generation_duration_ms: int = 0
    evaluation_duration_ms: int = 0

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ProbeCompleteEvent:
    """Emitted when a probe finishes execution.

    Summarizes results for the completed probe.
    """
    event_type: str = "probe_complete"
    timestamp: str = ""
    probe_name: str = ""
    probe_index: int = 0
    total_probes: int = 0
    results_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    error_count: int = 0
    duration_seconds: float = 0.0

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ScanCompleteEvent:
    """Emitted when all probes are finished.

    Provides final scan summary and statistics.
    """
    event_type: str = "scan_complete"
    timestamp: str = ""
    total_probes: int = 0
    total_results: int = 0
    total_pass: int = 0
    total_fail: int = 0
    total_error: int = 0
    duration_seconds: float = 0.0
    vulnerabilities_found: int = 0

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ScanErrorEvent:
    """Emitted when an error occurs during scanning.

    Captures errors without halting the stream.
    """
    event_type: str = "scan_error"
    timestamp: str = ""
    error_type: str = ""
    error_message: str = ""
    probe_name: Optional[str] = None
    prompt_index: Optional[int] = None
    recoverable: bool = True
    context: Dict[str, Any] = None

    def __post_init__(self):
        """Set timestamp and context if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if self.context is None:
            self.context = {}


# Union type for all scanner events
ScannerEvent = Union[
    ScanStartEvent,
    ProbeStartEvent,
    PromptResultEvent,
    ProbeCompleteEvent,
    ScanCompleteEvent,
    ScanErrorEvent,
]
