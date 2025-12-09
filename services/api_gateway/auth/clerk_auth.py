"""Clerk JWT authentication for FastAPI.

Verifies Clerk session tokens from the Authorization header and extracts user info.
"""
from typing import Optional
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from clerk_backend_api import Clerk, AuthenticateRequestOptions

from libs.config import get_settings


@dataclass
class ClerkUser:
    """Authenticated user data extracted from Clerk JWT."""

    user_id: str
    session_id: str
    public_metadata: dict
    is_friend: bool

    @classmethod
    def from_request_state(cls, request_state) -> "ClerkUser":
        """Create ClerkUser from Clerk SDK request state."""
        # Extract claims from the verified token
        claims = request_state.payload if hasattr(request_state, "payload") else {}

        public_metadata = claims.get("public_metadata", {})

        return cls(
            user_id=request_state.user_id or "",
            session_id=request_state.session_id or "",
            public_metadata=public_metadata,
            is_friend=public_metadata.get("isFriend", False),
        )


def _get_clerk_client() -> Optional[Clerk]:
    """Get Clerk client if configured."""
    settings = get_settings()
    if not settings.clerk_secret_key:
        return None
    return Clerk(bearer_auth=settings.clerk_secret_key)


async def get_current_user(request: Request) -> ClerkUser:
    """
    FastAPI dependency to get the current authenticated user.

    Raises:
        HTTPException: 401 if not authenticated or token is invalid.
    """
    clerk = _get_clerk_client()

    if not clerk:
        raise HTTPException(
            status_code=500,
            detail="Authentication not configured. Set CLERK_SECRET_KEY.",
        )

    # Get the Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )

    try:
        # Authenticate the request using Clerk SDK
        request_state = clerk.authenticate_request(
            request,
            AuthenticateRequestOptions(
                # Accept session tokens from the frontend
                authorized_parties=[
                    "http://localhost:8080",  # Dev frontend
                    "http://localhost:5173",  # Vite default
                ],
            ),
        )

        if not request_state.is_signed_in:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return ClerkUser.from_request_state(request_state)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def get_optional_user(request: Request) -> Optional[ClerkUser]:
    """
    FastAPI dependency to get the current user if authenticated, or None.

    Use this for endpoints that work for both authenticated and unauthenticated users.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
