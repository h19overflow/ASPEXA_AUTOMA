"""In-memory session management with TTL cleanup.

Sessions are stored in memory until user explicitly saves to S3.
Implements automatic cleanup of expired sessions.
Dependencies: asyncio, logging
System role: Session lifecycle and state management
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from ..models.session import Session, SessionStatus, AttackAttempt

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages in-memory session state with TTL.

    Thread-safe session store with automatic expiration.
    Sessions expire after DEFAULT_TTL_HOURS of inactivity.
    """

    DEFAULT_TTL_HOURS = 24
    CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes

    def __init__(self, ttl_hours: int = DEFAULT_TTL_HOURS):
        """Initialize session manager.

        Args:
            ttl_hours: Hours before inactive sessions expire
        """
        self._sessions: Dict[str, Session] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            "Session manager started with %d hour TTL", self._ttl.total_seconds() / 3600
        )

    async def stop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Session manager stopped")

    def create_session(
        self,
        name: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> Session:
        """Create a new session.

        Args:
            name: Optional session name
            campaign_id: Optional link to campaign

        Returns:
            Created Session object
        """
        session = Session(name=name, campaign_id=campaign_id)
        self._sessions[session.session_id] = session
        logger.info("Created session %s", session.session_id)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session if active, None otherwise
        """
        session = self._sessions.get(session_id)
        if session and session.status == SessionStatus.ACTIVE:
            return session
        return None

    def add_attempt(self, session_id: str, attempt: AttackAttempt) -> bool:
        """Add an attempt to a session.

        Args:
            session_id: Session identifier
            attempt: Attack attempt to add

        Returns:
            True if added, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        session.add_attempt(attempt)
        return True

    def update_attempt(
        self,
        session_id: str,
        attempt_id: str,
        **updates,
    ) -> bool:
        """Update an existing attempt.

        Args:
            session_id: Session identifier
            attempt_id: Attempt identifier
            **updates: Fields to update

        Returns:
            True if updated, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False

        for attempt in session.attempts:
            if attempt.attempt_id == attempt_id:
                for key, value in updates.items():
                    if hasattr(attempt, key):
                        setattr(attempt, key, value)
                session.updated_at = datetime.utcnow()
                return True
        return False

    def mark_saved(self, session_id: str, s3_key: str, scan_id: str) -> bool:
        """Mark a session as saved to S3.

        Args:
            session_id: Session identifier
            s3_key: S3 storage key
            scan_id: Generated scan ID

        Returns:
            True if marked, False if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.status = SessionStatus.SAVED
        session.s3_key = s3_key
        session.scan_id = scan_id
        session.updated_at = datetime.utcnow()
        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from memory.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Deleted session %s", session_id)
            return True
        return False

    def list_sessions(self) -> List[Session]:
        """List all active sessions.

        Returns:
            List of active Session objects
        """
        return [s for s in self._sessions.values() if s.status == SessionStatus.ACTIVE]

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup error: %s", e)

    def _cleanup_expired(self) -> int:
        """Remove sessions past TTL.

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        expired = [
            sid
            for sid, s in self._sessions.items()
            if s.status == SessionStatus.ACTIVE and (now - s.updated_at) > self._ttl
        ]
        for sid in expired:
            self._sessions[sid].status = SessionStatus.EXPIRED
            del self._sessions[sid]

        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))
        return len(expired)
