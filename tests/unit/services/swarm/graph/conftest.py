"""Fixtures for graph tests."""

import pytest
from datetime import datetime, timezone


@pytest.fixture
def valid_recon_context():
    """Return a valid ReconBlueprint-compatible context."""
    return {
        "audit_id": "test-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intelligence": {
            "system_prompt_leak": [],
            "detected_tools": [],
            "infrastructure": {
                "vector_db": None,
                "model_family": "gpt-4",
                "rate_limits": None,
            },
            "auth_structure": {
                "type": "bearer",
                "rules": [],
                "vulnerabilities": [],
            },
        },
    }


@pytest.fixture
def valid_recon_context_with_tools():
    """Return a valid ReconBlueprint context with detected tools."""
    return {
        "audit_id": "test-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intelligence": {
            "system_prompt_leak": ["You are a helpful assistant"],
            "detected_tools": [
                {"name": "search", "arguments": ["query"]},
                {"name": "calculator", "arguments": ["expression"]},
            ],
            "infrastructure": {
                "vector_db": "pinecone",
                "model_family": "gpt-4",
                "rate_limits": "100/min",
            },
            "auth_structure": {
                "type": "RBAC",
                "rules": ["admin can access all", "user restricted"],
                "vulnerabilities": ["BOLA possible"],
            },
        },
    }
