"""Persistence module for reconnaissance results.

Purpose: S3 persistence for reconnaissance data
Role: Saves recon blueprints to S3, updates campaign stage tracking
Dependencies: libs.persistence, libs.persistence.sqlite

Note: Local file persistence has been removed. All data is persisted to S3.
"""

from .s3_adapter import persist_recon_result

__all__ = [
    "persist_recon_result",
]
