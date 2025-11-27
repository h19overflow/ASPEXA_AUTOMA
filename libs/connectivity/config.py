"""
Connection settings with environment-based configuration.

This module provides Pydantic settings for default connection values
that can be overridden via environment variables.
"""
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class ConnectionSettings(BaseSettings):
    """Default connection settings loaded from environment.

    Environment variables:
        CONNECTIVITY_DEFAULT_TIMEOUT: Default request timeout (seconds)
        CONNECTIVITY_DEFAULT_MAX_RETRIES: Default max retry attempts
        CONNECTIVITY_DEFAULT_RETRY_BACKOFF: Default backoff factor
        CONNECTIVITY_DEFAULT_MESSAGE_FIELD: Default message field name
        CONNECTIVITY_DEFAULT_RESPONSE_FIELDS: Comma-separated response field names
    """

    default_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        alias="CONNECTIVITY_DEFAULT_TIMEOUT",
        description="Default request timeout in seconds",
    )

    default_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        alias="CONNECTIVITY_DEFAULT_MAX_RETRIES",
        description="Default maximum retry attempts",
    )

    default_retry_backoff: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        alias="CONNECTIVITY_DEFAULT_RETRY_BACKOFF",
        description="Default backoff factor for retries",
    )

    default_message_field: str = Field(
        default="message",
        alias="CONNECTIVITY_DEFAULT_MESSAGE_FIELD",
        description="Default field name for outgoing messages",
    )

    default_response_fields: List[str] = Field(
        default=["response", "text", "output", "message"],
        alias="CONNECTIVITY_DEFAULT_RESPONSE_FIELDS",
        description="Default priority-ordered response fields",
    )

    class Config:
        env_prefix = ""
        case_sensitive = False


def get_settings() -> ConnectionSettings:
    """Get cached connection settings instance."""
    return ConnectionSettings()
