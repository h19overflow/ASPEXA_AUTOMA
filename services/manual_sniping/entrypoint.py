"""Manual Sniping service entrypoint.

Public functions called by API Gateway router.
Dependencies: All service components
System role: Service facade and orchestration
"""
import asyncio
from typing import Any, Dict, List, Optional
import logging

from fastapi import WebSocket

from .core import SessionManager, ConverterChainExecutor, WebSocketManager, CONVERTER_CATALOG
from .execution import AttackExecutor
from .persistence import ManualSnipingS3Adapter
from .insights import CampaignIntelligenceLoader
from .models import (
    Session,
    AttackAttempt,
    TargetConfig,
    Protocol,
    AuthType,
    AuthConfig,
)

logger = logging.getLogger(__name__)

# Global instances (initialized on first use)
_session_manager: Optional[SessionManager] = None
_ws_manager: Optional[WebSocketManager] = None
_executor: Optional[AttackExecutor] = None
_converter_chain: Optional[ConverterChainExecutor] = None
_s3_adapter: Optional[ManualSnipingS3Adapter] = None
_insights_loader: Optional[CampaignIntelligenceLoader] = None


def _get_session_manager() -> SessionManager:
    """Get or create session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
        # Start cleanup task in background - wrapped to handle no running loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_session_manager.start())
        except RuntimeError:
            # No running loop yet, start will be called later
            pass
    return _session_manager


def _get_ws_manager() -> WebSocketManager:
    """Get or create WebSocket manager singleton."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


def _get_executor() -> AttackExecutor:
    """Get or create attack executor singleton."""
    global _executor
    if _executor is None:
        _executor = AttackExecutor()
    return _executor


def _get_converter_chain() -> ConverterChainExecutor:
    """Get or create converter chain singleton."""
    global _converter_chain
    if _converter_chain is None:
        _converter_chain = ConverterChainExecutor()
    return _converter_chain


def _get_s3_adapter() -> ManualSnipingS3Adapter:
    """Get or create S3 adapter singleton."""
    global _s3_adapter
    if _s3_adapter is None:
        _s3_adapter = ManualSnipingS3Adapter()
    return _s3_adapter


def _get_insights_loader() -> CampaignIntelligenceLoader:
    """Get or create insights loader singleton."""
    global _insights_loader
    if _insights_loader is None:
        _insights_loader = CampaignIntelligenceLoader()
    return _insights_loader


# Session Management


