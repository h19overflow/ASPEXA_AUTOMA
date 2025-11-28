"""Manual Sniping router - HTTP + WebSocket endpoints.

Provides REST API and WebSocket connections for manual attack execution.
Dependencies: fastapi, services.manual_sniping
System role: API gateway for manual sniping service
"""
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
import logging

from services.api_gateway.schemas.manual_sniping import (
    CreateSessionRequest,
    SessionListResponse,
    SessionDetailResponse,
    TransformRequest,
    TransformResponse,
    ExecuteRequest,
    ExecuteResponse,
    SaveSessionRequest,
    SaveSessionResponse,
    ConverterListResponse,
    CampaignInsightsResponse,
)
from services.manual_sniping.entrypoint import (
    create_session,
    get_session,
    list_sessions,
    delete_session,
    transform_payload,
    execute_attack,
    save_session,
    get_converters,
    get_campaign_insights,
    connect_websocket,
    disconnect_websocket,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manual-sniping", tags=["manual-sniping"])


# --- Session Endpoints ---


@router.post("/sessions", status_code=201)
async def create_session_endpoint(
    request: CreateSessionRequest,
) -> SessionDetailResponse:
    """Create a new manual sniping session.

    Args:
        request: Session creation request

    Returns:
        Session details with stats
    """
    result = await create_session(
        name=request.name,
        campaign_id=request.campaign_id,
    )
    return SessionDetailResponse(**result)


@router.get("/sessions")
async def list_sessions_endpoint() -> SessionListResponse:
    """List all active sessions.

    Returns:
        List of session summaries
    """
    result = await list_sessions()
    return SessionListResponse(**result)


@router.get("/sessions/{session_id}")
async def get_session_endpoint(session_id: str) -> SessionDetailResponse:
    """Get session details.

    Args:
        session_id: Session identifier

    Returns:
        Full session details with attempts

    Raises:
        HTTPException: If session not found
    """
    result = await get_session(session_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": f"Session '{session_id}' not found",
            },
        )
    return SessionDetailResponse(**result)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session_endpoint(session_id: str):
    """Delete a session.

    Args:
        session_id: Session identifier

    Raises:
        HTTPException: If session not found
    """
    success = await delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": f"Session '{session_id}' not found",
            },
        )


# --- Transform Endpoint ---


@router.post("/transform")
async def transform_endpoint(request: TransformRequest) -> TransformResponse:
    """Preview payload transformation through converter chain.

    Args:
        request: Transform request with payload and converters

    Returns:
        Transformation result with step-by-step details
    """
    result = await transform_payload(
        payload=request.payload,
        converters=request.converters,
    )
    return TransformResponse(**result)


# --- Execute Endpoint ---


@router.post("/execute", status_code=202)
async def execute_endpoint(request: ExecuteRequest) -> ExecuteResponse:
    """Execute attack (async). Results streamed via WebSocket.

    Args:
        request: Execution request with target and payload

    Returns:
        Attempt ID and status

    Raises:
        HTTPException: If session not found or execution fails
    """
    try:
        result = await execute_attack(
            session_id=request.session_id,
            payload=request.payload,
            converters=request.converters,
            target=request.target.model_dump(),
        )
        return ExecuteResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": str(e),
            },
        )
    except Exception as e:
        logger.error("Execute attack failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "EXECUTION_ERROR",
                "message": str(e),
            },
        )


# --- Save Endpoint ---


@router.post("/sessions/{session_id}/save")
async def save_session_endpoint(
    session_id: str,
    request: SaveSessionRequest,
) -> SaveSessionResponse:
    """Persist session to S3.

    Args:
        session_id: Session identifier
        request: Save request with optional name

    Returns:
        Save result with S3 key and scan ID

    Raises:
        HTTPException: If session not found or save fails
    """
    result = await save_session(session_id=session_id, name=request.name)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": f"Session '{session_id}' not found",
            },
        )
    return SaveSessionResponse(**result)


# --- Converter Endpoint ---


@router.get("/converters")
async def list_converters_endpoint() -> ConverterListResponse:
    """List available converters with metadata.

    Returns:
        Converter list with categories
    """
    result = await get_converters()
    return ConverterListResponse(**result)


# --- Insights Endpoint ---


@router.get("/insights/{campaign_id}")
async def get_insights_endpoint(campaign_id: str) -> CampaignInsightsResponse:
    """Load campaign intelligence from previous phases.

    Args:
        campaign_id: Campaign identifier

    Returns:
        Aggregated campaign insights

    Raises:
        HTTPException: If campaign not found
    """
    result = await get_campaign_insights(campaign_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CAMPAIGN_NOT_FOUND",
                "message": f"Campaign '{campaign_id}' not found",
            },
        )
    return CampaignInsightsResponse(**result)


# --- WebSocket ---


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time attack updates.

    Args:
        websocket: WebSocket connection
        session_id: Session to subscribe to
    """
    await connect_websocket(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await disconnect_websocket(websocket, session_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        await disconnect_websocket(websocket, session_id)
