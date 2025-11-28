"""Session state models for Manual Sniping.

Tracks all attempts within a session until user persists to S3.
Dependencies: pydantic
System role: Core data model for session management
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class SessionStatus(str, Enum):
    """Session lifecycle states."""

    ACTIVE = "active"
    SAVED = "saved"
    EXPIRED = "expired"


class AttemptStatus(str, Enum):
    """Individual attack attempt states."""

    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AttackAttempt(BaseModel):
    """Single attack attempt within a session.

    Captures input, transformation, execution, and results of one attack.
    """

    attempt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Input
    raw_payload: str
    converter_chain: List[str]  # ["Base64Converter", "ROT13Converter"]
    transformed_payload: str

    # Target
    target_url: str
    protocol: str  # "http" or "websocket"
    headers: Dict[str, str] = Field(default_factory=dict)

    # Output
    status: AttemptStatus = AttemptStatus.PENDING
    response_text: Optional[str] = None
    response_status_code: Optional[int] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None

    # Metadata
    transform_errors: List[str] = Field(default_factory=list)


class Session(BaseModel):
    """Manual sniping session container.

    Accumulates attempts in memory until user saves to S3.
    """

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # State
    status: SessionStatus = SessionStatus.ACTIVE

    # Configuration
    name: Optional[str] = None  # User-provided session name
    campaign_id: Optional[str] = None  # Link to parent campaign

    # Accumulated data
    attempts: List[AttackAttempt] = Field(default_factory=list)

    # Favorites/Presets
    saved_chains: List[List[str]] = Field(default_factory=list)

    # Persistence metadata (populated on save)
    s3_key: Optional[str] = None
    scan_id: Optional[str] = None

    def add_attempt(self, attempt: AttackAttempt) -> None:
        """Add an attempt and update timestamp."""
        self.attempts.append(attempt)
        self.updated_at = datetime.utcnow()

    def get_stats(self) -> Dict[str, Any]:
        """Calculate session statistics.

        Returns:
            Dict with total_attempts, successful, failed, success_rate, avg_latency_ms
        """
        total = len(self.attempts)
        success = sum(1 for a in self.attempts if a.status == AttemptStatus.SUCCESS)
        failed = sum(1 for a in self.attempts if a.status == AttemptStatus.FAILED)
        avg_latency = (
            sum(a.latency_ms for a in self.attempts if a.latency_ms)
            / max(1, sum(1 for a in self.attempts if a.latency_ms))
        )
        return {
            "total_attempts": total,
            "successful": success,
            "failed": failed,
            "success_rate": success / max(1, total),
            "avg_latency_ms": avg_latency,
        }
