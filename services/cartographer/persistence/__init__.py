"""Persistence module for reconnaissance results."""
from .json_storage import save_reconnaissance_result, load_reconnaissance_result
from .s3_adapter import persist_recon_result, persist_with_fallback

__all__ = [
    'save_reconnaissance_result',
    'load_reconnaissance_result',
    'persist_recon_result',
    'persist_with_fallback',
]
