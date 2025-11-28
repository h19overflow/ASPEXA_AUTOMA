"""WebSocket connection manager for real-time attack updates.

Manages WebSocket connections and broadcasts progress events to clients.
Dependencies: fastapi.WebSocket, asyncio
System role: Real-time communication with frontend
"""
import asyncio
from typing import Any, Dict, List, Set
from datetime import datetime
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for session updates.

    Allows multiple clients to subscribe to session events.
    """

    def __init__(self):
        """Initialize connection manager."""
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept a WebSocket connection and subscribe to session.

        Args:
            websocket: WebSocket connection
            session_id: Session to subscribe to
        """
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(websocket)
        logger.info("Client connected to session %s", session_id)

        # Send initial connected event
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """Remove a WebSocket connection from session.

        Args:
            websocket: WebSocket connection
            session_id: Session to unsubscribe from
        """
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]
        logger.info("Client disconnected from session %s", session_id)

    async def broadcast(
        self,
        session_id: str,
        event_type: str,
        data: Dict[str, Any],
        attempt_id: str = None,
    ) -> None:
        """Broadcast event to all clients subscribed to session.

        Args:
            session_id: Session to broadcast to
            event_type: Event type (progress, response, error)
            data: Event payload
            attempt_id: Optional attempt ID
        """
        if session_id not in self._connections:
            return

        message = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if attempt_id:
            message["attempt_id"] = attempt_id
        if "stage" in data:
            message["stage"] = data["stage"]
            message["data"] = {k: v for k, v in data.items() if k != "stage"}
        else:
            message["data"] = data

        dead_connections: List[WebSocket] = []
        for websocket in self._connections[session_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning("Failed to send to websocket: %s", e)
                dead_connections.append(websocket)

        # Clean up dead connections
        for websocket in dead_connections:
            self._connections[session_id].discard(websocket)

    async def send_progress(
        self,
        session_id: str,
        attempt_id: str,
        stage: str,
        data: Dict[str, Any],
    ) -> None:
        """Send progress update event.

        Args:
            session_id: Session ID
            attempt_id: Attempt ID
            stage: Current stage (transforming, executing, etc.)
            data: Stage-specific data
        """
        await self.broadcast(
            session_id,
            "progress",
            {"stage": stage, **data},
            attempt_id=attempt_id,
        )

    async def send_response(
        self,
        session_id: str,
        attempt_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Send response event (attack completed).

        Args:
            session_id: Session ID
            attempt_id: Attempt ID
            data: Response data
        """
        await self.broadcast(session_id, "response", data, attempt_id=attempt_id)

    async def send_error(
        self,
        session_id: str,
        attempt_id: str,
        message: str,
        code: str = "ERROR",
    ) -> None:
        """Send error event.

        Args:
            session_id: Session ID
            attempt_id: Attempt ID
            message: Error message
            code: Error code
        """
        await self.broadcast(
            session_id,
            "error",
            {"message": message, "code": code},
            attempt_id=attempt_id,
        )
