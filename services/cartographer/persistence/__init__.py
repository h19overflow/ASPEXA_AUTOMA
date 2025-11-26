"""Persistence module for reconnaissance results.

Local file persistence has been removed. All data is persisted to S3.
"""
from .json_storage import transform_to_if02_format, transform_deductions_to_observations
from .s3_adapter import persist_recon_result

__all__ = [
    'transform_to_if02_format',
    'transform_deductions_to_observations',
    'persist_recon_result',
]
