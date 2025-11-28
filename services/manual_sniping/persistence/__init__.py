"""Persistence layer for Manual Sniping service.

Provides S3 storage for session data.
"""
from .s3_adapter import ManualSnipingS3Adapter

__all__ = ["ManualSnipingS3Adapter"]
