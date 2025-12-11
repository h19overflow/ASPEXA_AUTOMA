"""Clerk JWT authentication for FastAPI.

Verifies Clerk session tokens from the Authorization header and extracts user info.
"""
from typing import Optional
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from clerk_backend_api import Clerk, AuthenticateRequestOptions

from libs.config import get_settings


# Cache for user metadata to avoid repeated API calls
_user_metadata_cache: dict[str, dict] = {}


@dataclass
class ClerkUser:
    """Authenticated user data extracted from Clerk JWT."""

    user_id: str
    session_id: str
    public_metadata: dict
    is_friend: bool

    @classmethod
    def from_request_state(cls, request_state, clerk_client: Optional["Clerk"] = None) -> "ClerkUser":
        """Create ClerkUser from Clerk SDK request state."""
        # Extract claims from the verified token payload
        payload = request_state.payload if hasattr(request_state, "payload") else {}

        # JWT standard claims: 'sub' = subject (user_id), 'sid' = session_id
        user_id = payload.get("sub", "")
        session_id = payload.get("sid", "")

        # public_metadata isn't in JWT by default - fetch from Clerk API if needed
        public_metadata = payload.get("public_metadata", {})

        if not public_metadata and user_id and clerk_client:
            # Check cache first
            if user_id in _user_metadata_cache:
                public_metadata = _user_metadata_cache[user_id]
            else:
                # Fetch user data from Clerk API
                try:
                    user_data = clerk_client.users.get(user_id=user_id)
                    public_metadata = user_data.public_metadata or {}
                    _user_metadata_cache[user_id] = public_metadata
                    print(f"[Auth] Fetched metadata for {user_id}: {public_metadata}")
                except Exception as e:
                    print(f"[Auth] Failed to fetch user metadata: {e}")
                    public_metadata = {}

        return cls(
            user_id=user_id,
            session_id=session_id,
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
                    "http://192.168.0.4:8080",  # Local network access
                    "http://192.168.0.4:5173",  # Local network Vite
                ],
                # Allow 30 seconds of clock skew to handle network latency
                # and minor clock drift between server and Clerk
                clock_skew_in_ms=30000,
            ),
        )

        print(f"[Auth Debug] is_signed_in: {request_state.is_signed_in}")
        print(f"[Auth Debug] All attributes: {dir(request_state)}")
        print(f"[Auth Debug] request_state dict: {vars(request_state) if hasattr(request_state, '__dict__') else 'no __dict__'}")

        if not request_state.is_signed_in:
            reason = getattr(request_state, 'reason', 'Unknown')
            message = getattr(request_state, 'message', 'Invalid or expired token')
            raise HTTPException(status_code=401, detail=f"Not signed in: {reason} - {message}")

        return ClerkUser.from_request_state(request_state, clerk_client=clerk)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[Auth Debug] Exception: {e}")
        traceback.print_exc()
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
