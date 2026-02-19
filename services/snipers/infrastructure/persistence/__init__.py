"""Persistence module for Snipers exploitation service."""
from .s3_adapter import (
    load_campaign_intel,
    persist_exploit_result,
    persist_with_fallback,
)

__all__ = [
    'load_campaign_intel',
    'persist_exploit_result',
    'persist_with_fallback',
]
