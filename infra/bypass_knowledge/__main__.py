"""
Pulumi entry point for Bypass Knowledge VDB infrastructure.

Run with:
    cd infra/bypass_knowledge
    pulumi up --stack dev
"""

from vector_infrastructure import (
    vector_bucket,
    episode_index,
    vector_access_policy,
)

# Resources are exported in vector_infrastructure.py
