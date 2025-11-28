"""Configuration settings for the Aspexa system.

Loads settings from environment variables with support for .env files.
"""
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources.providers.cli import T


class S3Settings(BaseSettings):
    """S3 Persistence Layer configuration."""
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    aws_access_key_id: Optional[str] = Field(None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(None, description="AWS secret key")
    s3_bucket_name: str = Field(..., description="S3 bucket for audit artifacts")
    aws_region: str = Field(default="ap-southeast-2", description="AWS region")


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    database_url: Optional[str] = Field(None, description="PostgreSQL connection URL")




class Settings(BaseSettings):
    """Root settings aggregating all configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # S3 Settings
    aws_access_key_id: Optional[str] = Field(None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(None, description="AWS secret key")
    s3_bucket_name: Optional[str] = Field(None, description="S3 bucket name")
    aws_region: str = Field(default="ap-southeast-2", description="AWS region")

    # Database Settings
    database_url: Optional[str] = Field(None, description="PostgreSQL URL")

    # Redis Settings
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL")

    # Langfuse Monitoring Settings
    langfuse_public_key: Optional[str] = Field(None, description="Langfuse public API key")
    langfuse_secret_key: Optional[str] = Field(None, description="Langfuse secret API key")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", description="Langfuse server host")
    langfuse_enabled: bool = Field(default=True, description="Enable Langfuse monitoring")

    @property
    def s3(self) -> S3Settings:
        """Get S3-specific settings."""
        return S3Settings(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            s3_bucket_name=self.s3_bucket_name or "",
            aws_region=self.aws_region,
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
