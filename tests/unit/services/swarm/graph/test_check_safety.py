"""Tests for check_safety node."""

import pytest
from services.swarm.graph.state import SwarmState
from services.swarm.graph.nodes.check_safety import check_safety


@pytest.mark.asyncio
async def test_check_safety_no_policy():
    """Test safety check with no policy - should pass."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["agent_sql"],
        safety_policy=None,
    )

    result = await check_safety(state)

    # Should not have agent_results (not blocked)
    assert "agent_results" not in result or len(result.get("agent_results", [])) == 0

    # Should have agent_start event
    events = result.get("events", [])
    assert any(e["type"] == "agent_start" for e in events)


@pytest.mark.asyncio
async def test_check_safety_sql_blocked():
    """Test safety check blocks SQL agent when injection is blocked."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["agent_sql"],
        safety_policy={"blocked_attack_vectors": ["injection"]},
    )

    result = await check_safety(state)

    # Should have agent_results with blocked status
    assert "agent_results" in result
    assert len(result["agent_results"]) == 1
    assert result["agent_results"][0].status == "blocked"

    # Should advance agent index
    assert result["current_agent_index"] == 1

    # Should have agent_blocked event
    events = result.get("events", [])
    assert any(e["type"] == "agent_blocked" for e in events)


@pytest.mark.asyncio
async def test_check_safety_auth_blocked():
    """Test safety check blocks auth agent when bypass is blocked."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["agent_auth"],
        safety_policy={"blocked_attack_vectors": ["bypass"]},
    )

    result = await check_safety(state)

    assert "agent_results" in result
    assert result["agent_results"][0].status == "blocked"


@pytest.mark.asyncio
async def test_check_safety_jailbreak_blocked():
    """Test safety check blocks jailbreak agent when jailbreak is blocked."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["agent_jailbreak"],
        safety_policy={"blocked_attack_vectors": ["jailbreak"]},
    )

    result = await check_safety(state)

    assert "agent_results" in result
    assert result["agent_results"][0].status == "blocked"


@pytest.mark.asyncio
async def test_check_safety_unrelated_vector():
    """Test safety check allows agent when unrelated vector is blocked."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["agent_sql"],
        safety_policy={"blocked_attack_vectors": ["jailbreak"]},  # Doesn't affect SQL
    )

    result = await check_safety(state)

    # Should not be blocked
    assert "agent_results" not in result or len(result.get("agent_results", [])) == 0


@pytest.mark.asyncio
async def test_check_safety_emits_agent_start():
    """Test that check_safety always emits agent_start event."""
    state = SwarmState(
        audit_id="test-001",
        target_url="https://api.test.local/chat",
        agent_types=["agent_sql", "agent_auth", "agent_jailbreak"],
        current_agent_index=1,  # auth agent
    )

    result = await check_safety(state)

    events = result.get("events", [])
    agent_start = next((e for e in events if e["type"] == "agent_start"), None)

    assert agent_start is not None
    assert agent_start["agent"] == "agent_auth"
    assert agent_start["index"] == 2  # 1-indexed
    assert agent_start["total"] == 3
