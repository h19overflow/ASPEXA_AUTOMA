"""Permission dependencies for API Gateway.

Provides authorization checks based on user metadata.
"""
from fastapi import Depends, HTTPException

from services.api_gateway.auth.clerk_auth import get_current_user, ClerkUser


async def require_friend(user: ClerkUser = Depends(get_current_user)) -> ClerkUser:
    """
    FastAPI dependency that requires the user to be a "friend".

    Friends are identified by having `isFriend: true` in their Clerk public metadata.

    Raises:
        HTTPException: 403 if user is not a friend.
    """
    if not user.is_friend:
        raise HTTPException(
            status_code=403,
            detail="Access restricted to friends only. Contact the admin for access.",
        )
    return user
