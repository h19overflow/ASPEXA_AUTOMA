"""Target configuration models.

Defines target endpoint configuration with authentication support.
Dependencies: pydantic
System role: Models for attack target configuration
"""
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class Protocol(str, Enum):
    """Supported target protocols."""

    HTTP = "http"
    WEBSOCKET = "websocket"


class AuthType(str, Enum):
    """Supported authentication types."""

    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"


class AuthConfig(BaseModel):
    """Authentication configuration.

    Supports bearer tokens, API keys, and basic auth.
    """

    auth_type: AuthType = AuthType.NONE
    token: Optional[str] = None  # For bearer/api_key
    username: Optional[str] = None  # For basic auth
    password: Optional[str] = None  # For basic auth
    header_name: str = "Authorization"  # Custom header for API key


class TargetConfig(BaseModel):
    """Complete target configuration.

    Encapsulates all information needed to connect to and attack a target.
    """

    url: str
    protocol: Protocol = Protocol.HTTP
    headers: Dict[str, str] = Field(default_factory=dict)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    timeout_seconds: int = 30
    message_field: str = "message"  # JSON key for payload
