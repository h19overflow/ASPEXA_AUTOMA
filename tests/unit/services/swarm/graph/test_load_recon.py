"""Tests for load_recon node."""

import pytest
from services.swarm.graph.state import SwarmState
from services.swarm.graph.nodes.load_recon import load_recon


@pytest.mark.asyncio
async def test_load_recon_success(valid_recon_context):
    """Test successful recon loading."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["sql"],
        recon_context=valid_recon_context,
    )

    result = await load_recon(state)

    assert "errors" not in result or len(result.get("errors", [])) == 0
    assert "events" in result
    assert len(result["events"]) > 0

    # Check log events
    log_events = [e for e in result["events"] if e["type"] == "log"]
    assert any("Starting scan" in e["message"] for e in log_events)


@pytest.mark.asyncio
async def test_load_recon_with_tools(valid_recon_context_with_tools):
    """Test recon loading with detected tools."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["sql"],
        recon_context=valid_recon_context_with_tools,
    )

    result = await load_recon(state)

    assert "errors" not in result or len(result.get("errors", [])) == 0

    # Should report tools detected
    log_events = [e for e in result["events"] if e["type"] == "log"]
    assert any("2 tools detected" in e.get("message", "") for e in log_events)


@pytest.mark.asyncio
async def test_load_recon_missing_context():
    """Test recon loading with empty context."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["sql"],
        recon_context={},
    )

    result = await load_recon(state)

    assert "errors" in result
    assert len(result["errors"]) > 0
    assert "No recon context" in result["errors"][0]


@pytest.mark.asyncio
async def test_load_recon_invalid_blueprint():
    """Test recon loading with invalid blueprint structure."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["sql"],
        recon_context={
            "invalid_field": "should fail validation",
        },
    )

    result = await load_recon(state)

    assert "errors" in result
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_load_recon_emits_correct_events(valid_recon_context):
    """Test that load_recon emits the expected event types."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["sql", "auth"],
        recon_context=valid_recon_context,
    )

    result = await load_recon(state)

    events = result.get("events", [])
    messages = [e.get("message", "") for e in events if e["type"] == "log"]

    # Should include audit ID and agents info
    assert any("test-001" in msg for msg in messages)
    assert any("sql, auth" in msg for msg in messages)