async def create_session(
    name: Optional[str] = None,
    campaign_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new manual sniping session.

    Args:
        name: Optional session name
        campaign_id: Optional link to campaign

    Returns:
        Session details with stats
    """
    manager = _get_session_manager()
    session = manager.create_session(name=name, campaign_id=campaign_id)
    return {
        "session_id": session.session_id,
        "name": session.name,
        "campaign_id": session.campaign_id,
        "status": session.status.value,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "attempts": [],
        "saved_chains": session.saved_chains,
        "stats": session.get_stats(),
    }


async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session details.

    Args:
        session_id: Session identifier

    Returns:
        Session details or None if not found
    """
    manager = _get_session_manager()
    session = manager.get_session(session_id)
    if not session:
        return None

    return {
        "session_id": session.session_id,
        "name": session.name,
        "campaign_id": session.campaign_id,
        "status": session.status.value,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "attempts": [attempt.model_dump(mode="json") for attempt in session.attempts],
        "saved_chains": session.saved_chains,
        "stats": session.get_stats(),
        "s3_key": session.s3_key,
        "scan_id": session.scan_id,
    }


async def list_sessions() -> Dict[str, Any]:
    """List all active sessions.

    Returns:
        Dict with sessions list and total count
    """
    manager = _get_session_manager()
    sessions = manager.list_sessions()

    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "name": s.name,
                "campaign_id": s.campaign_id,
                "status": s.status.value,
                "created_at": s.created_at.isoformat(),
                "attempt_count": len(s.attempts),
                "stats": s.get_stats(),
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


async def delete_session(session_id: str) -> bool:
    """Delete a session.

    Args:
        session_id: Session identifier

    Returns:
        True if deleted, False if not found
    """
    manager = _get_session_manager()
    return manager.delete_session(session_id)


# Transformation


async def transform_payload(
    payload: str,
    converters: List[str],
) -> Dict[str, Any]:
    """Preview payload transformation.

    Args:
        payload: Original payload
        converters: List of converter names

    Returns:
        Transform result with steps
    """
    chain = _get_converter_chain()
    result = await chain.transform_with_steps(payload, converters)
    return result.model_dump(mode="json")


# Execution


async def execute_attack(
    session_id: str,
    payload: str,
    converters: List[str],
    target: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute an attack (async).

    Args:
        session_id: Session identifier
        payload: Raw payload
        converters: List of converter names
        target: Target configuration dict

    Returns:
        Dict with attempt_id and status
    """
    manager = _get_session_manager()
    session = manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # Build target config
    target_config = TargetConfig(
        url=target["url"],
        protocol=Protocol(target.get("protocol", "http")),
        headers=target.get("headers", {}),
        auth=AuthConfig(
            auth_type=AuthType(target.get("auth", {}).get("auth_type", "none")),
            token=target.get("auth", {}).get("token"),
            username=target.get("auth", {}).get("username"),
            password=target.get("auth", {}).get("password"),
            header_name=target.get("auth", {}).get("header_name", "Authorization"),
        ),
        timeout_seconds=target.get("timeout_seconds", 30),
        message_field=target.get("message_field", "message"),
    )

    # Create attempt placeholder
    attempt = AttackAttempt(
        raw_payload=payload,
        converter_chain=converters,
        transformed_payload="",
        target_url=target_config.url,
        protocol=target_config.protocol.value,
        headers=target_config.headers.copy(),
    )
    manager.add_attempt(session_id, attempt)

    # Execute attack asynchronously
    ws_manager = _get_ws_manager()
    executor = _get_executor()

    def on_progress(stage: str, data: Dict[str, Any]) -> None:
        """Progress callback for WebSocket updates."""
        asyncio.create_task(
            ws_manager.send_progress(session_id, attempt.attempt_id, stage, data)
        )

    # Run execution in background
    asyncio.create_task(_execute_and_update(
        session_id, attempt.attempt_id, payload, converters, target_config, on_progress
    ))

    return {
        "attempt_id": attempt.attempt_id,
        "session_id": session_id,
        "status": "pending",
        "message": "Attack queued. Connect to WebSocket for real-time updates.",
    }


async def _execute_and_update(
    session_id: str,
    attempt_id: str,
    payload: str,
    converters: List[str],
    target: TargetConfig,
    on_progress,
) -> None:
    """Execute attack and update session (background task)."""
    manager = _get_session_manager()
    executor = _get_executor()
    ws_manager = _get_ws_manager()

    try:
        result = await executor.execute(payload, converters, target, on_progress)

        # Update attempt in session
        manager.update_attempt(
            session_id,
            attempt_id,
            transformed_payload=result.transformed_payload,
            status=result.status,
            response_text=result.response_text,
            response_status_code=result.response_status_code,
            response_headers=result.response_headers,
            latency_ms=result.latency_ms,
            error_message=result.error_message,
            transform_errors=result.transform_errors,
        )

        # Send final response
        await ws_manager.send_response(
            session_id,
            attempt_id,
            {
                "status": result.status.value,
                "text": result.response_text,
                "status_code": result.response_status_code,
                "headers": result.response_headers,
                "latency_ms": result.latency_ms,
            },
        )

    except Exception as e:
        logger.error("Attack execution failed: %s", e)
        await ws_manager.send_error(session_id, attempt_id, str(e))


# Persistence


async def save_session(
    session_id: str,
    name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Save session to S3.

    Args:
        session_id: Session identifier
        name: Optional name update

    Returns:
        Save result or None if session not found
    """
    manager = _get_session_manager()
    session = manager.get_session(session_id)
    if not session:
        return None

    if name:
        session.name = name

    adapter = _get_s3_adapter()
    s3_key, scan_id = await adapter.save_session(session)

    manager.mark_saved(session_id, s3_key, scan_id)

    return {
        "session_id": session_id,
        "s3_key": s3_key,
        "scan_id": scan_id,
        "status": "saved",
        "stats": session.get_stats(),
    }


# Converters


async def get_converters() -> Dict[str, Any]:
    """List available converters.

    Returns:
        Dict with converters and categories
    """
    converters = CONVERTER_CATALOG
    categories = list(set(c.category for c in converters))

    return {
        "converters": [c.model_dump(mode="json") for c in converters],
        "categories": sorted(categories),
    }


# Insights


async def get_campaign_insights(campaign_id: str) -> Optional[Dict[str, Any]]:
    """Load campaign intelligence.

    Args:
        campaign_id: Campaign identifier

    Returns:
        Campaign insights or None if not found
    """
    loader = _get_insights_loader()
    insights = await loader.load_campaign_insights(campaign_id)
    if not insights:
        return None

    return insights.model_dump(mode="json")


# WebSocket


async def connect_websocket(websocket: WebSocket, session_id: str) -> None:
    """Connect WebSocket for session updates.

    Args:
        websocket: WebSocket connection
        session_id: Session to subscribe to
    """
    ws_manager = _get_ws_manager()
    await ws_manager.connect(websocket, session_id)


async def disconnect_websocket(websocket: WebSocket, session_id: str) -> None:
    """Disconnect WebSocket.

    Args:
        websocket: WebSocket connection
        session_id: Session to unsubscribe from
    """
    ws_manager = _get_ws_manager()
    await ws_manager.disconnect(websocket, session_id)
