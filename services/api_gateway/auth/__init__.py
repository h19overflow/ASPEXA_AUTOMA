"""Authentication module for API Gateway.

Provides Clerk-based JWT verification and authorization dependencies.
"""
from services.api_gateway.auth.clerk_auth import (
    get_current_user,
    get_optional_user,
    ClerkUser,
)
from services.api_gateway.auth.permissions import require_friend

__all__ = [
    "get_current_user",
    "get_optional_user",
    "require_friend",
    "ClerkUser",
]
